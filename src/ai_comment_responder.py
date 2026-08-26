#!/usr/bin/env python3
"""
AI Community Comment Responder for eToro (Auto-Pilot)
=====================================================
Scans recent eToro posts (up to 7 days back) for genuine community comments without a reply,
and generates balanced, high-conviction, disciplined responses aligned with
Andrea Ravalli's Popular Investor strategy and portfolio theses.

Features:
  • Scans eToro posts from the last 7 days.
  • Automatically filters out self-comments and already-answered threads.
  • Strict conversation depth control (max 1-2 turns): never drags discussions out.
  • Concludes gracefully with warm wishes for life and trading/investing.
  • Uses Gemini AI (with contextual fallback) to craft concise, disciplined responses.
  • Automatically publishes replies on eToro (in live mode).
  • Sends instant rich Telegram notifications quoting the comment, post, URL, and reply.
"""

import os
import sys
import json
import re
import html as html_lib
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
import telegram_sender

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

4. CONVERSATION DEPTH & CLOSING RULES:
   - Do NOT drag discussions into long, repetitive back-and-forth threads.
   - If this is a follow-up reply or if there isn't much substantive left to add, keep the response brief (1-2 sentences) and conclude cleanly with a warm greeting and best wishes for their life and trading journey (e.g. "Un caro saluto e i migliori auguri per la vita e per il tuo trading! 📈🤝" / "Wishing you all the best in life and trading! 📈🤝").
   - Max length: 1 to 2 short paragraphs (50-100 words), easy to read on mobile, with 2 well-chosen emojis.
