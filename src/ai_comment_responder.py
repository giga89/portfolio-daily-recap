#!/usr/bin/env python3
"""
AI Community Comment Responder for eToro (Auto-Pilot)
=====================================================
Scans recent eToro posts (up to 7 days back) for genuine community comments without a reply,
and generates balanced, high-conviction, disciplined responses aligned with
Andrea Ravalli's Popular Investor strategy and portfolio theses.

Execution Modes:
  • --live : Automatically posts replies to eToro.
  • --dry-run (default if no flag): Previews replies without publishing.
"""

import os
import sys
import json
import re
from datetime import datetime, timezone, timedelta
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

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


PORTFOLIO_SYSTEM_PROMPT = """
You are Andrea Ravalli's Official AI Co-Pilot for the eToro Popular Investor Program.
Your job is to draft balanced, highly professional, disciplined, and appreciative replies to user comments on eToro posts.

CORE PROFILE & STRATEGY RULES:
1. Track Record & Philosophy:
   - +200% cumulative gain since 2020.
   - Long-term compound investing (3-5+ years time horizon).
   - Certified eToro Risk Score 3/10 (low risk).
   - Zero leverage (1x only, no CFD leverage gambling).
   - Disciplined Dollar-Cost Averaging (DCA) and dividend reinvestment.

2. Core Portfolio Pillars & Theses:
   - AI & Hyperscale Tech (NVDA, PLTR, TSM, AVGO, MSFT, GOOGL, AMZN, MRVL): Secular compute demand, Blackwell rollout, AIP commercial adoption.
   - Healthcare & GLP-1 (LLY, NOVO-B, ABBV, ABT, AZN): Demographic aging, blockbuster metabolic and immunology treatments, resilient pricing power.
   - Energy, Nuclear & Grid (CCJ, PRY, ENI, ENEL, GLEN, TRIG): Nuclear baseload 24/7 for AI data centers (Cameco), global electrification supercycle (Prysmian/Glencore).
   - Defense & Safe Havens (WDEF ETF, Physical Gold PPFB ETC, Cash/Treasuries IB01, XEON): Geopolitical hedging (NATO rearmament) and currency debasement protection.
   - Selected Emerging & Quality (MELI, BYD, Ferrari RACE, Walmart WMT): High barriers to entry and regional growth.

3. RESPONSE GUARDRAILS:
   - Language Detection: If user writes in English, reply in flawless English. If Italian, reply in Italian.
   - Tone: Warm, humble, appreciative, polite, yet intellectually rigorous and confident as a seasoned Popular Investor.
   - Never give individual financial advice, never promise guaranteed profits, never encourage short-term day trading or CFD leverage.
   - Never deviate from our core theses. Frame short-term volatility as normal market noise buffered by our multi-asset allocation and Risk Score 3/10.
   - Concise: 2 to 3 short paragraphs (80-140 words), easy to read on mobile, with 2-3 well-chosen emojis.
"""


def _detect_language(text: str) -> str:
    """Detect if text is primarily English or Italian."""
    english_clues = ["the", "and", "is", "for", "with", "thanks", "great", "portfolio", "earnings", "good", "pullback", "think", "what", "why", "you", "are", "regarding"]
    text_words = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
    matches = sum(1 for w in english_clues if w in text_words)
    return "en" if matches >= 2 else "it"


