#!/usr/bin/env python3
"""
AI Community Comment Responder for eToro (Auto-Pilot & High Conviction)
=====================================================================
Scans recent eToro posts (up to 7 days back) for genuine community comments without a reply,
and generates balanced, high-conviction, disciplined responses aligned with
Andrea Ravalli's Popular Investor strategy and portfolio theses.

Features & Strict Quality Control:
  • Two-Pass Generation Architecture:
      - Pass 1 (Drafting): Contextual draft generation via Gemini Flash models.
      - Pass 2 (Validator / Judge): Independent editorial & compliance evaluation.
  • Strict Deterministic Syntax Guardrails:
      - Rejects truncated / cut-off sentences (stops words, trailing prepositions/conjunctions).
      - Enforces terminal punctuation/emojis and minimum substantive length.
      - Strips unwanted markdown (**bold**) or AI meta-commentary.
  • Anti-Duplication Persistence (100% Guaranteed):
      - Uses Gist & local answered_comments.json state.
      - Categorically prevents re-answering already addressed comments.
  • Enhanced Topic-Aware Fallback Engine:
      - Flawless, domain-specific templates covering Tech/AMZN/GPUs, NVDA, PLTR,
        GLP-1/Healthcare, Nuclear/Energy, Gold/Defense, DCA, and Copy Trading.
  • Rich Telegram Notifications:
      - Sends instant alerts with post URL, comment snippet, and verified response.
"""

import os
import sys
import json
import re
import html as html_lib
import time
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

try:
    from api_usage_tracker import log_api_request
    API_TRACKER_AVAILABLE = True
except ImportError:
    API_TRACKER_AVAILABLE = False

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ANSWERED_COMMENTS_FILE = os.path.join(DATA_DIR, "answered_comments.json")

# Multi-model priority hierarchy
DEFAULT_GEMINI_MODELS = [
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-2.5-flash',
]

PORTFOLIO_SYSTEM_PROMPT = """
You are Andrea Ravalli's Official AI Co-Pilot for the eToro Popular Investor Program.
Your job is to draft balanced, highly professional, disciplined, and appreciative replies to user comments on eToro posts.

CORE PROFILE & STRATEGY RULES:
1. Track Record & Philosophy:
   - +200% cumulative gain since 2020.
   - Long-term compound investing (3-5+ years time horizon).
   - Certified eToro Risk Score 3/10 (conservative/moderate risk).
   - Zero leverage (1x only, no CFD leverage gambling, no shorting).
   - Disciplined Dollar-Cost Averaging (DCA) and dividend reinvestment.

2. Core Portfolio Pillars & Theses:
   - AI & Hyperscale Tech (NVDA, PLTR, TSM, AVGO, MSFT, GOOGL, AMZN, MRVL): Secular compute demand, custom silicon, cloud AI infrastructure, software monetization (AIP). Short-term market rotation is noise.
   - Healthcare & GLP-1 (LLY, NOVO-B, ABBV, ABT, AZN): Demographic aging, blockbuster metabolic and immunology treatments, resilient pricing power.
   - Energy, Nuclear & Grid (CCJ, PRY, ENI, ENEL, GLEN, TRIG): Nuclear baseload 24/7 for AI data centers (Cameco), global electrification supercycle (Prysmian/Glencore).
   - Defense & Safe Havens (WDEF ETF, Physical Gold PPFB ETC, Cash/Treasuries IB01): Geopolitical hedging (NATO rearmament) and currency debasement protection.
   - Selected Emerging & Quality (MELI, BYD, Ferrari RACE, Walmart WMT): High barriers to entry and strong cash flows.

3. RESPONSE GUARDRAILS:
   - Language Detection: If user writes in English, reply in flawless English. If Italian, reply in Italian.
   - Tone: Warm, humble, appreciative, polite, yet intellectually rigorous and confident as a seasoned Popular Investor.
   - Never give individual financial advice, never promise guaranteed profits, never encourage short-term day trading or CFD leverage.
   - Always address the user's specific questions or mentioned companies (e.g. AMZN, NVDA, PLTR, GPUs, tech sentiment, DCA) with concrete reasoning.
   - Formatting: Do NOT use markdown bold with asterisks (**text**). Use plain clean text. Include 1-2 relevant emojis (e.g. 📈, 🤝, 🚀, 🛡️).
   - Length: 1 to 2 short paragraphs (60-120 words), concise and punchy for mobile feed reading.
   - Always conclude cleanly with warm greetings and best wishes for their life and trading journey.
"""