"""


def _extract_text(obj: Any) -> str:
    """Safely extracts plain string text from string, dict, or nested structure."""
    if isinstance(obj, str):
        return obj.strip()
    if isinstance(obj, dict):
        return str(obj.get("text") or obj.get("content") or obj.get("message") or "").strip()
    return str(obj or "").strip()


def _detect_language(text: str) -> str:
    """Detect if text is primarily English or Italian."""
    clean_text = _extract_text(text)
    english_clues = ["the", "and", "is", "for", "with", "thanks", "great", "portfolio", "earnings", "good", "pullback", "think", "what", "why", "you", "are", "regarding"]
    text_words = set(re.findall(r"\b[a-zA-Z]+\b", clean_text.lower()))
    matches = sum(1 for w in english_clues if w in text_words)
    return "en" if matches >= 2 else "it"


def _is_simple_gratitude(text: str) -> bool:
    """Check if message is just a simple thanks or acknowledgment."""
    msg = text.lower().strip()
    courtesy_words = ["grazie", "grazie mille", "thanks", "thank you", "ok", "chiaro", "perfetto", "top", "good luck", "buona giornata", "ottimo", "capito", "d'accordo", "condivido", "👍", "🙏", "🤝"]
    if len(msg) < 35 and any(cw in msg for cw in courtesy_words):
        return True
    return False


def _build_contextual_fallback(user_comment: str, user_author: str, tickers: List[str], lang: str, is_follow_up: bool = False) -> str:
    """Intelligent topic-aware fallback when AI API is unavailable."""
    msg_lower = _extract_text(user_comment).lower()
    
    # 0. If it's a follow-up or simple thank-you, conclude warmly
    if is_follow_up or _is_simple_gratitude(msg_lower):
        if lang == "en":
            return (
                f"You're very welcome, @{user_author}! 🤝\n\n"
                "Wishing you all the best in life and in your trading journey! Happy compounding! 📈✨"
            )
        else:
            return (
                f"Grazie a te, @{user_author}! 🤝\n\n"
                "Un caro saluto e i migliori auguri per la tua vita e per il tuo trading! A presto! 📈✨"
            )

    # 1. Accumulo / Paura di ritracciamento / Volatilità / DCA
    if "accumul" in msg_lower or "paura" in msg_lower or "rintracci" in msg_lower or "ritracci" in msg_lower or "drop" in msg_lower or "crash" in msg_lower or "fear" in msg_lower:
        if lang == "en":
            return (
                f"Great discipline, @{user_author}! 📊\n\n"
                "Accumulating gradually through Dollar-Cost Averaging (DCA) is the best way to handle market anxiety. "
                "In our portfolio, we maintain a certified Risk Score 3/10, zero leverage, and defensive allocations (Gold, Cash reserves, Dividend ETFs) specifically designed to absorb any sharp pullbacks.\n\n"
                "Wishing you all the best in life and trading! 🚀🤝"
            )
        else:
            return (
                f"Ottima disciplina, @{user_author}! 📊\n\n"
                "Accumulare con ingressi frazionati (DCA) è la strategia migliore per gestire la paura dei ritracciamenti. "
                "Nel nostro portafoglio manteniamo volutamente un Risk Score 3/10, zero leva e coperture (Oro fisico, riserve di liquidità ed ETF a dividendo) proprio per attutire eventuali correzioni senza ansia.\n\n"
                "Un caro saluto e i migliori auguri per la tua vita e per il tuo percorso di investimenti! 📈🤝"
            )

    # 2. NVIDIA / Tech Earnings / Pullback
    elif "nvda" in msg_lower or "nvidia" in msg_lower or "earnings" in msg_lower or "pullback" in msg_lower:
        if lang == "en":
            return (
                f"Thanks for the feedback and for following the portfolio, @{user_author}! 🤝\n\n"
                "Near-term profit-taking is always a natural reaction after huge runs. "
                "However, our conviction in $NVDA remains extremely high (we actually reinforced the position recently) thanks to the Blackwell ramp-up and multi-year data center Capex.\n\n"
                "Wishing you the very best in life and trading! 🚀📈"
            )
        else:
            return (
                f"Grazie per il commento e per il riscontro, @{user_author}! 🤝\n\n"
                "Prese di profitto di breve termine sono del tutto fisiologiche dopo rally importanti. "
                "Manteniamo altissima convinzione su $NVDA (su cui abbiamo recentemente incrementato la quota): l'accelerazione dell'architettura Blackwell e i Capex dei data center rimangono solidissimi.\n\n"
                "Un saluto cordiale e i migliori auguri per la vita e per il tuo trading! 📈🚀"
            )

    # 3. Palantir / Multiples / Valuation
    elif "pltr" in msg_lower or "palantir" in msg_lower or "valutazion" in msg_lower or "multipl" in msg_lower or "p/e" in msg_lower:
        if lang == "en":
            return (
                f"Appreciate your question, @{user_author}! 🛡️\n\n"
                "Valuation multiples on $PLTR are indeed demanding, but reflect an exceptional Rule of 40 score (>60%), over $4B net cash, and accelerating commercial AIP adoption. "
                "With our Risk Score 3/10 discipline, position sizing captures the upside while protecting against drawdowns.\n\n"
                "Wishing you all the best in life and happy investing! 📊✨"
            )
        else:
            return (
                f"Ottima domanda, @{user_author}! 🛡️\n\n"
                "I multipli di $PLTR sono elevati, ma riflettono una Rule of 40 oltre il 60%, oltre 4 miliardi di cassa netta e la rapida accelerazione commerciale di AIP. "
                "Con la nostra gestione a Risk Score 3/10 e zero leva, il dimensionamento controllato protegge il capitale da correzioni improvvise.\n\n"
                "Un caro saluto e i migliori auguri per la tua vita e per i tuoi investimenti! 📊✨"
            )

    # 4. Copy Trading / Minimum Capital / Strategy
    elif "copi" in msg_lower or "copy" in msg_lower or "minim" in msg_lower or "capitale" in msg_lower or "start" in msg_lower:
        if lang == "en":
            return (
                f"Hello @{user_author}, welcome to the community! 👋\n\n"
                "To ensure proportional replication across all ~40 portfolio positions, eToro recommends $500–$1,000 with 'Copy Open Trades' selected. "
                "Our focus is 100% on long-term compounding (+200% since 2020) with Risk Score 3/10 and zero leverage.\n\n"
                "Wishing you great success in life and trading! 🚀💼"
            )
        else:
            return (
                f"Ciao @{user_author} e benvenuto/a nella community! 👋\n\n"
                "Per replicare al meglio tutte le circa 40 posizioni del portafoglio, il capitale ideale per iniziare è tra 500$ e 1.000$, con spunta su 'Copia operazioni aperte'. "
                "La nostra strategia punta al lungo termine (+200% dal 2020) con Risk Score 3/10 e zero leva.\n\n"
                "Un caloroso saluto e i migliori auguri per il tuo percorso di investimenti! 🚀💼"
            )

    # General Fallback
    if lang == "en":
        return (
            f"Thanks for sharing your thoughts, @{user_author}! 🤝\n\n"
            "Our portfolio strategy remains firmly focused on multi-year structural trends, low risk (Score 3/10), and zero leverage, letting fundamentals drive compound gains.\n\n"
            "Wishing you all the best in life and trading! 📈✨"
        )
    else:
        return (
            f"Grazie mille per il commento, @{user_author}! 🤝\n\n"
            "La nostra strategia rimane saldamente focalizzata su trend secolari di lungo termine, disciplina a basso rischio (Risk Score 3/10) e zero leva.\n\n"
            "Un caro saluto e i migliori auguri per la tua vita e per il tuo trading! 📈✨"
        )


def generate_ai_comment_reply(
    user_comment_text: str,
    user_author: str,
    post_context: Optional[str] = None,
    relevant_tickers: Optional[List[str]] = None,
    is_follow_up: bool = False,
) -> str:
    """
    Generate a tailored, balanced reply to a community comment using Gemini AI or context engine.
    """
    clean_text = _extract_text(user_comment_text)
    api_key = os.environ.get("GEMINI_API_KEY")
    lang = _detect_language(clean_text)

    # Short courtesy check
    if _is_simple_gratitude(clean_text) or is_follow_up:
        if lang == "en":
            return f"You're very welcome, @{user_author}! Wishing you all the best in life and trading! 📈🤝"
        else:
            return f"Grazie a te, @{user_author}! Un caro saluto e i migliori auguri per la vita e per il tuo trading! 📈🤝"

    tickers_str = ", ".join(relevant_tickers) if relevant_tickers else "N/A"
    context_snippet = f"Original Post Context: {post_context[:300]}..." if post_context else "General Portfolio Post"
    follow_up_hint = "NOTE: This is a concise follow-up reply. Conclude the discussion cleanly with best wishes for their life and trading." if is_follow_up else "NOTE: First reply. Keep it concise, balanced, and conclude with warm best wishes."

    prompt = f"""
{PORTFOLIO_SYSTEM_PROMPT}