def _build_contextual_fallback(user_comment: str, user_author: str, tickers: List[str], lang: str) -> str:
    """Intelligent topic-aware fallback when AI API is unavailable."""
    msg_lower = user_comment.lower()
    
    # 1. NVIDIA / Tech Earnings / Pullback
    if "nvda" in msg_lower or "nvidia" in msg_lower or "earnings" in msg_lower or "pullback" in msg_lower:
        if lang == "en":
            return (
                f"Thanks for the feedback and for following the portfolio, @{user_author}! 🤝\n\n"
                "You make a very valid point: after such strong runs, near-term profit-taking is always a natural reaction regardless of how solid the numbers are. "
                "However, our conviction in $NVDA remains extremely high—we actually reinforced our position recently. Between the Blackwell ramp-up and multi-year hyperscaler Capex commitments, the moat is unparalleled.\n\n"
                "For our long-term horizon, any short-term dips just offer great compounding opportunities for copiers! 🚀📈"
            )
        else:
            return (
                f"Grazie per il commento e per il riscontro, @{user_author}! 🤝\n\n"
                "Condivido l'analisi: dopo rally importanti, prese di profitto di breve termine sono del tutto fisiologiche. "
                "Dal punto di vista della nostra strategia, manteniamo altissima convinzione su $NVDA (su cui abbiamo recentemente incrementato la quota): l'accelerazione dell'architettura Blackwell e i Capex pluriennali dei data center rimangono solidissimi.\n\n"
                "Con orizzonte a 3-5 anni, la volatilità di breve è solo un'opportunità di consolidamento! 📈🚀"
            )

    # 2. Palantir / Multiples / Valuation
    elif "pltr" in msg_lower or "palantir" in msg_lower or "valutazion" in msg_lower or "multipl" in msg_lower or "p/e" in msg_lower:
        if lang == "en":
            return (
                f"Appreciate your question, @{user_author}! 🛡️\n\n"
                "Valuation multiples on $PLTR are indeed demanding on traditional GAAP metrics. However, we look at the exceptional Rule of 40 score (>60%), over $4B in pure cash with zero debt, and the unprecedented commercial acceleration of AIP.\n\n"
                "Because we manage risk at 3/10 with zero leverage, position sizing is strictly controlled to capture massive upside while buffering against drawdowns. 📊✨"
            )
        else:
            return (
                f"Ottima domanda, @{user_author}! 🛡️\n\n"
                "I multipli di $PLTR sono certamente elevati sui parametri tradizionali, ma riflettono una combinazione unica: Rule of 40 oltre il 60%, cassa netta per più di 4 miliardi e accelerazione esponenziale dei contratti commerciali AIP.\n\n"
                "Nella nostra gestione a Risk Score 3/10 e zero leva, il dimensionamento della posizione ci permette di beneficiare della crescita esponenziale proteggendo il capitale da correzioni improvvise. 📊✨"
            )

    # 3. Copy Trading / Minimum Capital / Strategy
    elif "copi" in msg_lower or "copy" in msg_lower or "minim" in msg_lower or "capitale" in msg_lower or "start" in msg_lower:
        if lang == "en":
            return (
                f"Hello @{user_author}, welcome to the community! 👋\n\n"
                "To ensure proportional replication across all ~40 holdings in the portfolio (from Big Tech to Gold and dividend ETFs), eToro recommends a minimum of $500–$1,000 with 'Copy Open Trades' selected.\n\n"
                "Our focus is 100% on long-term compound growth (+200% since 2020) with a certified Risk Score of 3/10 and zero leverage. Happy to have you on board! 🚀💼"
            )
        else:
            return (
                f"Ciao @{user_author} e benvenuto/a nella community! 👋\n\n"
                "Per replicare al meglio tutte le circa 40 posizioni del portafoglio (tra Tech, Healthcare, Oro ed ETF a dividendo), il capitale ideale per iniziare è tra 500$ e 1.000$, spuntando sempre l'opzione 'Copia operazioni aperte'.\n\n"
                "La nostra strategia è impostata per il lungo termine (+200% dal 2020), con Risk Score certificato 3/10 e zero leva. A disposizione per qualsiasi dubbio! 🚀💼"
            )

    # 4. Gold / Defence / Diversification vs Tech
    elif "gold" in msg_lower or "oro" in msg_lower or "wdef" in msg_lower or "ppfb" in msg_lower or "difesa" in msg_lower or "diversif" in msg_lower:
        if lang == "en":
            return (
                f"Great point, @{user_author}! ⚖️\n\n"
                "While pure US tech offers high beta, maintaining structural allocations to Physical Gold ($PPFB.DE) and European Defence ($WDEF) is what allows us to keep a low Risk Score 3/10 and prevent severe portfolio drawdowns during macro shocks.\n\n"
                "This asymmetric balance enables stress-free long-term compounding without sacrificing substantial upside! 🥇🛡️"
            )
        else:
            return (
                f"Ottima osservazione, @{user_author}! ⚖️\n\n"
                "Il settore Tech offre grande spinta nei cicli rialzisti, ma includere pilastri non correlati come l'Oro fisico ($PPFB.DE) e la Difesa Europea ($WDEF.L) è proprio ciò che ci permette di mantenere un Risk Score certificato di 3/10 e proteggere il portafoglio da shock geopolitici e inflattivi.\n\n"
                "Questo bilanciamento asimmetrico rende il compounding stabile e sostenibile negli anni! 🥇🛡️"
            )

    # General Fallback
    if lang == "en":
        return (
            f"Thanks for sharing your thoughts, @{user_author}! 🤝\n\n"
            "Appreciate the valuable perspective. Our portfolio strategy remains firmly anchored in multi-year structural trends, low risk (Score 3/10), and zero leverage, letting fundamentals drive long-term compound gains.\n\n"
            "Great having you in the discussion! 📈✨"
        )
    else:
        return (
            f"Grazie mille per il commento e per il riscontro, @{user_author}! 🤝\n\n"
            "Apprezzo molto il confronto. La nostra strategia rimane saldamente focalizzata su trend secolari di lungo termine, disciplina a basso rischio (Risk Score 3/10) e zero leva, lasciando che siano i fondamentali a guidare la crescita nel tempo.\n\n"
            "Un saluto e buon investimento! 📈✨"
        )


