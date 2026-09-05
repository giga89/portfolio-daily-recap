#!/usr/bin/env python3
"""
Stock News & Catalyst Follow-up Commenter for eToro
===================================================
Monitors high-impact corporate news & catalysts for portfolio holdings.
When breaking news occurs for an asset that has a past Stock Focus post on eToro:
  1. Finds the original Stock Focus eToro Post ID from Gist storage.
  2. Synthesizes a focused, professional Italian catalyst update via Gemini.
  3. Publishes the update as a direct comment under that asset's original post.
  4. Records the news hash on Gist to strictly prevent duplicate comments.
"""

import os
import sys
import time
import json
import hashlib
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load local .env if available
if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')):
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

import etoro_client
import gist_storage
import analytics_tracker
from etoro_sender import _strip_html

try:
    from post_verifier import verify_and_clean_comment
except ImportError:
    try:
        from src.post_verifier import verify_and_clean_comment
    except ImportError:
        verify_and_clean_comment = None

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from api_usage_tracker import log_api_request
    API_TRACKER_AVAILABLE = True
except ImportError:
    API_TRACKER_AVAILABLE = False


DEFAULT_GEMINI_MODELS = [
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-2.5-flash',
]
try:
    from ai_model_cascade import DEFAULT_GEMINI_MODELS
except ImportError:
    try:
        from src.ai_model_cascade import DEFAULT_GEMINI_MODELS
    except ImportError:
        DEFAULT_GEMINI_MODELS = [
            'gemini-3.1-pro',
            'gemini-3.8-flash',
            'gemini-3.7-flash',
            'gemini-3.6-flash',
            'gemini-3.5-flash',
            'gemini-2.5-flash',
        ]


# Keywords indicating operational, financial, or strategic catalysts
CATALYST_KEYWORDS = [
    'earnings', 'revenue', 'profit', 'margin', 'quarter', 'results',
    'chip', 'blackwell', 'gpu', 'semiconductor', 'aip', 'software',
    'fda', 'approval', 'trial', 'drug', 'glp-1', 'phase', 'treatment',
    'contract', 'deal', 'partnership', 'customer', 'enterprise', 'defense',
    'acquisition', 'merger', 'guidance', 'forecast', 'outlook', 'target',
    'upgrade', 'dividend', 'buyback', 'split', 'orders', 'sales',
    'invest', 'expansion', 'patent', 'cloud', 'datacenter', 'launch', 'model'
]

# Words that indicate generic clickbait or noise to filter out
EXCLUDED_HEADLINE_TERMS = [
    'zacks rank', 'should you buy', 'is it time to sell', 'motley fool',
    'why is it falling', 'why is it rising', 'stock price prediction',
    'technical analysis', 'meme stock'
]