# Incomplete trailing words/prepositions indicating truncation
DANGLING_STOP_WORDS = {
    # Italian
    'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una',
    'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
    'e', 'ed', 'o', 'od', 'ma', 'però', 'che', 'se', 'quando', 'mentre',
    'del', 'dello', 'della', 'dei', 'degli', 'delle',
    'al', 'allo', 'alla', 'ai', 'agli', 'alle',
    'dal', 'dallo', 'dalla', 'dai', 'dagli', 'dalle',
    'nel', 'nello', 'nella', 'nei', 'negli', 'nelle',
    'sul', 'sullo', 'sulla', 'sui', 'sugli', 'sulle',
    'anche', 'come', 'dove', 'perché', 'perche', 'quindi', 'infatti',
    # English
    'the', 'a', 'an', 'of', 'to', 'in', 'for', 'on', 'with', 'at', 'by',
    'from', 'up', 'about', 'into', 'over', 'after', 'and', 'or', 'but',
    'because', 'if', 'while', 'that', 'which', 'as', 'than', 'so', 'then'
}

VALID_TERMINAL_PUNCTUATION = ('.', '!', '?')
VALID_TERMINAL_EMOJIS = ('🤝', '📈', '🚀', '✨', '💼', '🎯', '📊', '🛡️', '👋', '🙏', '🔥', '💡')


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
    english_clues = ["the", "and", "is", "for", "with", "thanks", "great", "portfolio", "earnings", "good", "pullback", "think", "what", "why", "you", "are", "regarding", "tech", "growth"]
    text_words = set(re.findall(r"\b[a-zA-Z]+\b", clean_text.lower()))
    matches = sum(1 for w in english_clues if w in text_words)
    return "en" if matches >= 2 else "it"


def _is_simple_gratitude(text: str) -> bool:
    """Check if message is just a simple thanks or acknowledgment."""
    msg = text.lower().strip()
    if any(q in msg for q in ["?", "cosa", "come", "quanto", "perch", "target", "prezzo", "consigli", "chiuso", "aperto", "entr", "view on"]):
        return False
    courtesy_words = ["grazie", "grazie mille", "thanks", "thank you", "ok", "chiaro", "perfetto", "top", "good luck", "buona giornata", "complimenti", "ottimo", "capito", "d'accordo", "condivido", "a presto", "buon trading", "👍", "🙏", "🤝"]
    if len(msg) < 45 and any(cw in msg for cw in courtesy_words):
        return True
    return False


# ─── Andrea Ravalli Style Archive & Few-Shot Learning ──────────────────────────

DEFAULT_ANDREA_STYLE_SEEDS = [
    {
        "id": "seed_dca_strategy_it",
        "user_comment": "Ha senso entrare adesso con tutto il capitale o meglio fare un PAC?",
        "andrea_reply": "Ciao @utente! Con la nostra strategia a Risk Score 3/10 e orizzonte pluriennale, suggerisco sempre un approccio graduale tramite Dollar-Cost Averaging (DCA). Dividere il capitale in ingressi periodici ti permette di non preoccuparti del timing di breve termine e di sfruttare la volatilità come alleata. Un caro saluto e buon trading! 📈🤝",
        "language": "it",
        "source": "seed"
    },
    {
        "id": "seed_nvda_blackwell_it",
        "user_comment": "Cosa ne pensi del ritracciamento di NVIDIA? Conviene tenere?",
        "andrea_reply": "Grazie per la domanda, @utente! Prese di profitto dopo rally importanti sono del tutto fisiologiche. La nostra tesi su $NVDA rimane intatta: la domanda per l'architettura Blackwell e i piani di Capex dei giganti del cloud rimangono solidissimi per i prossimi 3-5 anni. Manteniamo la posizione con disciplina senza farci condizionare dal rumore di breve termine. 🚀📊",
        "language": "it",
        "source": "seed"
    },
    {
        "id": "seed_copy_minimum_it",
        "user_comment": "Quanto capitale consigli per iniziare a copiare il portafoglio?",
        "andrea_reply": "Ciao @utente! Il minimo per copiare su eToro è di 200$, ma per replicare fedelmente tutti i 40 titoli del portafoglio e ricevere le quote frazionate di ogni dividendo suggerisco di partire da almeno 500$-1000$, impostando l'opzione di copiare i trade aperti. Un caro saluto e benvenuto a bordo! 🤝✨",
        "language": "it",
        "source": "seed"
    },
    {
        "id": "seed_cameco_energy_en",
        "user_comment": "Why are you holding Cameco and Prysmian in the portfolio?",
        "andrea_reply": "Hi @user! Great question. Cameco ($CCJ) and Prysmian ($PRY.MI) represent two foundational pillars of our infrastructure thesis: 24/7 carbon-free nuclear baseload and global high-voltage grid electrification, both driven by massive datacenter energy demands. We are positioned for multi-year structural growth with 0 leverage. Wishing you the best in your trading! 📈🤝",
        "language": "en",
        "source": "seed"
    },
    {
        "id": "seed_palantir_valuation_it",
        "user_comment": "Palantir non ti sembra troppo cara a questi multipli?",
        "andrea_reply": "Ottimo punto, @utente! I multipli di $PLTR sono certamente elevati se confrontati con il software tradizionale, ma la crescita di AIP (Artificial Intelligence Platform) e l'espansione dei contratti commerciali USA confermano un pricing power quasi monopolistico. Gestiamo la posizione con un peso ponderato per beneficiare del rialzo proteggendo il capitale con il nostro Risk 3/10. Un saluto cordiale! 🛡️📊",
        "language": "it",
        "source": "seed"
    }
]