TASK:
Draft a reply to the following user comment on eToro:
- User: @{user_author}
- Comment: "{clean_text}"
- Detected Language: {'English' if lang == 'en' else 'Italian'}
- Related Tickers: {tickers_str}
- Post Context: {context_snippet}
- Instruction: {follow_up_hint}

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
                    max_output_tokens=250,
                )
            )
            if response.text and len(response.text.strip()) > 15:
                return response.text.strip()
        except Exception as e:
            print(f"⚠️ Gemini API note: {e}")

    # High-quality fallback
    return _build_contextual_fallback(clean_text, user_author, relevant_tickers or [], lang, is_follow_up=is_follow_up)


def _extract_comment_details(c: Dict[str, Any]) -> Tuple[str, str, str, bool, List[Dict[str, Any]]]:
    """Helper to extract (comment_id, author_username, text, is_author_self, replies) across eToro JSON formats."""
    c_id = str(c.get("id") or c.get("entity", {}).get("id") or "")
    owner_dict = c.get("owner") or c.get("entity", {}).get("owner") or {}
    owner_username = owner_dict.get("username", "") or c.get("username", "")
    
    raw_text = c.get("message") or c.get("content") or c.get("entity", {}).get("content") or c.get("entity", {}).get("message") or c.get("text") or ""
    text = _extract_text(raw_text)
    
    is_owner = c.get("requesterContext", {}).get("isOwner", False)
    if owner_username.lower() == "andrearavalli":
        is_owner = True
    replies = c.get("replies") or c.get("entity", {}).get("replies") or []
    return c_id, owner_username, text, is_owner, replies


def format_post_description(item: Dict[str, Any]) -> Tuple[str, str]:
    """Format human-readable post description like 'Apertura US del giorno 26/08/2026'."""
    pub_str = item.get("published_at", "")
    date_formatted = ""
    if pub_str:
        try:
            clean = pub_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean)
            date_formatted = dt.strftime("%d/%m/%Y")
        except Exception:
            date_formatted = pub_str[:10]
    
    session = item.get("session_name") or item.get("post_title") or "Post Recap"
    clean_title = re.sub(r'[\r\n]+', ' ', session).strip()
    if len(clean_title) > 60:
        clean_title = clean_title[:57] + "..."
        
    desc = f"{clean_title}"
    if date_formatted:
        desc += f" del giorno {date_formatted}"
    return desc, date_formatted