def _load_portfolio_config() -> Tuple[Dict[str, str], Dict[str, str]]:
    """Load company names and emojis from portfolio_config.json."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'portfolio_config.json')
    names = {}
    emojis = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                emojis = cfg.get('emojis', {})
                for k, v in cfg.get('tickers', {}).items():
                    if isinstance(v, list) and len(v) >= 2:
                        names[k] = v[1]
                    else:
                        names[k] = k
        except Exception as e:
            print(f"⚠️ Error reading portfolio_config.json: {e}")
    return names, emojis


def compute_news_hash(ticker: str, title: str) -> str:
    """Generate a stable unique hash for a ticker + news headline."""
    norm_title = re.sub(r'[^a-zA-Z0-9]', '', title.lower())
    raw = f"{ticker.upper()}:{norm_title}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]


def is_catalyst_headline(title: str, description: str = "") -> bool:
    """Check if the headline/summary represents a meaningful catalyst."""
    text = f"{title} {description}".lower()
    
    # Filter out clickbait/generic
    for term in EXCLUDED_HEADLINE_TERMS:
        if term in title.lower():
            return False
            
    # Check for catalyst keywords
    return any(k in text for k in CATALYST_KEYWORDS)


def fetch_recent_stock_news(ticker: str, company_name: str, max_items: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch recent news headlines from Google News RSS for a specific company.
    """
    clean_ticker = ticker.replace('$', '').strip()
    # Build clean query: e.g. "NVDA" OR "NVIDIA" stock
    query_parts = [f'"{clean_ticker}"']
    if company_name and company_name != clean_ticker:
        short_name = company_name.split(' Inc')[0].split(' Corp')[0].split(' Co')[0].split(' Ltd')[0].strip()
        query_parts.append(f'"{short_name}"')
    
    query = f"({' OR '.join(query_parts)}) stock when:2d"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    news_items = []
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')
            for it in items[:max_items * 2]:
                title = (it.findtext('title') or '').strip()
                link = (it.findtext('link') or '').strip()
                pub_date = (it.findtext('pubDate') or '').strip()
                desc = (it.findtext('description') or '').strip()
                desc_clean = _strip_html(desc)

                if not title:
                    continue

                if is_catalyst_headline(title, desc_clean):
                    n_hash = compute_news_hash(clean_ticker, title)
                    news_items.append({
                        'ticker': clean_ticker,
                        'company_name': company_name,
                        'title': title,
                        'link': link,
                        'pub_date': pub_date,
                        'description': desc_clean,
                        'hash': n_hash,
                    })
                    if len(news_items) >= max_items:
                        break
    except Exception as e:
        print(f"⚠️ Error fetching Google News RSS for {clean_ticker}: {e}")

    return news_items