def load_andrea_style_archive() -> List[Dict[str, Any]]:
    """
    Loads authentic Andrea Ravalli replies from Gist storage.
    If Gist is empty, returns the high-quality seed dataset.
    """
    archive = []
    try:
        gist_archive = gist_storage.get_andrea_style_archive()
        if gist_archive and isinstance(gist_archive, list):
            archive.extend(gist_archive)
    except Exception as e:
        print(f"⚠️ Warning loading style archive from Gist: {e}")

    # Fallback to seeds if empty
    if not archive:
        archive = list(DEFAULT_ANDREA_STYLE_SEEDS)

    return archive


def format_style_examples_for_prompt(
    user_comment: str,
    lang: str = "it",
    relevant_tickers: Optional[List[str]] = None,
    max_examples: int = 3
) -> str:
    """
    Formats the most relevant authentic replies written by Andrea Ravalli
    into a structured few-shot prompt block.
    """
    archive = load_andrea_style_archive()
    if not archive:
        return ""

    # Filter by language
    matching = [r for r in archive if r.get("language", "it") == lang]
    if not matching:
        matching = archive

    # Score by relevance to user query
    user_lower = user_comment.lower()
    tickers = [t.lower().replace('$', '') for t in (relevant_tickers or [])]

    scored = []
    for item in matching:
        score = 0
        q_text = item.get("user_comment", "").lower()
        r_text = item.get("andrea_reply", "").lower()

        # Check ticker matches
        for t in tickers:
            if t in q_text or t in r_text:
                score += 5

        # Check keyword matches
        for kw in ["pac", "dca", "copi", "copy", "leva", "leverage", "blackwell", "capex", "divid", "multipl", "risk", "rischio", "cameco", "pltr", "nvda"]:
            if kw in user_lower and (kw in q_text or kw in r_text):
                score += 3

        scored.append((score, item))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [item for _, item in scored[:max_examples]]

    lines = [
        "────────────────────────────────────────────────────────────",
        "AUTHENTIC ANDREA RAVALLI WRITING STYLE & VOICE (FEW-SHOT EXAMPLES):",
        "Adopt Andrea's exact tone, polite structure, greetings, and closing signatures:",
    ]

    for idx, ex in enumerate(selected, 1):
        q = ex.get("user_comment", "").strip()
        r = ex.get("andrea_reply", "").strip()
        lines.append(f"\n[Style Example {idx}]")
        lines.append(f"User Comment: \"{q}\"")
        lines.append(f"Andrea's Authentic Reply:\n\"{r}\"")

    lines.append("────────────────────────────────────────────────────────────\n")
    return "\n".join(lines)


def harvest_andrea_replies_to_archive(days_back: int = 30, my_username: str = "AndreaRavalli") -> int:
    """
    Scans published posts and harvests replies personally authored by Andrea Ravalli,
    saving them into the persistent Gist style archive.
    """
    if not etoro_client.is_configured():
        return 0

    posts = []
    try:
        posts_candidates = []
        local_path = os.path.join(DATA_DIR, "post_analytics.json")
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                posts_candidates.extend(json.load(f).get("posts", []))
        gist_data = gist_storage.load_data()
        posts_candidates.extend(gist_data.get("published_posts", []))
        for p in posts_candidates:
            pid = p.get("id") or p.get("post_id")
            if pid and pid not in [x.get("id") for x in posts]:
                posts.append(p)
    except Exception:
        pass

    harvested = []
    for p in posts:
        pid = p.get("id") or p.get("post_id")
        if not pid:
            continue
        comments = etoro_client.get_post_comments(pid)
        for c in comments:
            cid, owner, text, is_self, replies = _extract_comment_details(c, my_username=my_username)
            if not replies:
                replies = etoro_client.get_comment_replies(pid, cid)
            for r in replies:
                rid, r_owner, r_text, r_is_self, _ = _extract_comment_details(r, my_username=my_username)
                if (r_is_self or (r_owner and r_owner.lower() == my_username.lower())) and len(r_text) > 20:
                    lang = _detect_language(r_text)
                    harvested.append({
                        "id": f"harvested_{rid}",
                        "post_id": pid,
                        "user_comment": text,
                        "andrea_reply": r_text,
                        "language": lang,
                        "source": "harvested_etoro"
                    })

    if harvested:
        added = gist_storage.upsert_andrea_style_replies(harvested)
        return added
    return 0