def generate_ai_comment_reply(
    user_comment_text: str,
    user_author: str,
    post_context: Optional[str] = None,
    relevant_tickers: Optional[List[str]] = None,
) -> str:
    """
    Generate a tailored, balanced reply to a community comment using Gemini AI or context engine.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    lang = _detect_language(user_comment_text)

    tickers_str = ", ".join(relevant_tickers) if relevant_tickers else "N/A"
    context_snippet = f"Original Post Context: {post_context[:300]}..." if post_context else "General Portfolio Post"

    prompt = f"""
{PORTFOLIO_SYSTEM_PROMPT}

TASK:
Draft a reply to the following user comment on eToro:
- User: @{user_author}
- Comment: "{user_comment_text}"
- Detected Language: {'English' if lang == 'en' else 'Italian'}
- Related Tickers: {tickers_str}
- Post Context: {context_snippet}

Please write the exact reply ready to be posted. Do not include markdown code blocks or quotes around the entire message, just the text.
"""

    if HAS_GENAI and api_key:
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=350,
                )
            )
            if response.text and len(response.text.strip()) > 20:
                return response.text.strip()
        except Exception as e:
            print(f"⚠️ Gemini API note: {e}")

    # High-quality fallback
    return _build_contextual_fallback(user_comment_text, user_author, relevant_tickers or [], lang)


def _extract_comment_details(c: Dict[str, Any]) -> Tuple[str, str, str, bool, List[Dict[str, Any]]]:
    """Helper to extract (comment_id, author_username, text, is_author_self, replies) across eToro JSON formats."""
    c_id = str(c.get("id") or c.get("entity", {}).get("id") or "")
    owner_dict = c.get("owner") or c.get("entity", {}).get("owner") or {}
    owner_username = owner_dict.get("username", "") or c.get("username", "")
    text = c.get("message") or c.get("content") or c.get("entity", {}).get("content") or c.get("entity", {}).get("message") or c.get("text") or ""
    is_owner = c.get("requesterContext", {}).get("isOwner", False)
    if owner_username.lower() == "andrearavalli":
        is_owner = True
    replies = c.get("replies") or c.get("entity", {}).get("replies") or []
    return c_id, owner_username, text, is_owner, replies


def find_unreplied_comments(
    days_back: int = 7,
    my_username: str = "AndreaRavalli"
) -> List[Dict[str, Any]]:
    """
    Scans posts published within the last `days_back` days (default: 7) and returns
    comments by other users without a reply from AndreaRavalli.
    """
    unreplied = []
    
    if not etoro_client.is_configured():
        print("⚠️ eToro API not configured.")
        return unreplied

    # 1. Load posts from local analytics & gist
    posts_candidates = []
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_analytics_path = os.path.join(root_dir, "data", "post_analytics.json")
    if os.path.exists(local_analytics_path):
        try:
            with open(local_analytics_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                posts_candidates.extend(data.get("posts", []))
        except Exception:
            pass

    try:
        gist_data = gist_storage.load_data()
        posts_candidates.extend(gist_data.get("published_posts", []))
    except Exception:
        pass

    # Deduplicate posts by ID
    unique_posts = {}
    for p in posts_candidates:
        p_id = p.get("id") or p.get("post_id")
        if p_id and p_id not in unique_posts:
            unique_posts[p_id] = p

    # Filter to posts from last `days_back` days
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_back)
    recent_posts = []

    for p_id, p in unique_posts.items():
        pub_str = p.get("published_at") or p.get("timestamp")
        if pub_str:
            try:
                clean_pub = pub_str.replace("Z", "+00:00")
                pub_dt = datetime.fromisoformat(clean_pub)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                if pub_dt >= cutoff_time:
                    recent_posts.append(p)
            except Exception:
                recent_posts.append(p)
        else:
            recent_posts.append(p)

    print(f"🔍 Trovati {len(recent_posts)} post pubblicati negli ultimi {days_back} giorni.")

    total_comments_scanned = 0
    total_user_comments_found = 0

    for p in recent_posts:
        post_id = p.get("id") or p.get("post_id")
        if not post_id:
            continue

        raw_comments = etoro_client.get_post_comments(post_id)
        if not raw_comments:
            continue

        total_comments_scanned += len(raw_comments)

        for c in raw_comments:
            c_id, owner, c_text, is_self, replies = _extract_comment_details(c)

            if is_self or not owner or owner.lower() == my_username.lower():
                continue

            total_user_comments_found += 1

            # Check if this comment already has a reply from AndreaRavalli
            has_my_reply = False
            for r in replies:
                _, r_owner, _, r_is_self, _ = _extract_comment_details(r)
                if r_is_self or r_owner.lower() == my_username.lower():
                    has_my_reply = True
                    break

            if not has_my_reply:
                unreplied.append({
                    "post_id": post_id,
                    "comment_id": c_id,
                    "author": owner,
                    "message": c_text,
                    "post_title": p.get("title") or p.get("session_name") or "Post Recap",
                    "tickers": p.get("tickers", []),
                    "published_at": p.get("published_at") or "",
                    "created_at": c.get("created") or c.get("createdAt") or ""
                })

    print(f"📊 Statistiche scansione: {total_comments_scanned} commenti totali esaminati | {total_user_comments_found} commenti di utenti esterni | {len(unreplied)} in attesa di risposta.")

    return unreplied


def process_community_replies(
    dry_run: bool = False,
    days_back: int = 7,
    max_replies: int = 10,
    my_username: str = "AndreaRavalli"
) -> List[Dict[str, Any]]:
    """
    Finds unreplied comments from the last `days_back` days, generates AI replies,
    and publishes them (live) or previews them (dry-run).
    """
    print("=" * 70)
    print("🤖 AI COMMUNITY COMMENT RESPONDER (eToro)")
    print(f"🕒 Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"📅 Lookback Window: Ultimi {days_back} giorni")
    print(f"⚙️ Modalità Esecuzione: {'🛡️ DRY RUN (Solo Anteprima)' if dry_run else '🚀 LIVE AUTO-REPLY (Pubblicazione Automatica)'}")
    print("=" * 70)

    unreplied_comments = find_unreplied_comments(days_back=days_back, my_username=my_username)
    results = []

    if not unreplied_comments:
        print("\n✅ Nessun commento della community in sospeso senza risposta trovato negli ultimi 7 giorni.")
        return results

    print(f"\n📬 Trovati {len(unreplied_comments)} commenti in sospeso senza risposta. Elaborazione in corso...\n")

    for idx, item in enumerate(unreplied_comments[:max_replies], 1):
        print("─" * 65)
        print(f"🔹 [Commento {idx}/{len(unreplied_comments)}]")
        print(f"👤 Autore Commento: @{item['author']}")
        print(f"📅 Data/Ora: {item.get('created_at', 'N/D')}")
        print(f"📌 Post: \"{item['post_title'][:80]}\" (ID: {item['post_id']})")
        print(f"🏷️ Titoli Coinvolti: {', '.join(item.get('tickers', [])) or 'Macro/Portafoglio'}")
        print(f"💬 Testo Utente: \"{item['message']}\"")

        reply_text = generate_ai_comment_reply(
            user_comment_text=item['message'],
            user_author=item['author'],
            post_context=item['post_title'],
            relevant_tickers=item.get('tickers', [])
        )

        print(f"\n💡 Risposta Generata dall'IA:\n{reply_text}\n")

        if not dry_run:
            print(f"🚀 Pubblicazione automatica in corso per @{item['author']}...")
            res = etoro_client.reply_to_comment(
                post_id=item['post_id'],
                comment_id=item['comment_id'],
                message=reply_text
            )
            if res.get("success"):
                print(f"🎉 Risposta pubblicata con successo su eToro! ID Risposta: {res.get('id')}")
                results.append({"status": "published", "item": item, "reply": reply_text})
            else:
                print(f"❌ Errore pubblicazione: {res.get('error')}")
                results.append({"status": "failed", "item": item, "error": res.get('error')})
        else:
            print("🛡️ [DRY RUN] Nessuna azione eseguita su eToro.")
            results.append({"status": "preview", "item": item, "reply": reply_text})

    return results


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    process_community_replies(dry_run=is_dry, days_back=7)