def generate_catalyst_comment_text(
    ticker: str,
    company_name: str,
    news_item: Dict[str, Any],
    api_key: Optional[str] = None,
) -> str:
    """
    Generate a concise, professional Italian follow-up comment for eToro.
    """
    title = news_item['title']
    desc = news_item.get('description', '')
    pub_date = news_item.get('pub_date', '')

    fallback_text = (
        f"⚡ UPDATE ${ticker} ({company_name}) 📰\n\n"
        f"• Notizia: {title}\n"
        f"• Impatto per il nostro portafoglio: Questo catalyst conferma la solidità della tesi di crescita "
        f"e la capacità dell'azienda di consolidare la propria leadership di mercato nel medio/lungo termine.\n\n"
        f"💬 Come valutate questa novità per ${ticker}? Lasciate un commento qui sotto! 👇"
    )

    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key or not GENAI_AVAILABLE:
        return fallback_text

    prompt = f"""Sei Andrea Ravalli, Popular Investor italiano su eToro.
Abbiamo precedentemente pubblicato un post di approfondimento su ${ticker} ({company_name}).
È appena emersa questa importante notizia di mercato / catalyst aziendale:

- Titolo Notizia: {title}
- Dettagli: {desc}
- Data: {pub_date}

Scrivi un breve commento di aggiornamento (news update) in ITALIANO da pubblicare come commento sotto al post originale di ${ticker} su eToro.

REGOLE OBBLIGATORIE:
1. Inizia con: ⚡ UPDATE ${ticker} ({company_name}) 📰
2. • Notizia: [1-2 frasi chiare e oggettive che spiegano i fatti salienti della notizia in italiano]
3. • Impatto Portafoglio: [1-2 frasi sintetiche che spiegano perché questa notizia supporta la nostra tesi di investimento a medio/lungo termine o la crescita dei fondamentali]
4. Concludi con una brevissima domanda stimolante per la community di eToro (max 1 riga).
5. Lunghezza totale: tra 300 e 500 caratteri. Stile sobrio, lucido, professionale. NO cliché da robot, NO 'Ciao a tutti'. NO hashtag generici.
6. NON usare mai il markdown per il grassetto (NON usare **testo** o asterischi).

Output SOLO il testo del commento in italiano."""

    try:
        from post_verifier import verify_and_clean_comment
    except ImportError:
        try:
            from src.post_verifier import verify_and_clean_comment
        except ImportError:
            verify_and_clean_comment = None

    try:
        client = genai.Client(api_key=api_key)
        config_gen = types.GenerateContentConfig(temperature=0.6)
        config_gen = types.GenerateContentConfig(temperature=0.4)

        for model_name in DEFAULT_GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config_gen,
                )
                if response and response.text:
                    out = response.text.strip()
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "stock_news_catalyst_comment")
                    return out
            except Exception as exc:
                print(f"   ⚠️ Gemini {model_name} failed: {exc}")
                continue
        for idx, model_name in enumerate(DEFAULT_GEMINI_MODELS):
            for attempt in range(2):
                try:
                    print(f"   🤖 Trying model for catalyst comment ({idx+1}/{len(DEFAULT_GEMINI_MODELS)}): {model_name}...")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config_gen,
                    )
                    if response and response.text:
                        out = response.text.strip()
                        if API_TRACKER_AVAILABLE:
                            log_api_request(model_name, True, "stock_news_catalyst_comment")

                        # Pass 2: Double-Check & Anti-Hallucination Gate
                        if verify_and_clean_comment:
                            approved, verified_text, audit_info = verify_and_clean_comment(
                                text=out,
                                primary_ticker=ticker,
                                generator_model=model_name,
                                run_ai_review=True,
                            )
                            if approved and verified_text:
                                print(f"   ✅ Catalyst comment passed dual-check ({model_name})!")
                                return verified_text
                            else:
                                print(f"   ⚠️ Catalyst comment failed verification ({model_name}), trying next model...")
                                break
                        return out

                except Exception as exc:
                    err_s = str(exc).lower()
                    if "429" in err_s or "quota" in err_s or "resource_exhausted" in err_s:
                        wait_t = 3.0 * (attempt + 1)
                        print(f"   ⏳ Rate limit/Quota (429) on {model_name}. Pausing {wait_t:.1f}s...")
                        time.sleep(wait_t)
                        continue
                    print(f"   ⚠️ Gemini {model_name} failed: {exc}")
                    break
    except Exception as e:
        print(f"⚠️ Gemini client error: {e}")

    # Fallback text also verified
    if verify_and_clean_comment:
        _, clean_fb, _ = verify_and_clean_comment(fallback_text, primary_ticker=ticker, run_ai_review=False)
        return clean_fb or fallback_text
    return fallback_text