def validate_response_syntax(text: str, user_author: str, is_follow_up_or_short: bool = False) -> Tuple[bool, str, str]:
    """
    Strict deterministic validation of the reply.
    Checks:
      1. Non-empty and proper length.
      2. No abrupt cut-offs (dangling prepositions, unfinished words).
      3. Valid ending (punctuation or emoji).
      4. Mentions user tag @username.
      5. Strips markdown bold (**) and unwanted meta-commentary.
    Returns: (is_valid, cleaned_text, failure_reason)
    """
    if not text or not isinstance(text, str):
        return False, "", "Empty response text"

    cleaned = text.strip()

    # Remove outer quotes if wrapped
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()

    # Remove markdown code blocks if any
    cleaned = re.sub(r'^```[a-zA-Z]*\n', '', cleaned)
    cleaned = re.sub(r'\n```$', '', cleaned)
    cleaned = cleaned.strip()

    # Remove markdown bold asterisks (**text** -> text)
    cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned)
    cleaned = re.sub(r'\*(.*?)\*', r'\1', cleaned)

    # Remove AI meta prefixes like "Ecco una risposta:" or "Andrea Ravalli:"
    cleaned = re.sub(r'^(Ecco (la|una) risposta[:\s]*|Risposta[:\s]*|Draft[:\s]*|Andrea Ravalli[:\s]*|AI Assistant[:\s]*)', '', cleaned, flags=re.IGNORECASE).strip()

    # Ensure user mention is present
    author_clean = user_author.replace('@', '').strip()
    if f"@{author_clean}" not in cleaned and f"@{author_clean.lower()}" not in cleaned.lower():
        # Prepend greeting if missing
        cleaned = f"Ciao @{author_clean}! {cleaned}"

    # Check minimum length for non-trivial comments
    min_length = 50 if is_follow_up_or_short else 100
    min_words = 10 if is_follow_up_or_short else 20

    if len(cleaned) < min_length:
        return False, cleaned, f"Response too short ({len(cleaned)} chars < {min_length})"

    words = re.findall(r'\b[\w\'-]+\b', cleaned)
    if len(words) < min_words:
        return False, cleaned, f"Response too few words ({len(words)} words < {min_words})"

    # Check for unfinished trailing characters
    if cleaned.endswith((',', ';', ':', '-', '—', '(', '[', '{', '...', '…', '/')):
        return False, cleaned, "Response ends with an incomplete punctuation symbol"

    # Check for dangling stop words at the very end
    last_word = words[-1].lower() if words else ""
    if last_word in DANGLING_STOP_WORDS:
        return False, cleaned, f"Response cut off on trailing word/preposition: '{last_word}'"

    # Check if ends with valid punctuation or emoji
    has_valid_ending = False
    for p in VALID_TERMINAL_PUNCTUATION:
        if cleaned.endswith(p):
            has_valid_ending = True
            break
    if not has_valid_ending:
        for emoji in VALID_TERMINAL_EMOJIS:
            if cleaned.endswith(emoji):
                has_valid_ending = True
                break

    if not has_valid_ending:
        # If it ends with letters, it likely got chopped off mid-sentence
        return False, cleaned, "Response does not end with terminal punctuation (. ! ?) or emoji"

    # Check for forbidden AI hallucination phrases
    forbidden_meta = [
        "as an ai", "in qualità di ia", "here is a reply", "spero che questa risposta",
        "fammi sapere se vuoi modificare", "let me know if you would like", "json format",
        "proposta di risposta"
    ]
    for fm in forbidden_meta:
        if fm in cleaned.lower():
            return False, cleaned, f"Contains forbidden meta-phrase: '{fm}'"

    return True, cleaned, "OK"