def send_telegram_comment_notification(
    item: Dict[str, Any],
    reply_text: str
) -> bool:
    """
    Sends a rich Telegram notification when the AI answers a community comment.
    """
    try:
        post_desc, _ = format_post_description(item)
        post_id = item.get("post_id", "")
        post_url = f"https://www.etoro.com/posts/{post_id}" if post_id else "https://www.etoro.com/people/AndreaRavalli"

        author = item.get("author", "Utente")
        user_msg = item.get("message", "").strip()

        safe_author = html_lib.escape(author)
        safe_desc = html_lib.escape(post_desc)
        safe_user_msg = html_lib.escape(user_msg)
        safe_reply = html_lib.escape(reply_text)

        tg_message = (
            f"🤖 <b>Nuova Risposta Automatica su eToro!</b>\n\n"
            f"📌 <b>Post:</b> {safe_desc}\n"
            f"🔗 <b>Link Post:</b> <a href=\"{post_url}\">{post_url}</a>\n\n"
            f"👤 <b>Commento di:</b> @{safe_author}\n"
            f"💬 <b>Messaggio Utente:</b>\n<i>\"{safe_user_msg}\"</i>\n\n"
            f"💡 <b>Risposta inviata dall'IA:</b>\n"
            f"{safe_reply}"
        )

        ok = telegram_sender.send_telegram_message(tg_message)
        if ok:
            print(f"📱 Notifica Telegram inviata con successo per @{author}!")
        else:
            print(f"⚠️ Invio notifica Telegram non riuscito per @{author}.")
        return ok
    except Exception as e:
        print(f"⚠️ Errore durante l'invio della notifica Telegram: {e}")
        return False


def find_unreplied_comments(
    days_back: int = 7,
    my_username: str = "AndreaRavalli"
) -> List[Dict[str, Any]]:
    """
    Scans posts published within the last `days_back` days (default: 7) and returns
    comments by other users needing a reply (max 1-2 turns per thread).
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

            # ── Thread Turn & Depth Inspection ────────────────────────────────
            my_replies_count = 0
            last_reply_by_me = False
            last_user_message = c_text
            last_user_author = owner

            for r in replies:
                _, r_owner, r_text, r_is_self, _ = _extract_comment_details(r)
                if r_is_self or r_owner.lower() == my_username.lower():
                    my_replies_count += 1
                    last_reply_by_me = True
                else:
                    last_reply_by_me = False
                    if r_text:
                        last_user_message = r_text
                    if r_owner:
                        last_user_author = r_owner

            # Rule 1: If we have already replied 2 or more times in this sub-thread, STOP.
            if my_replies_count >= 2:
                continue

            # Rule 2: If we replied last, wait for the user (nothing to answer)
            if last_reply_by_me:
                continue

            # Rule 3: Determine if this is a follow-up (turn 2)
            is_follow_up = (my_replies_count == 1)

            unreplied.append({
                "post_id": post_id,
                "comment_id": c_id,
                "author": last_user_author,
                "message": last_user_message,
                "post_title": p.get("title") or p.get("session_name") or "Post Recap",
                "session_name": p.get("session") or p.get("session_name") or "",
                "tickers": p.get("tickers", []),
                "published_at": p.get("published_at") or "",
                "created_at": c.get("created") or c.get("createdAt") or "",
                "is_follow_up": is_follow_up,
                "turn": my_replies_count + 1
            })

    print(f"📊 Statistiche scansione: {total_comments_scanned} commenti totali esaminati | {total_user_comments_found} commenti di utenti esterni | {len(unreplied)} in attesa di risposta (entro il limite turni).")

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
        print(f"🔹 [Commento {idx}/{len(unreplied_comments)}] (Turno: {item.get('turn', 1)}/2 | Follow-up: {item.get('is_follow_up', False)})")
        print(f"👤 Autore Commento: @{item['author']}")
        print(f"📅 Data/Ora: {item.get('created_at', 'N/D')}")
        print(f"📌 Post: \"{item['post_title'][:80]}\" (ID: {item['post_id']})")
        print(f"🏷️ Titoli Coinvolti: {', '.join(item.get('tickers', [])) or 'Macro/Portafoglio'}")
        print(f"💬 Testo Utente: \"{item['message']}\"")

        reply_text = generate_ai_comment_reply(
            user_comment_text=item['message'],
            user_author=item['author'],
            post_context=item['post_title'],
            relevant_tickers=item.get('tickers', []),
            is_follow_up=item.get('is_follow_up', False)
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
                send_telegram_comment_notification(item, reply_text)
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