def run_stock_news_commenter(
    dry_run: bool = False,
    specific_ticker: Optional[str] = None,
    max_comments: int = 2,
) -> Dict[str, Any]:
    """
    Main orchestrator:
    1. Reads tracked stock focus posts from Gist.
    2. Fetches fresh news for each stock.
    3. If an un-commented catalyst is found, generates and posts a targeted comment.
    """
    print("=" * 65)
    print("🔍 RUNNING STOCK NEWS & CATALYST FOLLOW-UP COMMENTER")
    print(f"🕒 Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"⚙️  Mode: {'DRY RUN (Preview only)' if dry_run else 'LIVE PUBLISH'}")
    print("=" * 65)

    names_map, emojis_map = _load_portfolio_config()
    tracked_posts = gist_storage.get_all_stock_focus_posts()

    if not tracked_posts:
        print("ℹ️ No tracked Stock Focus post IDs currently in Gist.")
        if specific_ticker:
            print(f"ℹ️ Testing with specific ticker: {specific_ticker}")
            tracked_posts = {
                specific_ticker.upper(): {
                    'post_id': 'TEST_POST_ID',
                    'title': f'Stock Focus: ${specific_ticker.upper()}',
                    'company_name': names_map.get(specific_ticker.upper(), specific_ticker.upper()),
                }
            }
        else:
            return {"success": True, "comments_published": 0, "reason": "no_tracked_posts"}

    tickers_to_check = [specific_ticker.upper()] if specific_ticker else list(tracked_posts.keys())
    print(f"📋 Checking {len(tickers_to_check)} asset(s) with historical Stock Focus posts: {tickers_to_check}")

    published_count = 0
    results = []

    for sym in tickers_to_check:
        if published_count >= max_comments:
            print(f"⏹️ Reached maximum comments per run limit ({max_comments}). Stopping.")
            break

        post_data = tracked_posts.get(sym, {})
        post_id = post_data.get('post_id')
        company_name = names_map.get(sym, sym)

        if not post_id:
            continue

        print(f"\n📰 Checking fresh news for ${sym} ({company_name}) [eToro Post ID: {post_id}]...")
        news_items = fetch_recent_stock_news(sym, company_name, max_items=4)
        print(f"   Found {len(news_items)} potential catalyst article(s).")

        for item in news_items:
            n_hash = item['hash']
            if gist_storage.is_news_commented(n_hash):
                print(f"   ⏭️  News already commented (hash: {n_hash}): {item['title'][:60]}...")
                continue

            print(f"\n   🔥 NEW CATALYST DETECTED for ${sym}!")
            print(f"   • Headline: {item['title']}")
            print(f"   • Date: {item['pub_date']}")

            # Generate high quality comment
            comment_text = generate_catalyst_comment_text(sym, company_name, item)
            clean_text = _strip_html(comment_text)
            try:
                from ai_news_generator import sanitize_etoro_cashtags
                clean_text = sanitize_etoro_cashtags(clean_text)
            except Exception:
                pass

            print("\n" + "-" * 50)
            print(f"💬 Generated Comment to post under eToro Post {post_id}:\n")
            print(clean_text)
            print("-" * 50 + "\n")

            if dry_run:
                print("   [DRY RUN] Skipping actual eToro API call.")
                published_count += 1
                results.append({
                    'ticker': sym,
                    'post_id': post_id,
                    'headline': item['title'],
                    'hash': n_hash,
                    'dry_run': True,
                })
                break
            else:
                if not etoro_client.is_configured():
                    print("   ❌ eToro API not configured. Cannot post comment.")
                    break

                # Pre-flight Gatekeeper Check
                if verify_and_clean_comment:
                    ok_gate, clean_text, audit_info = verify_and_clean_comment(
                        text=clean_text,
                        primary_ticker=sym,
                        run_ai_review=False
                    )
                    if not ok_gate:
                        print(f"   🛑 CATALYST COMMENT BLOCKED BY GATEKEEPER: {audit_info.get('issues')}")
                        continue

                res = etoro_client.add_post_comment(
                    post_id=post_id,
                    message=clean_text,
                    language="it"
                )

                if res.get("success"):
                    c_id = res.get("id")
                    print(f"   ✅ Successfully posted catalyst comment! Comment ID: {c_id}")
                    gist_storage.mark_news_commented(n_hash, sym, post_id, item['title'])
                    published_count += 1
                    results.append({
                        'ticker': sym,
                        'post_id': post_id,
                        'comment_id': c_id,
                        'headline': item['title'],
                        'hash': n_hash,
                    })
                    time.sleep(3)
                    break
                else:
                    print(f"   ❌ Failed to post comment on eToro: {res.get('error')}")

    print("\n" + "=" * 65)
    print(f"🎉 STOCK NEWS COMMENTER FINISHED: {published_count} news comment(s) processed.")
    print("=" * 65)

    return {
        "success": True,
        "comments_published": published_count,
        "results": results
    }


if __name__ == "__main__":
    cli_dry_run = "--dry-run" in sys.argv
    cli_ticker = None
    if "--ticker" in sys.argv:
        idx = sys.argv.index("--ticker")
        if idx + 1 < len(sys.argv):
            cli_ticker = sys.argv[idx + 1]

    run_stock_news_commenter(dry_run=cli_dry_run, specific_ticker=cli_ticker)