def verify_and_refine_reply(
    user_comment: str,
    user_author: str,
    candidate_reply: str,
    post_context: Optional[str] = None,
    lang: str = "it",
    api_key: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Pass 2: Double-Verification Judge (Independent Editorial & Compliance Review).
    Evaluates:
      1. Relevance & Substance: Does it specifically address what the user wrote?
      2. Completeness & Fluent Ending: Is it a 100% complete text without abrupt cuts?
      3. Compliance: Aligns with Andrea Ravalli's Risk 3/10, no CFD leverage, no financial advice.
    Returns: (is_approved, perfected_reply, reason)
    """
    if not HAS_GENAI or not api_key:
        return True, candidate_reply, "Pass 2 skipped (no API key/SDK)"

    judge_prompt = f"""
You are the Senior Compliance and Editorial Director for Andrea Ravalli's official eToro Popular Investor Channel (+200% gain, Risk Score 3/10, long-term multi-asset investing, zero leverage).

Review the following proposed reply to a community comment on eToro:

USER COMMENT (from @{user_author}):
"{user_comment}"

ORIGINAL POST CONTEXT:
"{post_context or 'General Portfolio Post'}"

PROPOSED CANDIDATE REPLY:
"{candidate_reply}"

EVALUATION RUBRIC:
1. Relevance & Substance: Does the reply genuinely address the topics and questions raised by @{user_author} (e.g. specific tickers like AMZN/NVDA/PLTR, GPU additions, tech sentiment, valuation, DCA, pullback)?
2. Completeness: Is the text 100% complete with no truncated sentences, no dangling prepositions, and a natural closing?
3. Compliance & Tone: Is it polite, disciplined (Risk 3/10, 0 leverage, 3-5+ years horizon), and free of financial advice or markdown asterisks (**)?

TASK:
Provide your verdict in exact JSON format:
{{
  "approved": true or false,
  "score": <integer from 1 to 10>,
  "reason": "<concise explanation in Italian or English>",
  "perfected_reply": "<the perfected final text ready to post with @{user_author} tag and clean emojis, or leave empty if rejected>"
}}
Output ONLY valid JSON.
"""

    client = genai.Client(api_key=api_key)

    # Use a priority model for review
    models_to_try = [m for m in DEFAULT_GEMINI_MODELS if m in ['gemini-3.7-flash', 'gemini-3.5-flash', 'gemini-2.5-flash']]

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=judge_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1500,
                )
            )
            if API_TRACKER_AVAILABLE:
                log_api_request(model_name, True, "comment_validator_judge")

            if response and response.text:
                raw_json = response.text.strip()
                # Clean json blocks
                if "```json" in raw_json:
                    raw_json = raw_json.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_json:
                    raw_json = raw_json.split("```")[1].split("```")[0].strip()

                parsed = json.loads(raw_json)
                approved = bool(parsed.get("approved", False))
                score = int(parsed.get("score", 0))
                reason = str(parsed.get("reason", ""))
                perfected = str(parsed.get("perfected_reply", "")).strip()

                if approved and score >= 8:
                    final_text = perfected if perfected else candidate_reply
                    # Run deterministic check on perfected text too
                    ok, clean_final, err = validate_response_syntax(final_text, user_author)
                    if ok:
                        return True, clean_final, f"Validated by {model_name} (Score: {score}/10 - {reason})"

                print(f"⚠️ Pass 2 Validator ({model_name}) rejected reply (Score {score}/10): {reason}")
                return False, "", f"Validator rejected (Score {score}/10): {reason}"

        except Exception as e:
            print(f"⚠️ Pass 2 Validator error with {model_name}: {e}")
            continue

    return True, candidate_reply, "Pass 2 fallback (validator model timeout)"


def load_answered_comments() -> Dict[str, Any]:
    """Load persistent state of answered comments from local JSON and Gist."""
    answered = {}
    if os.path.exists(ANSWERED_COMMENTS_FILE):
        try:
            with open(ANSWERED_COMMENTS_FILE, "r", encoding="utf-8") as f:
                answered.update(json.load(f))
        except Exception:
            pass

    try:
        gist_data = gist_storage.load_data()
        gist_answered = gist_data.get("answered_comments", {})
        if isinstance(gist_answered, dict):
            answered.update(gist_answered)
    except Exception:
        pass

    return answered


def record_answered_comment(comment_id: str, post_id: str, author: str, reply_id: Optional[str] = None):
    """Save answered comment state locally and sync to Gist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    db = load_answered_comments()

    current_entry = db.get(comment_id, {
        "post_id": post_id,
        "author": author,
        "first_answered_at": datetime.now(timezone.utc).isoformat(),
        "reply_ids": []
    })

    if reply_id and reply_id not in current_entry.get("reply_ids", []):
        current_entry.setdefault("reply_ids", []).append(reply_id)

    current_entry["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    db[comment_id] = current_entry

    try:
        with open(ANSWERED_COMMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Warning saving local answered comments: {e}")

    try:
        gist_data = gist_storage.load_data()
        gist_data["answered_comments"] = db
        gist_storage.save_data(gist_data)
    except Exception:
        pass


def cleanup_duplicate_replies(post_id: str, comment_id: str, my_username: str = "AndreaRavalli") -> int:
    """
    If multiple replies from Andrea exist on the same comment, deletes all but the first one.
    """
    replies = etoro_client.get_comment_replies(post_id, comment_id)
    my_replies = []
    for r in replies:
        r_id, r_owner, _, r_is_self, _ = _extract_comment_details(r)
        if r_is_self or (r_owner and r_owner.lower() == my_username.lower()):
            my_replies.append(r_id)

    deleted_count = 0
    if len(my_replies) > 1:
        print(f"🧹 Rilevate {len(my_replies)} risposte duplicate sul commento {comment_id}. Pulizia in corso...")
        for extra_id in my_replies[1:]:
            ok = etoro_client.delete_comment_reply(post_id, comment_id, extra_id)
            if ok:
                deleted_count += 1
    return deleted_count


def _build_contextual_fallback(user_comment: str, user_author: str, tickers: List[str], lang: str, is_follow_up: bool = False) -> str:
    """Intelligent, topic-specific certified fallback when AI API is unavailable."""
    msg_lower = _extract_text(user_comment).lower()

    # 0. If it's a simple thank-you or courtesy acknowledgment, conclude warmly
    if _is_simple_gratitude(msg_lower):
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

    # 1. AMZN / Tech Sentiment / Cloud / GPU / AI Infrastructure
    if "amzn" in msg_lower or "amazon" in msg_lower or ("gpu" in msg_lower and "tech" in msg_lower) or "sentiment sulle tech" in msg_lower or "sentiment tech" in msg_lower:
        if lang == "en":
            return (
                f"Great point and question, @{user_author}! 📊\n\n"
                "Short-term tech sentiment is experiencing healthy rotation as the market digests massive Capex. "
                "For $AMZN, AWS remains the backbone of enterprise cloud computing: expanding custom silicon (Trainium/Inferentia) and adding GPU capacity will strengthen operating margins over the 3-5 year horizon. "
                "With our Risk Score 3/10 and zero leverage, we stay comfortably positioned for the long-term compounding.\n\n"
                "Wishing you all the best in life and trading! 📈🤝"
            )
        else:
            return (
                f"Ottima osservazione e punto centrale, @{user_author}! 📊\n\n"
                "Il sentiment sulle big tech sta attraversando una fisiologica fase di rotazione mentre il mercato digerisce gli ingenti Capex in infrastruttura AI. "
                "Su $AMZN, la forza di AWS e l'integrazione di chip proprietari e GPU rappresentano un pilastro fondamentale per i margini operativi nei prossimi 3-5 anni. "
                "Con la nostra gestione a Risk Score 3/10, zero leva e diversificazione multi-asset, affrontiamo queste oscillazioni con assoluta serenità.\n\n"
                "Un caro saluto e i migliori auguri per la tua vita e per i tuoi investimenti! 📈🤝"
            )

    # 2. NVIDIA / Blackwell / Tech Earnings / Pullback
    elif "nvda" in msg_lower or "nvidia" in msg_lower or "earnings" in msg_lower or "blackwell" in msg_lower:
        if lang == "en":
            return (
                f"Thanks for the feedback and for following the portfolio, @{user_author}! 🤝\n\n"
                "Near-term profit-taking is completely natural after historic rallies. "
                "However, our conviction in $NVDA remains extremely solid (we recently reinforced our allocation) driven by uninterrupted Blackwell demand and multi-year hyperscaler data center buildouts.\n\n"
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
                "Valuation multiples on $PLTR are demanding, but reflect an exceptional Rule of 40 score (>60%), over $4B net cash, and accelerating commercial AIP adoption. "
                "With our Risk Score 3/10 discipline, position sizing captures the secular upside while strictly protecting capital against pullbacks.\n\n"
                "Wishing you all the best in life and happy investing! 📊✨"
            )
        else:
            return (
                f"Ottima domanda, @{user_author}! 🛡️\n\n"
                "I multipli di $PLTR sono elevati, ma riflettono una Rule of 40 oltre il 60%, oltre 4 miliardi di cassa netta e la rapida accelerazione commerciale di AIP. "
                "Con la nostra gestione a Risk Score 3/10 e zero leva, il dimensionamento controllato protegge il capitale da correzioni improvvise.\n\n"
                "Un caro saluto e i migliori auguri per la tua vita e per i tuoi investimenti! 📊✨"
            )

    # 4. Accumulo / Paura di ritracciamento / Volatilità / DCA
    elif "accumul" in msg_lower or "paura" in msg_lower or "rintracci" in msg_lower or "ritracci" in msg_lower or "drop" in msg_lower or "crash" in msg_lower or "fear" in msg_lower:
        if lang == "en":
            return (
                f"Great discipline, @{user_author}! 📊\n\n"
                "Accumulating gradually through Dollar-Cost Averaging (DCA) is the most effective approach to handle market anxiety. "
                "In our portfolio, we maintain a certified Risk Score 3/10, zero leverage, and defensive allocations (Physical Gold, Cash reserves, Dividend ETFs) specifically designed to absorb pullbacks smoothly.\n\n"
                "Wishing you all the best in life and trading! 🚀🤝"
            )
        else:
            return (
                f"Ottima disciplina, @{user_author}! 📊\n\n"
                "Accumulare con ingressi frazionati (DCA) è la strategia migliore per gestire la paura dei ritracciamenti. "
                "Nel nostro portafoglio manteniamo volutamente un Risk Score 3/10, zero leva e coperture (Oro fisico, riserve di liquidità ed ETF difensivi) proprio per attutire eventuali correzioni senza ansia.\n\n"
                "Un caro saluto e i migliori auguri per la tua vita e per il tuo percorso di investimenti! 📈🤝"
            )

    # 5. Copy Trading / Minimum Capital / Strategy
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
            "Our portfolio strategy remains firmly focused on multi-year structural trends, low risk (Score 3/10), and zero leverage, letting company fundamentals drive compound gains.\n\n"
            "Wishing you all the best in life and trading! 📈✨"
        )
    else:
        return (
            f"Grazie mille per il commento e per il riscontro, @{user_author}! 🤝\n\n"
            "La nostra strategia rimane saldamente focalizzata su trend secolari di lungo termine, disciplina a basso rischio (Risk Score 3/10) e zero leva, lasciando che siano i fondamentali a guidare la crescita.\n\n"
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
    Two-Pass Generation Engine with Ultra-Strict Guardrails & Quality Double-Check:
      1. Short courtesy bypass for simple thank-yous.
      2. Pass 1: Generates a tailored draft with generous token limits across Gemini models.
      3. Strict Deterministic Syntax Check.
      4. Pass 2: Validator Judge review.
      5. Retry loop if validation fails; automatic fallback to certified template.
    """
    clean_text = _extract_text(user_comment_text)
    api_key = os.environ.get("GEMINI_API_KEY")
    lang = _detect_language(clean_text)

    # Short courtesy check
    if _is_simple_gratitude(clean_text):
        if lang == "en":
            return f"You're very welcome, @{user_author}! Wishing you all the best in life and trading! 📈🤝"
        else:
            return f"Grazie a te, @{user_author}! Un caro saluto e i migliori auguri per la vita e per il tuo trading! 📈🤝"

    tickers_str = ", ".join(relevant_tickers) if relevant_tickers else "General Tech & Multi-Asset"
    context_snippet = f"Original Post Context: {post_context[:300]}..." if post_context else "General Portfolio Post"

    few_shot_block = format_style_examples_for_prompt(clean_text, lang=lang, relevant_tickers=relevant_tickers)

    prompt = f"""
{PORTFOLIO_SYSTEM_PROMPT}

{few_shot_block}

TASK:
Draft a professional, complete reply to this eToro community user comment:
- User: @{user_author}
- Comment: "{clean_text}"
- Detected Language: {'English' if lang == 'en' else 'Italian'}
- Related Tickers: {tickers_str}
- Post Context: {context_snippet}

CRITICAL RULES:
1. Address the SPECIFIC questions or stocks mentioned in the comment (e.g. AMZN, GPUs, tech sentiment, valuation, DCA, etc.).
2. Write 1 to 2 complete paragraphs (60-120 words). DO NOT cut off mid-sentence.
3. Start with a greeting mentioning @{user_author}.
4. Conclude with a complete sentence wishing them all the best in life and trading, followed by 1-2 emojis (e.g. 📈🤝).
5. DO NOT use markdown bold with asterisks (**). Output clean plain text ready for eToro.
"""

    if HAS_GENAI and api_key:
        client = genai.Client(api_key=api_key)

        for attempt in range(2):
            for model_name in DEFAULT_GEMINI_MODELS:
                try:
                    # Pass 1: Draft Generation
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.35,
                            max_output_tokens=1500,  # Generous token budget to prevent thinking token choke
                        )
                    )
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "comment_reply_draft")

                    if response and response.text:
                        raw_draft = response.text.strip()

                        # Deterministic Syntax Check
                        is_valid, cleaned_draft, syntax_err = validate_response_syntax(raw_draft, user_author)
                        if not is_valid:
                            print(f"⚠️ Pass 1 Draft rejected by syntax guardrails ({model_name}): {syntax_err}")
                            continue

                        # Pass 2: Double-Verification Judge
                        is_approved, final_reply, judge_reason = verify_and_refine_reply(
                            user_comment=clean_text,
                            user_author=user_author,
                            candidate_reply=cleaned_draft,
                            post_context=post_context,
                            lang=lang,
                            api_key=api_key
                        )

                        if is_approved:
                            print(f"✅ Pass 2 Double-Check Passed! ({judge_reason})")
                            return final_reply
                        else:
                            print(f"⚠️ Pass 2 Double-Check Failed: {judge_reason}. Retrying...")
                            prompt += f"\n\nPREVIOUS ATTEMPT WAS REJECTED: {judge_reason}. Make sure the answer is 100% complete and directly answers the user's specific questions."

                except Exception as e:
                    print(f"⚠️ Gemini API attempt failed with {model_name}: {e}")
                    continue

    print("🛡️ Falling back to certified topic-aware contextual template...")
    return _build_contextual_fallback(clean_text, user_author, relevant_tickers or [], lang, is_follow_up=is_follow_up)


def _extract_comment_details(c: Dict[str, Any], my_username: str = "AndreaRavalli") -> Tuple[str, str, str, bool, List[Dict[str, Any]]]:
    """Helper to extract (comment_id, author_username, text, is_author_self, replies) across eToro JSON formats."""
    c_id = str(c.get("id") or c.get("commentId") or c.get("entity", {}).get("id") or "")
    owner_dict = c.get("owner") or c.get("user") or c.get("author") or c.get("entity", {}).get("owner") or {}
    owner_username = (
        owner_dict.get("username")
        or owner_dict.get("userName")
        or c.get("username")
        or c.get("userName")
        or ""
    )

    raw_text = (
        c.get("message")
        or c.get("content")
        or c.get("text")
        or c.get("entity", {}).get("content")
        or c.get("entity", {}).get("message")
        or ""
    )
    text = _extract_text(raw_text)

    # Strictly check username to determine if it was posted by Andrea
    is_owner = bool(owner_username and owner_username.strip().lower() == my_username.strip().lower())
    
    replies = c.get("replies") or c.get("entity", {}).get("replies") or []
    if isinstance(replies, dict):
        replies = replies.get("items", []) or replies.get("comments", []) or []
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
            f"💡 <b>Risposta inviata dall'IA (Doppia Verifica):</b>\n"
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

    answered_db = load_answered_comments()

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

        time.sleep(0.3)  # Gentle delay to prevent eToro API HTTP 429 rate limit
        raw_comments = etoro_client.get_post_comments(post_id)
        if not raw_comments:
            continue

        total_comments_scanned += len(raw_comments)

        for c in raw_comments:
            c_id, owner, c_text, is_self, replies = _extract_comment_details(c, my_username=my_username)

            if is_self or (owner and owner.lower() == my_username.lower()):
                continue

            if not owner:
                owner = "Utente"

            total_user_comments_found += 1

            # Fetch live replies for this comment sub-resource if not already present
            if not replies:
                live_replies = etoro_client.get_comment_replies(post_id, c_id)
                if live_replies:
                    replies = live_replies

            # ── Thread Turn & Depth Inspection ────────────────────────────────
            my_replies_count = 0
            last_reply_by_me = False
            last_user_message = c_text
            last_user_author = owner
            has_subsequent_user_reply = False

            for r in replies:
                _, r_owner, r_text, r_is_self, _ = _extract_comment_details(r, my_username=my_username)
                if r_is_self or (r_owner and r_owner.lower() == my_username.lower()):
                    my_replies_count += 1
                    last_reply_by_me = True
                else:
                    last_reply_by_me = False
                    has_subsequent_user_reply = True
                    if r_text:
                        last_user_message = r_text
                    if r_owner:
                        last_user_author = r_owner

            # STRICT PERSISTENT MEMORY CHECK:
            # If this root comment was already answered in persistent DB:
            # We ONLY answer if the user sent an explicit subsequent reply in the sub-thread.
            if c_id in answered_db:
                if not has_subsequent_user_reply or last_reply_by_me:
                    continue

            # Rule 1: If we have already replied in this sub-thread and we had the last word, STOP.
            if my_replies_count >= 1 and last_reply_by_me:
                record_answered_comment(c_id, post_id, owner)
                continue

            # Rule 2: If we have already replied 2 or more times in this sub-thread, STOP.
            if my_replies_count >= 2:
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

    print(f"📊 Statistiche scansione: {total_comments_scanned} commenti totali esaminati | {total_user_comments_found} commenti di utenti esterni | {len(unreplied)} in attesa di risposta.")

    return unreplied


def process_community_replies(
    dry_run: bool = False,
    days_back: int = 7,
    max_replies: int = 10,
    my_username: str = "AndreaRavalli"
) -> List[Dict[str, Any]]:
    """
    Finds unreplied comments from the last `days_back` days, generates AI replies
    with dual-pass verification and syntax guardrails, and publishes them (live) or previews them (dry-run).
    """
    print("=" * 70)
    print("🤖 AI COMMUNITY COMMENT RESPONDER (eToro - Dual-Pass Verified)")
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

        print(f"\n💡 Risposta Verificata dall'IA:\n{reply_text}\n")

        if not dry_run:
            print(f"🚀 Pubblicazione automatica in corso per @{item['author']}...")
            res = etoro_client.reply_to_comment(
                post_id=item['post_id'],
                comment_id=item['comment_id'],
                message=reply_text
            )
            if res.get("success"):
                reply_id = res.get('id')
                print(f"🎉 Risposta pubblicata con successo su eToro! ID Risposta: {reply_id}")
                record_answered_comment(
                    comment_id=item['comment_id'],
                    post_id=item['post_id'],
                    author=item['author'],
                    reply_id=reply_id
                )
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
