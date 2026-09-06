#!/usr/bin/env python3
"""
AI News Generator
Generates market news recap using Google Gemini API
"""

import os
import time
import re
from datetime import datetime
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️  google-genai not installed, AI news generation will be disabled")

from config import PORTFOLIO_TICKERS

# Import Gist storage module
try:
    from gist_storage import load_data, save_data, load_recap_history, save_to_history
    GIST_STORAGE_AVAILABLE = True
except ImportError:
    GIST_STORAGE_AVAILABLE = False
    print("⚠️  gist_storage module not available, using fallback")

# Import API usage tracker
try:
    from api_usage_tracker import log_api_request, save_usage_report
    API_TRACKER_AVAILABLE = True
except ImportError:
    API_TRACKER_AVAILABLE = False
    print("⚠️  api_usage_tracker module not available, usage tracking disabled")

# Maximum number of $ tags per post
MAX_TAGS_PER_POST = 4

# Default Gemini models in priority order (Smartest -> Standard fallback).
# Each model belongs to an independent Free Tier quota bucket (20 RPD each).
DEFAULT_GEMINI_MODELS = [
    'gemini-3.7-flash',       # Most intelligent & capable (5 RPM, 20 RPD)
    'gemini-3.6-flash',       # High capability 3.x series (5 RPM, 20 RPD)
    'gemini-3.5-flash',       # Advanced financial context & reasoning (5 RPM, 20 RPD)
    'gemini-2.5-flash',       # Robust standard model (5 RPM, 20 RPD)
]
try:
    from ai_model_cascade import DEFAULT_GEMINI_MODELS
except ImportError:
    try:
        from src.ai_model_cascade import DEFAULT_GEMINI_MODELS
    except ImportError:
        DEFAULT_GEMINI_MODELS = [
            'gemini-3.1-pro-preview', # Flagship Deep Reasoning model (Best quality)
            'gemini-3.8-flash',       # Newest Flagship Flash model
            'gemini-3.7-flash',       # Most intelligent & capable
            'gemini-3.6-flash',       # High capability 3.x series
            'gemini-3.5-flash',       # Advanced financial context & reasoning
            'gemini-2.5-flash',       # Robust standard model
        ]



def _throttle_request(delay: float = 2.0):
    """Sleep briefly between API requests to avoid breaching RPM limits on Free Tier."""
    time.sleep(delay)

# Valid eToro symbols for tagging (only use these in posts)
# These are confirmed to exist on eToro platform
# Exclude Russian stocks (sanctioned/untradeable)
_EXCLUDED_FROM_TAGS = {'MNODL.L', 'NVTKL.L'}
ETORO_VALID_SYMBOLS = [t for t in PORTFOLIO_TICKERS.keys() if t not in _EXCLUDED_FROM_TAGS]


def _get_all_portfolio_tags():
    """Get all valid portfolio ticker tags for eToro"""
    # Map to eToro symbols (keys of PORTFOLIO_TICKERS), excluding Russian stocks
    return [t for t in PORTFOLIO_TICKERS.keys() if t not in _EXCLUDED_FROM_TAGS]


def _select_tags_for_rotation(max_tags=MAX_TAGS_PER_POST, excluded_tags=None, allowed_tickers=None):
    """
    Select tags for the current post with rotation to ensure variety.
    
    Args:
        max_tags: Maximum number of tags to select
        excluded_tags: List of tags to exclude (e.g. already used in this post)
        allowed_tickers: Optional list of tickers to restrict the selection to
    
    Returns:
        list: List of selected tags
    """
    all_tags = _get_all_portfolio_tags()
    
    if allowed_tickers:
        allowed_normalized = [t.replace('.', '').upper() for t in allowed_tickers]
        all_tags = [t for t in all_tags if t.replace('.', '').upper() in allowed_normalized]
    
    if excluded_tags:
        # Remove excluded tags from candidates
        excluded_normalized = [t.replace('.', '').upper() for t in excluded_tags]
        all_tags = [t for t in all_tags if t.replace('.', '').upper() not in excluded_normalized]
    
    if max_tags <= 0:
        return []

    try:
        data = load_data()
        used_tags = data.get('used_tags', [])

        # Prioritize tags that haven't been used recently
        unused_tags = [tag for tag in all_tags if tag not in used_tags]

        if len(unused_tags) >= max_tags:
            selected = unused_tags[:max_tags]
        elif unused_tags:
            # Not enough unused — fill the gap from all_tags (least-recently-used first)
            already = set(unused_tags)
            filler = [t for t in all_tags if t not in already]
            selected = unused_tags + filler[:max_tags - len(unused_tags)]
        else:
            # All tags recently used — just take from the full list
            selected = all_tags[:max_tags]

        # Guarantee we always return exactly max_tags (safety net: pool was too small)
        if len(selected) < max_tags:
            # all_tags already had excluded_tags stripped; ignore excluded to fill
            full_pool = _get_all_portfolio_tags()
            if allowed_tickers:
                allowed_normalized = [t.replace('.', '').upper() for t in allowed_tickers]
                full_pool = [t for t in full_pool if t.replace('.', '').upper() in allowed_normalized]
            extra = [t for t in full_pool if t not in selected]
            selected = selected + extra[:max_tags - len(selected)]

        # Update used-tags rotation history (keep last 2 full rounds)
        new_used = used_tags + selected
        max_history = len(_get_all_portfolio_tags()) * 2
        data['used_tags'] = new_used[-max_history:] if len(new_used) > max_history else new_used

        save_data(data)

        return selected

    except Exception as e:
        print(f"⚠️ Error in tag rotation: {e}")
        return all_tags[:max_tags]


def _is_valid_ticker(tag):
    """Check if a tag looks like a valid stock/index ticker after normalization"""
    tag_upper = tag.upper()
    if not (1 <= len(tag_upper) <= 10):
        return False
    # Must be uppercase alphanumeric, dots, or hyphens
    return bool(re.match(r'^[A-Z0-9\-\.]+$', tag_upper))


def _limit_tags_in_text(text, allowed_tags, max_tags=MAX_TAGS_PER_POST):
    """
    Ensure text has at most max_tags $ symbols, and only uses allowed tags.
    Allows at most 1 dynamic trending stock/index tag not in allowed_tags,
    as long as it looks like a valid ticker and fits in the total tag budget.
    
    Args:
        text: The generated text
        allowed_tags: List of allowed portfolio tag symbols (without $)
        max_tags: Maximum number of tags to keep
    
    Returns:
        str: Text with limited and validated tags
    """
    # Find all $ tags in the text
    tag_pattern = r'\$([A-Za-z0-9\-\.]+)'
    
    tags_found = []
    trending_found = False
    
    def tag_replacer(match):
        nonlocal trending_found
        tag = match.group(1)
        # Normalize tag (remove dots and hyphens for comparison)
        tag_normalized = tag.replace('.', '').replace('-', '').upper()
        
        # 1. Check if it's an allowed portfolio tag
        matched_portfolio_tag = None
        for t in allowed_tags:
            if t.replace('.', '').replace('-', '').upper() == tag_normalized:
                matched_portfolio_tag = t
                break
                
        if matched_portfolio_tag:
            # Avoid duplicate tagging of the same symbol in a single post
            if matched_portfolio_tag not in tags_found and len(tags_found) < max_tags:
                tags_found.append(matched_portfolio_tag)
                # Ensure a space before and after the tag as requested by the user
                return f' ${matched_portfolio_tag} '
            else:
                # Exceeded max tags or duplicate, remove the $ prefix
                return matched_portfolio_tag
                
        # 2. Check if it's a valid trending index/stock tag (allow at most 1)
        if not trending_found and _is_valid_ticker(tag):
            tag_upper = tag.upper()
            if tag_upper not in tags_found and len(tags_found) < max_tags:
                tags_found.append(tag_upper)
                trending_found = True
                return f' ${tag_upper} '
            else:
                return tag_upper
                
        # Not allowed, remove the $ prefix
        return tag
            
    result = re.sub(tag_pattern, tag_replacer, text)
    # Collapse multiple spaces created by padding tags into a single space
    result = re.sub(r' +', ' ', result)
    return result


def _remove_intro_text(text):
    """
    Remove introductory sentences that Gemini sometimes adds before the Market Overview.
    Examples: "Here is your concise daily market recap for today, YYYY-MM-DD:"
    
    Args:
        text: The full recap text
    
    Returns:
        str: Text with intro removed
    """
    # Pattern to match common intro formats
    # Match lines that start with "Here is" or similar until the first real section
    intro_patterns = [
        r'^Here is .*?\n+',
        r'^Below is .*?\n+',
        r'^Here\'s .*?\n+',
    ]
    
    cleaned_text = text
    for pattern in intro_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Also remove any leading whitespace after removal
    return cleaned_text.lstrip()


def sanitize_etoro_cashtags(text: str) -> str:
    """
    Ensure all $TICKER cashtags are properly isolated with whitespace on eToro.
    eToro requires cashtags (e.g. $AAPL, $ENEL.MI) to not be enclosed in parentheses or asterisks
    e.g. ($ENEL.MI) -> $ENEL.MI, **$NVDA** -> $NVDA
    and not immediately glued to punctuation e.g. $IBE.MC. -> $IBE.MC .
    """
    if not text:
        return text
    # 1. Ensure space before '$' if attached to a letter/number
    text = re.sub(r'([A-Za-z0-9_])(\$[A-Za-z0-9])', r'\1 \2', text)
    
    # 2. Remove markdown asterisks around cashtags: **$TICKER** -> $TICKER
    text = re.sub(r'\*\*\s*(\$[A-Za-z0-9.\-_]+)\s*\*\*', r' \1 ', text)
    text = re.sub(r'\*\s*(\$[A-Za-z0-9.\-_]+)\s*\* ', r' \1 ', text)

    # 3. Remove enclosing parentheses or brackets around cashtags: ($TICKER) -> $TICKER
    text = re.sub(r'\(\s*(\$[A-Za-z0-9.\-_]+)\s*\)', r' \1 ', text)
    text = re.sub(r'\[\s*(\$[A-Za-z0-9.\-_]+)\s*\]', r' \1 ', text)
    text = re.sub(r'\(\s*(\$[A-Za-z0-9.\-_]+)', r'( \1', text)
    text = re.sub(r'(\$[A-Za-z0-9.\-_]+)\s*\)', r'\1 )', text)
    
    # 4. Separate punctuation immediately glued to the end of a cashtag (?, !, ,, :, ;)
    text = re.sub(r'(\$[A-Za-z0-9.\-_]+)([?!,:;])', r'\1 \2', text)
    
    # 5. Handle trailing period at end of cashtag (e.g. '$ENEL.MI.' or '$NVDA.')
    text = re.sub(r'(\$[A-Za-z0-9\-_]+(?:\.[A-Za-z0-9\-_]+)*)\.(\s|$)', r'\1 .\2', text)
    
    # 6. Clean up any excess spaces while preserving newlines
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.split('\n')]
    return '\n'.join(lines)


def _clean_robotic_phrases(text: str) -> str:
    """
    Remove unnatural, robotic self-introductions such as:
    - 'Come Andrea Ravalli, monitoro costantemente...'
    - 'Come Andrea Ravalli, ...'
    - 'In qualità di Andrea Ravalli...'
    - 'Io sono Andrea Ravalli...'
    And strip any '@AndreaRavalli' mentions that generate notifications to followers.
    Also strips markdown asterisks and ensures cashtags are isolated and taggable on eToro.
    """
    if not text:
        return text

    # Remove markdown bold/italic asterisks & underscores (**text**, __text__, *text*)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"__(.*?)__", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\w)\*([^\*\n]+)\*(?!\w)", r"\1", text)
    text = text.replace("**", "")

    patterns = [
        (r"(?i)@AndreaRavalli\b", ""),
        (r"(?i)@andrearavalli\b", ""),
        (r"(?i)Come\s+Andrea\s+Ravalli[,\s]+(io\s+)?(monitoro|gestisco|investo|seguo|ritengo|credo|osservo)?\s*", r"\2 "),
        (r"(?i)Come\s+Andrea\s+Ravalli[,\s]*", ""),
        (r"(?i)In\s+qualit[àa]\s+di\s+Andrea\s+Ravalli[,\s]*", ""),
        (r"(?i)Io\s+sono\s+Andrea\s+Ravalli[,\s]*", ""),
        (r"(?i)Come\s+investitore\s+privato\s+Andrea\s+Ravalli[,\s]*", ""),
    ]
    cleaned = text
    for pat, repl in patterns:
        cleaned = re.sub(pat, repl, cleaned)

    # Auto-correct frequent LLM hallucinations for ETF identities
    # $WDEF.L is WisdomTree Europe Defence UCITS ETF (EU defense/aerospace, accumulating, NO dividends), NEVER Europe Equity Income or "Windows"!
    etf_identity_patterns = [
        (r"(?i)WisdomTree\s+Europe\s+Equity\s+Income(?:\s+UCITS\s+ETF)?", "WisdomTree Europe Defence UCITS ETF"),
        (r"(?i)Windows\s+Europe\s+(?:Equity|Quity)\s+Income(?:\s+UCITS\s+ETF)?", "WisdomTree Europe Defence UCITS ETF"),
        (r"(?i)Europe\s+Equity\s+Income(?:\s+UCITS\s+ETF)?", "WisdomTree Europe Defence UCITS ETF"),
        (r"(?i)European\s+Equity\s+Income(?:\s+UCITS\s+ETF)?", "WisdomTree Europe Defence UCITS ETF"),
        (r"(?i)WisdomTree\s+Europe\s+Income", "WisdomTree Europe Defence UCITS ETF"),
        (r"(?i)Windows\s+Europe\s+Defence", "WisdomTree Europe Defence"),
        (r"(?i)Windows\s+Europe", "WisdomTree Europe"),
    ]
    for pat, repl in etf_identity_patterns:
        cleaned = re.sub(pat, repl, cleaned)

    # Clean up any leftover empty lines or double spaces
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Capitalize the first letter if stripped at beginning
    cleaned = re.sub(r"^\s*([a-z])", lambda m: m.group(1).upper(), cleaned)
    
    # Ensure all cashtags are properly isolated for eToro
    cleaned = sanitize_etoro_cashtags(cleaned)
    return cleaned.strip()


def _run_post_verification(
    text: str,
    primary_ticker: str = None,
    session_name: str = None,
    generator_model: str = None,
    run_ai_review: bool = True,
) -> tuple[bool, str]:
    """Helper to run pre-publication verification and auto-correction on generated content."""
    try:
        from post_verifier import verify_and_clean_post
        approved, final_text, audit = verify_and_clean_post(
            text=text,
            primary_ticker=primary_ticker,
            session_name=session_name,
            generator_model=generator_model,
            run_ai_review=run_ai_review,
        )
        if not approved:
            print(f"⚠️ Post rejected by verifier: {audit.get('explanation')}")
            return False, ""
        return True, final_text
    except Exception as exc:
        print(f"⚠️ Post verification warning: {exc}")
        return True, text


def _remove_market_section_tags(text):
    """
    Remove all $ tags from the MARKET OVERVIEW section.
    Keep tags only in PORTFOLIO FOCUS section.
    
    Args:
        text: The full recap text
    
    Returns:
        str: Text with tags removed from market section
    """
    # Split into sections
    sections = text.split('💼 PORTFOLIO FOCUS')
    
    if len(sections) == 2:
        market_section = sections[0]
        portfolio_section = sections[1]
        
        # Remove all $ tags from market section
        tag_pattern = r'\$([A-Za-z0-9\-\.]+)'
        market_section_clean = re.sub(tag_pattern, r'\1', market_section)
        
        return market_section_clean + '💼 PORTFOLIO FOCUS' + portfolio_section
    
    return text



# ─── Dynamic greeting helpers ───────────────────────────────────────────────

# Greeting pools indexed by session key.
# Each session can also have day-specific variants keyed by weekday integer
# (0=Monday … 6=Sunday). Falls back to the 'default' list.
_GREETING_POOLS = {
    "EU_OPEN": {
        0: [
            "Buon lunedì! Si riparte, vediamo subito cosa ci aspetta sull'apertura europea...",
            "Lunedì mattina: nuova settimana, nuove opportunità sui mercati europei! Ecco le prime notizie...",
            "Ripartiamo! È lunedì e i mercati europei stanno per accendersi...",
        ],
        4: [
            "Buon venerdì! Ultimo giorno della settimana di trading europeo, vediamo come chiudiamo...",
            "È venerdì e i mercati europei aprono per l'ultima sessione della settimana. Ecco cosa tenere d'occhio...",
            "Siamo all'ultimo sprint! Apertura europea di venerdì in avvicinamento...",
        ],
        "default": [
            "Buongiorno! I mercati europei stanno per aprire, ecco le prime notizie del giorno...",
            "Un nuovo giorno di trading europeo. Ecco gli spunti principali da tenere d'occhio questa mattina...",
            "Eccoci qui, inizia una nuova sessione europea! Vediamo cosa ci riserva il mercato oggi...",
            "Apertura europea in avvicinamento! Ecco le notizie che potrebbero muovere i titoli del nostro portafoglio...",
            "Buongiorno a tutti! Nuova mattinata, nuova sessione europea: partiamo con un rapido sguardo ai mercati...",
        ],
    },
    "US_OPEN": {
        0: [
            "Buon pomeriggio! Si apre la settimana anche a Wall Street: vediamo come si presentano i mercati USA...",
            "Lunedì pomeriggio e Wall Street si sveglia! Ecco le prime notizie per capire come potrebbe andare...",
        ],
        4: [
            "Buon pomeriggio di venerdì! Ultimo giorno di Wall Street questa settimana: vediamo come si chiuderà...",
            "Venerdì pomeriggio: apertura USA in arrivo. Sarà un finale di settimana in rosa o in rosso?",
        ],
        "default": [
            "Buon pomeriggio! Tra poco apre Wall Street: vediamo cosa ci aspetta nella sessione americana...",
            "È l'ora di Wall Street! Ecco gli spunti principali prima dell'apertura USA...",
            "Ci prepariamo all'apertura americana. Ecco le notizie chiave da monitorare per i titoli del nostro portafoglio...",
            "Pomeriggio di borsa! Wall Street sta per aprire e questo è il momento per capire l'umore del mercato...",
            "Buon pomeriggio! La sessione americana si avvicina: facciamo il punto su cosa succede oltreoceano...",
        ],
    },
    "US_CLOSE": {
        0: [
            "Buona sera! La prima sessione della settimana si chiude: vediamo com'è andata sui mercati USA...",
            "Lunedì sera: Wall Street ha chiuso i battenti, ecco il nostro primo resoconto settimanale...",
        ],
        4: [
            "Buona sera e buon weekend anticipato! Wall Street ha chiuso l'ultima sessione della settimana...",
            "È venerdì sera e i mercati USA hanno detto l'ultima parola della settimana. Ecco com'è andata...",
        ],
        "default": [
            "Buonasera! I mercati USA hanno chiuso: ecco il nostro recap di fine giornata...",
            "Giornata conclusa! Analizziamo insieme i movimenti di oggi su Wall Street...",
            "I mercati americani hanno abbassato il sipario. Ecco com'è andata oggi sul nostro portafoglio...",
            "Buonasera a tutti! Chiusura USA completata: vediamo cosa ha combinato il mercato oggi...",
            "Fine sessione! Facciamo un po' di chiarezza su quello che è successo oggi oltre Atlantico...",
        ],
    },
    "WEEKLY_SAT": {
        "default": [
            "Buon sabato! Con i mercati chiusi, è il momento perfetto per fare il punto sulla settimana...",
            "Weekend! È arrivato il momento di guardare la settimana nel suo insieme: com'è andata?",
            "Sabato di analisi! Prendiamoci un attimo per capire cosa ha mosso il portafoglio questa settimana...",
            "Buon fine settimana! Approfittiamo della pausa dai mercati per un bilancio settimanale onesto...",
        ],
    },
    "WEEKLY_SUN": {
        "default": [
            "Buona domenica! Oggi diamo uno sguardo più da vicino ai titoli che hanno guidato la classifica settimanale...",
            "Domenica di recap! Analizziamo insieme i migliori titoli di questa settimana e le ragioni dei loro movimenti...",
            "Eccoci alla domenica! Un'occhiata alla classifica settimanale per capire chi ha brillato di più...",
            "Buona domenica a tutti! Oggi ci concentriamo sui titoli che hanno fatto la differenza in questa settimana...",
        ],
    },
}


def _get_dynamic_greeting(session_upper: str, day_of_week: int = None) -> str:
    """
    Return a randomly chosen greeting string for the given session and day.

    Args:
        session_upper: Upper-case session name (e.g. 'EUROPEAN MARKET OPEN').
        day_of_week:   0=Monday … 6=Sunday (default: today).

    Returns:
        A greeting string ready to inject into an AI prompt.
    """
    import random as _random
    from datetime import datetime as _dt

    if day_of_week is None:
        day_of_week = _dt.now().weekday()

    if "EUROPEAN" in session_upper and "OPEN" in session_upper:
        pool_key = "EU_OPEN"
    elif "U.S." in session_upper and "OPEN" in session_upper:
        pool_key = "US_OPEN"
    elif "U.S." in session_upper and "CLOSE" in session_upper:
        pool_key = "US_CLOSE"
    elif "WEEKLY" in session_upper and "SAT" in session_upper:
        pool_key = "WEEKLY_SAT"
    elif "WEEKLY" in session_upper and "SUN" in session_upper:
        pool_key = "WEEKLY_SUN"
    else:
        pool_key = "US_CLOSE"  # generic fallback

    session_pool = _GREETING_POOLS[pool_key]
    # Prefer day-specific list; fall back to 'default'
    candidates = session_pool.get(day_of_week, session_pool["default"])
    return _random.choice(candidates)


def _get_closing_question_instruction(session_upper: str) -> str:
    """
    Return a prompt instruction asking Gemini to close the post with a
    contextual, open-ended question to boost follower interaction.

    The instruction includes a few example questions to guide the model;
    Gemini should pick the most fitting one or write a similar variant.
    """
    import random as _random

    if "EUROPEAN" in session_upper and "OPEN" in session_upper:
        examples = [
            "Quali titoli europei state seguendo oggi?",
            "Vi aspettate un'apertura europea positiva o negativa?",
            "C'è qualche notizia europea che vi preoccupa o entusiasma questa mattina?",
        ]
    elif "U.S." in session_upper and "OPEN" in session_upper:
        examples = [
            "Vi aspettate una giornata positiva o negativa per Wall Street oggi?",
            "Quale titolo USA del portafoglio monitorate con più attenzione questa sessione?",
            "Come pensate che reagirà Wall Street alle notizie di oggi?",
        ]
    elif "WEEKLY" in session_upper and "SAT" in session_upper:
        examples = [
            "Qual è stato per voi il titolo più sorprendente di questa settimana?",
            "Cosa vi ha colpito di più nell'andamento del mercato questa settimana?",
            "Siete soddisfatti della direzione del portafoglio questa settimana?",
        ]
    elif "WEEKLY" in session_upper and "SUN" in session_upper:
        examples = [
            "Cosa vi aspettate dalla prossima settimana? Ottimismo o cautela?",
            "Quale titolo pensate potrà sorprendere la prossima settimana?",
            "Qual è il vostro sentiment per la settimana che inizia domani?",
        ]
    else:  # US Close / generic
        examples = [
            "Com'è andata la vostra giornata? Soddisfatti dell'andamento del portafoglio?",
            "Qual è stato il movimento di mercato che vi ha sorpreso di più oggi?",
            "Cosa pensate delle performance di oggi sul nostro portafoglio?",
            "Avete domande sull'andamento di oggi o su qualche titolo in particolare?",
        ]

    chosen = _random.choice(examples)
    return (
        f"- Concludi il tuo messaggio con una domanda aperta e naturale per coinvolgere i lettori. "
        f"Scegli la domanda più adatta al contesto di oggi, oppure scrivi una variante simile. "
        f"Esempi: \"{chosen}\" — ma adattala liberamente al contenuto che hai scritto sopra. "
        f"La domanda deve sembrare spontanea, non formulaica."
    )

# ─── End dynamic greeting helpers ───────────────────────────────────────────


def get_recent_tags(limit=None):
    """
    Get list of recently used tags from storage.
    Args:
        limit: Return only the last N tags. If None, return all history.
    """
    if not GIST_STORAGE_AVAILABLE:
        return []
    
    try:
        data = load_data()
        tags = data.get('used_tags', [])
        if limit:
            return tags[-limit:]
        return tags
    except Exception:
        return []


def update_rotation_history(new_tags):
    """
    Update the list of used tags in Gist storage.
    Call this when tags are used outside of this module (e.g. in formatter).
    """
    if not GIST_STORAGE_AVAILABLE or not new_tags:
        return

    try:
        # Normalize tags
        normalized_new = [t.replace('$', '').replace('.', '').upper() for t in new_tags]
        
        data = load_data()
        used_tags = data.get('used_tags', [])
        
        # Add new tags
        updated_used = used_tags + normalized_new
        
        # Keep history limited (e.g. 20 items)
        all_tickers = _get_all_portfolio_tags()
        max_history = len(all_tickers) * 2
        
        data['used_tags'] = updated_used[-max_history:] if len(updated_used) > max_history else updated_used
        save_data(data)
        print(f"🔄 Updated tag rotation history with: {normalized_new}")
            
    except Exception as e:
        print(f"⚠️ Error updating tag rotation: {e}")


def generate_monthly_ai_recap(max_tags=MAX_TAGS_PER_POST, excluded_tags=None):
    """
    Generate AI-powered monthly market recap summarizing major events over the past month
    
    Args:
        max_tags: Maximum number of $ tags allowed in the AI output
        excluded_tags: List of tags already used elsewhere in the post
        
    Returns:
        str: Formatted monthly recap or empty string if API key not set
    """
    if not GENAI_AVAILABLE:
        print("⚠️  google-genai package not available, skipping AI monthly recap")
        return ""
    
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("⚠️  Warning: GEMINI_API_KEY not set, skipping AI monthly recap")
        return ""
    
    # Models in order of preference — each belongs to a DIFFERENT quota bucket (20 RPD each).
    # gemini-2.5-flash-lite is first (10 RPM vs 5 RPM).
    models_to_try = list(DEFAULT_GEMINI_MODELS)
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Select tags for this post (with rotation)
        selected_tags = []
        selected_tags_str = "None"
        tag_instruction = ""
        
        if max_tags > 0:
            portfolio_budget = max(0, max_tags - 1)
            selected_tags = _select_tags_for_rotation(portfolio_budget, excluded_tags)
            selected_tags_str = ', '.join([f'${tag}' for tag in selected_tags]) if selected_tags else "None"
            tag_instruction = f"""
- IMPORTANT: You MUST dedicate exactly 1 tag of the allowed {max_tags} tags to a highly discussed/trending index or stock of the month that you will discuss in the recap. Choose this tag from popular indices like $NSDQ100, $SPX500 (highly recommended to attract copiers), or if there is major news about a specific hot stock this month (e.g. $TSLA, $AAPL, $BTC, etc.), you can tag and discuss that instead. This index/stock MUST be included and explained in the recap.
- In addition to this trending tag, you can use at most {portfolio_budget} tags from this portfolio list: {selected_tags_str}.
- Never exceed the total limit of {max_tags} tags with the $ symbol in the post.
"""
        else:
            tag_instruction = """
- Do NOT use any $ tags in this section.
"""
        
        # Get current month/year for context
        now = datetime.now()
        current_month = now.strftime('%B %Y')  # e.g., "January 2026"
        
        # Get all portfolio tickers for context with descriptions (exclude Russian stocks)
        excluded_tickers = {'MNODL.L', 'NVTKL.L'}
        portfolio_items = []
        for t, (_, descr) in PORTFOLIO_TICKERS.items():
            if t not in excluded_tickers:
                portfolio_items.append(f"{t} ({descr})")
        portfolio_context = ", ".join(portfolio_items)
        
        prompt = f"""You are a senior financial analyst. Generate a comprehensive MONTHLY MARKET RECAP for {current_month}.

Use your search tool to find the MAJOR EVENTS and TRENDS that defined this month across:
1. USA Markets (S&P500, Nasdaq, Dow Jones)
2. European Markets (Euro Stoxx, DAX, FTSE)
3. Asian Markets (Shanghai, Nikkei, Hang Seng)
4. Key Economic Data (inflation, employment, GDP, central bank decisions)
5. Major Corporate News (earnings, M&A, product launches)
6. Geopolitical Events (if market-relevant)

PORTFOLIO CONTEXT:
These are the tickers in the portfolio you should focus on for the PORTFOLIO IMPACT section:
{portfolio_context}

Structure your response in TWO sections with a TOPIC-BASED FORMAT:

1. 🌍 MONTHLY MARKET OVERVIEW
Organize this section into MAX 3 MAJOR TOPICS/THEMES that defined {current_month}.
For each topic:
- Use 3 relevant emojis at the start (e.g., 🏛️💵🔔 for Fed decisions, 📊📈💹 for market trends, etc.)
- Write the topic title
- Write a 2-3 sentence summary with specific data points
- IMPORTANT: Do NOT use any $ tags in this section

Example format:
🏛️💵🔔 Fed Rate Decision
The Federal Reserve cut rates by 25bps to 4.25-4.50%, signaling a more dovish stance...

2. 💼 PORTFOLIO IMPACT & OUTLOOK
Organize this section into MAX 5 TOPICS showing how the month's events impacted PORTFOLIO STOCKS listed above.
IMPORTANT: Focus EXCLUSIVELY on the tickers from the portfolio context provided above.
For each topic, if you have available tags from this list: {selected_tags_str}:
- Use 3 relevant emojis + $TAG (e.g., 🤖💡🚀 $NVDA)
- Write a 2-3 sentence summary about impact and outlook
- If no tags available, just use emojis without tags
{tag_instruction}

Example format (when tag is available):
🤖💡🚀 $NVDA
NVIDIA's new AI chip announcement drove 15% gains this month. Looking ahead to strong Q1 earnings...

STRICT LIMITS:
- MAXIMUM 3 topics for MARKET OVERVIEW, 5 for PORTFOLIO IMPACT (total 8 topics max)
- MAXIMUM {MAX_TAGS_PER_POST} $ tags TOTAL across both sections
- Use $ prefix ONLY for the allowed tags listed above
- Focus on HIGH-IMPACT events that shaped the month
- Total character count must stay under 2200 for this AI section
- FOCUS ON PORTFOLIO TICKERS in the Portfolio Impact section

Output format:
🌍 MONTHLY MARKET OVERVIEW

[emoji emoji emoji] Topic Title
Brief summary with data points...

[emoji emoji emoji] Topic Title
Brief summary with data points...

💼 PORTFOLIO IMPACT & OUTLOOK

[emoji emoji emoji] $TAG (if available)
Impact and outlook summary...

[emoji emoji emoji] Topic Title
Impact and outlook summary...
"""
        
        print(f"🤖 Generating monthly AI recap for {current_month}...")
        print(f"   Selected tags: {selected_tags_str}")
        
        # Configure with search tool
        config = None
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7
            )
        except Exception as config_err:
            print(f"⚠️ Search tool unavailable: {config_err}")
            config = types.GenerateContentConfig(temperature=0.7)
        
        # Try models
        for model_name in models_to_try:
            try:
                print(f"   Trying model: {model_name}...")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                
                if response and response.text:
                    print(f"✅ Monthly recap generated using {model_name}!")
                    recap_text = response.text.strip()
                    
                    # Log successful API usage
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "monthly_recap")
                    
                    # Post-process: remove intro text and tags from overview section
                    recap_text = _remove_intro_text(recap_text)
                    recap_text = _remove_market_section_tags(recap_text)
                    
                    # Limit tags
                    recap_text = _limit_tags_in_text(recap_text, selected_tags, MAX_TAGS_PER_POST)
                    
                    return "\n" + recap_text + "\n"
                    # Pre-publication double-check
                    approved, verified_text = _run_post_verification(
                        recap_text,
                        session_name="Monthly recap",
                        generator_model=model_name,
                    )
                    if not approved or not verified_text:
                        print(f"⚠️ Monthly recap rejected by verifier ({model_name}), trying next model...")
                        continue

                    return "\n" + verified_text + "\n"
                else:
                    print(f"⚠️  Empty response from {model_name}")
                    continue
                    
            except Exception as model_error:
                error_msg = str(model_error).lower()
                print(f"⚠️  Model {model_name} failed: {model_error}")
                if API_TRACKER_AVAILABLE:
                    log_api_request(model_name, False, "monthly_recap")
                
                # Quota / rate limit (429) backoff
                if '429' in error_msg or 'quota' in error_msg or 'resource_exhausted' in error_msg:
                    # If tools were active, the 429 may be specifically on Google Search tool.
                    # Attempt generation with this same model without tools first before cascading.
                    if config and getattr(config, 'tools', None):
                        print(f"   ℹ️ Model {model_name} search tool rate-limited (429), trying without search tool...")
                        try:
                            time.sleep(2.0)
                            response = client.models.generate_content(
                                model=model_name,
                                contents=prompt,
                                config=types.GenerateContentConfig(temperature=0.7)
                            )
                            if response and response.text:
                                print(f"✅ Monthly recap generated using {model_name} (direct, no tools)!")
                                if API_TRACKER_AVAILABLE:
                                    log_api_request(model_name, True, "monthly_recap")
                                recap_text = response.text.strip()
                                recap_text = _remove_intro_text(recap_text)
                                recap_text = _remove_market_section_tags(recap_text)
                                recap_text = _limit_tags_in_text(recap_text, selected_tags, MAX_TAGS_PER_POST)
                                return "\n" + recap_text + "\n"
                        except Exception as e_notools:
                            print(f"   Direct attempt without tools also failed: {e_notools}")

                    print(f"   ⏳ Model {model_name} quota/rate limited (429). Waiting 6s before cascading...")
                    time.sleep(6.0)
                    continue

                # 503 UNAVAILABLE — retry with 10-minute intervals up to 5 times
                if '503' in error_msg or 'unavailable' in error_msg:
                    max_503_retries = 5
                    retry_wait_secs = 600
                    succeeded = False
                    for attempt in range(1, max_503_retries + 1):
                        print(f"   503 on {model_name} (retry {attempt}/{max_503_retries}), waiting {retry_wait_secs}s...")
                        time.sleep(retry_wait_secs)
                        try:
                            response = client.models.generate_content(
                                model=model_name,
                                contents=prompt,
                                config=config
                            )
                            if response and response.text:
                                print(f"✅ Monthly recap generated (after 503 retry {attempt}) using {model_name}!")
                                if API_TRACKER_AVAILABLE:
                                    log_api_request(model_name, True, "monthly_recap")
                                recap_text = response.text.strip()
                                recap_text = _remove_intro_text(recap_text)
                                recap_text = _remove_market_section_tags(recap_text)
                                recap_text = _limit_tags_in_text(recap_text, selected_tags, MAX_TAGS_PER_POST)
                                succeeded = True
                                return "\n" + recap_text + "\n"
                        except Exception as e2:
                            retry_msg = str(e2).lower()
                            if '503' not in retry_msg and 'unavailable' not in retry_msg:
                                print(f"   Non-503 error on 503-retry {attempt}: {e2}")
                                break
                    if not succeeded:
                        last_error = model_error
                    continue
                
                time.sleep(2)
                
                # Try without tools if not supported (exclude 404 NOT_FOUND from this branch)
                is_tool_issue = ('not supported' in error_msg or 'invalid' in error_msg) and '404' not in error_msg
                if is_tool_issue:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt
                        )
                        if response and response.text:
                            print(f"✅ Monthly recap generated (no tools) using {model_name}!")
                            if API_TRACKER_AVAILABLE:
                                log_api_request(model_name, True, "monthly_recap")
                            recap_text = response.text.strip()
                            recap_text = _remove_intro_text(recap_text)
                            recap_text = _remove_market_section_tags(recap_text)
                            recap_text = _limit_tags_in_text(recap_text, selected_tags, MAX_TAGS_PER_POST)
                            return "\n" + recap_text + "\n"
                    except Exception as e2:
                        print(f"   Retry failed: {e2}")
                
                continue
        
        print("❌ All models failed for monthly recap")
        return ""
        
    except Exception as e:
        print(f"❌ Error generating monthly recap: {e}")
        return ""


def generate_market_news_recap(max_tags=MAX_TAGS_PER_POST, excluded_tags=None, market_session=None):
    """
    Generate AI-powered market news recap for USA, CHINA, and EU markets
    
    Args:
        max_tags: Maximum number of $ tags allowed in the AI output
        excluded_tags: List of tags already used elsewhere in the post
        market_session: Name of the current market session
        
    Returns:
        str: Formatted news recap or empty string if API key not set
    """
    if not GENAI_AVAILABLE:
        print("⚠️  google-genai package not available, skipping AI news generation")
        return ""
    
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("⚠️  Warning: GEMINI_API_KEY not set, skipping AI news generation")
        return ""
    
    # Models in order of preference — each belongs to a DIFFERENT quota bucket (20 RPD each).
    # gemini-2.5-flash-lite is first (10 RPM vs 5 RPM).
    models_to_try = list(DEFAULT_GEMINI_MODELS)
    
    if not market_session:
        market_session = os.environ.get('MARKET_SESSION', 'Daily recap')
        
    EUROPEAN_TICKERS = ['ENEL.MI', 'ENI.MI', 'PRY.MI', 'RACE', 'VOW3.DE', 'NOVO-B.CO', 'AZN.L', 'GLEN.L', 'TRIG.L', 'ULVR.L', 'MAU.PA', 'SX7PEX.DE', 'IEUR', 'WDEF.L', 'IQQL.DE', 'PPFB.DE']
    US_TICKERS = ['NVDA', 'MSFT', 'AMZN', 'GOOG', 'PLTR', 'AVGO', 'TSM', 'MRVL', 'LLY', 'ABBV', 'ABT.US', 'HUM', 'CCJ', 'WMT', 'MELI', 'IB01.L']
    
    allowed_tickers = None
    session_upper = market_session.upper()
    if "EUROPEAN" in session_upper:
        allowed_tickers = EUROPEAN_TICKERS
    elif "U.S." in session_upper or "US" in session_upper:
        if "OPEN" in session_upper:
            allowed_tickers = US_TICKERS
            
    try:
        # Configure Gemini client
        client = genai.Client(api_key=api_key)
        
        # Build the full list of allowed tickers for tag validation
        # (broader than the rotation-selected subset — any valid portfolio ticker is OK)
        all_allowed_for_validation = list(PORTFOLIO_TICKERS.keys())
        
        # Select tags for this post (with rotation)
        selected_tags = []
        selected_tags_str = "None" # Fix UnboundLocalError
        tag_instruction = ""
        
        if max_tags > 0:
            portfolio_budget = max(0, max_tags - 1)
            selected_tags = _select_tags_for_rotation(portfolio_budget, excluded_tags, allowed_tickers)
            selected_tags_str = ', '.join([f'${tag}' for tag in selected_tags]) if selected_tags else "Nessuno"
            tag_instruction = f"""
- REGOLA ASSOLUTA SUI TAG: devi usare ESATTAMENTE {max_tags} tag con il simbolo $ nel testo. Non uno di meno, non uno di più.
- TAG OBBLIGATORI DEL PORTAFOGLIO ({portfolio_budget}): DEVI includere TUTTI questi tag nel testo, ognuno accompagnato da almeno una frase che lo riguardi: {selected_tags_str}. Non puoi saltarne nessuno.
- TAG TENDENZA OBBLIGATORIO (1): DEVI aggiungere esattamente 1 tag tra i più cercati/discussi del momento, scegliendo tra $NSDQ100 o $SPX500 (preferiti perché attirano copiatori), oppure un titolo di enorme interesse del giorno (es. $TSLA, $NVDA, $AAPL, $BTC). Questo tag DEVE essere spiegato nel testo.
- TOTALE: {portfolio_budget} tag portafoglio + 1 tag tendenza = {max_tags} tag totali. Conta i $ nel testo prima di concludere e verifica che siano esattamente {max_tags}.
"""
        else:
            tag_instruction = """
- IMPORTANTE: Non usare alcun tag con il simbolo $ in questa sezione.
- Scrivi tutti i simboli azionari come testo normale (es. NVDA, MSFT) senza il prefisso $.
"""
        
        # Get all portfolio tickers for context with descriptions (exclude Russian stocks)
        excluded_tickers = {'MNODL.L', 'NVTKL.L'}
        portfolio_items = []
        for t, (_, descr) in PORTFOLIO_TICKERS.items():
            if t not in excluded_tickers:
                portfolio_items.append(f"{t} ({descr})")
        portfolio_context = ", ".join(portfolio_items)
        
        # Load previous history to avoid repetition
        history = load_recap_history() if GIST_STORAGE_AVAILABLE else []
        previous_topics_str = ""
        if history:
            previous_topics_str = "\nCRITICAL: DO NOT REPEAT the following news which were already reported recently:\n"
            for entry in history:
                previous_topics_str += f"- {entry['content'][:300]}...\n"
        
        # Create prompt based on session
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Build dynamic greeting and closing question for this session
        dynamic_greeting = _get_dynamic_greeting(session_upper)
        closing_question_instruction = _get_closing_question_instruction(session_upper)

        asset_identity_rules = (
            "- REGOLE IDENTITÀ ASSET (TASSATIVE): $WDEF.L è WisdomTree Europe Defence UCITS ETF "
            "(difesa e aerospazio UE, ad accumulazione, ZERO dividendi/cedole). È SEVERAMENTE VIETATO chiamarlo "
            "'WisdomTree Europe Equity Income', 'Windows Europe' o attribuirgli dividendi! "
            "$IQQL.DE è iShares Listed Private Equity UCITS ETF (Private Equity, es. KKR, Blackstone), NON World Quality. "
            "Nessuna menzione di XEON (dismesso dal portafoglio)."
        )
        
        if "EUROPEAN" in session_upper and "OPEN" in session_upper:
            prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro. Scrivi un post di buongiorno caldo, professionale e naturale per i tuoi copiatori ed follower prima dell'apertura dei mercati europei.
            
            Usa il tuo strumento di ricerca Google per cercare le notizie finanziarie e gli eventi di mercato più rilevanti delle ultime 12-24 ore relativi ai mercati europei o ai titoli europei nel nostro portafoglio.
            
            CONTESTO PORTAFOGLIO EUROPEO:
            I principali titoli europei del nostro portafoglio su cui concentrarsi sono:
            AstraZeneca (AZN.L), Novo Nordisk (NOVO-B.CO), Enel (ENEL.MI), Eni (ENI.MI), Prysmian (PRY.MI), Ferrari (RACE), Volkswagen (VOW3.DE), Glencore (GLEN.L).
            
            LINEE GUIDA PER IL TESTO:
            - Scrivi in ITALIANO con uno stile estremamente naturale, fluido e colloquiale (come un messaggio personale a dei compagni investitori che seguono la tua strategia). Evita assolutamente toni formali, accademici o robotici.
            - NON usare mai il markdown per il grassetto (NON usare **testo** o asterischi per evidenziare parole): scrivi in testo semplice pulito, poiché eToro non supporta la formattazione markdown.
            - IMPORTANTE: Parla direttamente in prima persona ("Nel nostro portafoglio...", "Monitoriamo...", "La mia strategia..."). È TASSATIVAMENTE VIETATO iniziare frasi con "Come Andrea Ravalli..." o "Io sono Andrea Ravalli...". Non presentarti mai per nome nel testo del messaggio!
            {asset_identity_rules}
            - Inizia il tuo messaggio ESATTAMENTE con questa frase di apertura (adattala leggermente se necessario per renderla più fluida): "{dynamic_greeting}"
            - Presenta MAX 3 brevi spunti o notizie principali per l'apertura europea, focalizzandoti sulle novità dei nostri titoli in portafoglio o sull'indice Euro Stoxx.
            - {tag_instruction}
            - Usa le emoji in modo spontaneo e naturale (non metterne troppe, massimo 3 o 4 in tutto il post).
            - {closing_question_instruction}
            - Mantieni la lunghezza totale di questa sezione generata sotto i 1800 caratteri.
            
            Output format (ONLY return the plain text of the post in Italian):
            [Il tuo messaggio naturale in italiano]
            """
            
        elif "U.S." in session_upper and "OPEN" in session_upper:
            prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro. Scrivi un post di buongiorno/buon pomeriggio caldo, professionale e naturale per i tuoi copiatori ed follower prima dell'apertura di Wall Street (U.S. market open).
            
            Usa il tuo strumento di ricerca Google per cercare le notizie finanziarie e gli eventi di mercato più rilevanti delle ultime 12-24 ore relativi ai mercati americani o ai titoli USA nel nostro portafoglio.
            
            CONTESTO PORTAFOGLIO USA:
            I principali titoli USA del nostro portafoglio su cui concentrarsi sono:
            NVIDIA (NVDA), Microsoft (MSFT), Amazon (AMZN), Eli Lilly (LLY), Palantir (PLTR), Broadcom (AVGO), Cloudflare (NET), PayPal (PYPL), Taiwan Semiconductor (TSM), AbbVie (ABBV), Abbott (ABT).
            
            LINEE GUIDA PER IL TESTO:
            - Scrivi in ITALIANO con uno stile estremamente naturale, fluido e colloquiale (come un messaggio personale a dei compagni investitori che seguono la tua strategia). Evita assolutamente toni formali o robotici.
            - NON usare mai il markdown per il grassetto (NON usare **testo** o asterischi per evidenziare parole): scrivi in testo semplice pulito, poiché eToro non supporta la formattazione markdown.
            - IMPORTANTE: Parla direttamente in prima persona ("Nel nostro portafoglio...", "Oggi all'apertura guardiamo...", "La mia strategia..."). È TASSATIVAMENTE VIETATO iniziare frasi con "Come Andrea Ravalli..." o "Io sono Andrea Ravalli...". Non presentarti mai per nome nel testo del messaggio!
            {asset_identity_rules}
            - Inizia il tuo messaggio ESATTAMENTE con questa frase di apertura (adattala leggermente se necessario per renderla più fluida): "{dynamic_greeting}"
            - Presenta MAX 3 brevi spunti o notizie principali per l'apertura USA, focalizzandoti sulle novità dei nostri titoli in portafoglio o sugli indici americani (S&P 500, Nasdaq).
            - {tag_instruction}
            - Usa le emoji in modo spontaneo e naturale (non metterne troppe, massimo 3 o 4 in tutto il post).
            - {closing_question_instruction}
            - Mantieni la lunghezza totale di questa sezione generata sotto i 1800 caratteri.
            
            Output format (ONLY return the plain text of the post in Italian):
            [Il tuo messaggio naturale in italiano]
            """
            
        elif "WEEKLY" in session_upper and "SAT" in session_upper:
            prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro. Scrivi un post di fine settimana caldo, onesto e naturale per i tuoi copiatori ed follower (Weekly Recap - Sabato).
            
            Usa il tuo strumento di ricerca Google per analizzare l'andamento della settimana appena trascorsa sui mercati globali e l'impatto sul nostro portafoglio.
            
            CONTESTO PORTAFOGLIO:
            {portfolio_context}
            
            LINEE GUIDA PER IL TESTO:
            - Scrivi in ITALIANO con uno stile estremamente naturale, fluido ed empatico. Parla apertamente di come è andata la settimana, se è stata verde o rossa, dei risultati ottenuti e delle tue sensazioni.
            - NON usare mai il markdown per il grassetto (NON usare **testo** o asterischi per evidenziare parole): scrivi in testo semplice pulito, poiché eToro non supporta la formattazione markdown.
            - IMPORTANTE: Parla direttamente in prima persona. È TASSATIVAMENTE VIETATO iniziare con "Come Andrea Ravalli..." o "Io sono Andrea Ravalli...". Non presentarti mai col tuo nome nel testo!
            {asset_identity_rules}
            - Inizia il tuo messaggio ESATTAMENTE con questa frase di apertura (adattala leggermente se necessario per renderla più fluida): "{dynamic_greeting}"
            - Fai un bilancio sincero di cosa ha guidato il portafoglio in questa settimana, menzionando i movimenti principali dei nostri titoli chiave.
            - Spiega brevemente cosa terremo d'occhio per la prossima settimana.
            - {tag_instruction}
            - Usa le emoji in modo spontaneo e naturale (massimo 3 o 4 in tutto il post).
            - {closing_question_instruction}
            - Mantieni la lunghezza totale di questa sezione generata sotto i 1800 caratteri.
            
            Output format (ONLY return the plain text of the post in Italian):
            [Il tuo messaggio naturale in italiano]
            """
            
        elif "WEEKLY" in session_upper and "SUN" in session_upper:
            prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro. Scrivi un commento domenicale naturale e professionale per i tuoi copiatori sui migliori titoli della settimana (Weekly Recap - Domenica).
            
            Usa il tuo strumento di ricerca Google per analizzare i motivi del forte rialzo dei migliori titoli del nostro portafoglio durante la settimana appena trascorsa.
            
            CONTESTO PORTAFOGLIO:
            {portfolio_context}
            
            LINEE GUIDA PER IL TESTO:
            - Scrivi in ITALIANO con uno stile naturale e chiaro. Questo post accompagnerà la classifica dei migliori titoli del portafoglio.
            - NON usare mai il markdown per il grassetto (NON usare **testo** o asterischi per evidenziare parole): scrivi in testo semplice pulito, poiché eToro non supporta la formattazione markdown.
            - IMPORTANTE: Parla direttamente in prima persona. È TASSATIVAMENTE VIETATO usare formule come "Come Andrea Ravalli..." o "Io sono Andrea Ravalli...". Non presentarti mai col tuo nome nel testo!
            {asset_identity_rules}
            - Inizia il tuo messaggio ESATTAMENTE con questa frase di apertura (adattala leggermente se necessario per renderla più fluida): "{dynamic_greeting}"
            - Spiega in modo semplice e chiaro i motivi del successo dei titoli migliori di questa settimana (massimo 2-3 titoli).
            - Collega queste performance alla nostra tesi d'investimento di lungo termine, rassicurando i copiatori sulla bontà delle nostre scelte.
            - {tag_instruction}
            - Usa le emoji in modo spontaneo e naturale (massimo 3 o 4 in tutto il post).
            - {closing_question_instruction}
            - Mantieni la lunghezza totale di questa sezione generata sotto i 1800 caratteri.
            
            Output format (ONLY return the plain text of the post in Italian):
            [Il tuo messaggio naturale in italiano]
            """
            
        else:
            prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro. Scrivi un resoconto serale caldo, professionale e naturale per i tuoi copiatori dopo la chiusura dei mercati USA (U.S. market close / fine giornata).
            
            Usa il tuo strumento di ricerca Google per cercare le notizie finanziarie e le performance più rilevanti delle ultime 24 ore sui mercati globali e per i titoli del nostro portafoglio.
            
            {previous_topics_str}
            
            CONTESTO PORTAFOGLIO:
            {portfolio_context}
            
            LINEE GUIDA PER IL TESTO:
            - Scrivi in ITALIANO con uno stile estremamente naturale, fluido e colloquiale (come un resoconto sincero scritto a fine giornata per i tuoi compagni investitori).
            - NON usare mai il markdown per il grassetto (NON usare **testo** o asterischi per evidenziare parole): scrivi in testo semplice pulito, poiché eToro non supporta la formattazione markdown.
            - IMPORTANTE: Parla direttamente in prima persona ("Chiudiamo la sessione...", "Nel nostro portafoglio...", "Oggi abbiamo osservato..."). È TASSATIVAMENTE VIETATO iniziare frasi con "Come Andrea Ravalli..." o "Io sono Andrea Ravalli...". Non presentarti mai per nome nel testo del messaggio!
            - È TASSATIVAMENTE VIETATO inserire menzioni o tag come @AndreaRavalli o @andrearavalli.
            {asset_identity_rules}
            - Inizia il tuo messaggio ESATTAMENTE con questa frase di apertura (adattala leggermente se necessario per renderla più fluida): "{dynamic_greeting}"
            - Presenta un breve quadro della giornata di borsa (S&P 500, Nasdaq, mercati europei) e spiega l'impatto diretto sui titoli del nostro portafoglio.
            - {tag_instruction}
            - Usa le emoji in modo spontaneo e naturale (massimo 3 o 4 in tutto il post).
            - {closing_question_instruction}
            - Mantieni la lunghezza totale di questa sezione generata sotto i 1800 caratteri.
            
            Output format (ONLY return the plain text of the post in Italian):
            [Il tuo messaggio naturale in italiano]
            """
        
        print("🤖 Generating AI market news recap...")
        print(f"   Selected tags for this post: {selected_tags_str}")
        
        # Configure search tool if available in the SDK
        config = None
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7
            )
        except Exception as config_err:
            print(f"⚠️ Could not initialize Google Search tool: {config_err}")
            config = types.GenerateContentConfig(temperature=0.7)

        # Try each model until one works
        last_error = None
        for model_name in models_to_try:
            try:
                print(f"   Trying model: {model_name}...")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                
                if response and response.text:
                    print(f"✅ AI news recap generated successfully using {model_name}!")
                    recap_text = response.text.strip()
                    
                    # Log successful API usage
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "daily_recap")
                    
                    # Post-process: remove intro text and any $ tags from market section
                    recap_text = _remove_intro_text(recap_text)
                    recap_text = _remove_market_section_tags(recap_text)
                    
                    # Post-process: ensure only valid portfolio tags are used and limit count
                    recap_text = _limit_tags_in_text(recap_text, all_allowed_for_validation, max_tags)
                    recap_text = _clean_robotic_phrases(recap_text)
                    

                    # Pre-publication double-check
                    approved, verified_text = _run_post_verification(
                        recap_text,
                        session_name=market_session or "Daily recap",
                        generator_model=model_name,
                    )
                    if not approved or not verified_text:
                        print(f"⚠️ Market news recap rejected by verifier ({model_name}), trying next model...")
                        continue
                    recap_text = verified_text

                    # Update rotation history with the tags actually selected for the post
                    if selected_tags:
                        update_rotation_history(selected_tags)
                    
                    # Save to history (using Gist storage)
                    if GIST_STORAGE_AVAILABLE:
                        save_to_history(recap_text)
                    
                    return "\n" + recap_text + "\n"
                else:
                    print(f"⚠️  Empty response from {model_name}, trying next model...")
                    continue
                    
            except Exception as model_error:
                error_msg = str(model_error).lower()
                print(f"⚠️  Model {model_name} failed: {model_error}")
                if API_TRACKER_AVAILABLE:
                    log_api_request(model_name, False, "daily_recap")
                
                # 429 QUOTA / RATE LIMIT — pause before cascading
                if '429' in error_msg or 'quota' in error_msg or 'resource_exhausted' in error_msg:
                    # If search tools were active, the 429 quota exhaustion could be on the Google Search Tool.
                    # Attempt direct generation with this same high-intelligence model without search tool.
                    if config and getattr(config, 'tools', None):
                        print(f"   ℹ️ Model {model_name} search tool rate-limited (429), trying without search tool...")
                        try:
                            time.sleep(2.0)
                            response = client.models.generate_content(
                                model=model_name,
                                contents=prompt,
                                config=types.GenerateContentConfig(temperature=0.7)
                            )
                            if response and response.text:
                                print(f"✅ AI news recap generated successfully using {model_name} (direct, no tools)!")
                                if API_TRACKER_AVAILABLE:
                                    log_api_request(model_name, True, "daily_recap")
                                recap_text = response.text.strip()
                                recap_text = _remove_intro_text(recap_text)
                                recap_text = _remove_market_section_tags(recap_text)
                                recap_text = _limit_tags_in_text(recap_text, all_allowed_for_validation, max_tags)
                                recap_text = _clean_robotic_phrases(recap_text)
                                approved, verified_text = _run_post_verification(
                                    recap_text,
                                    session_name=market_session or "Daily recap",
                                    generator_model=model_name,
                                )
                                if approved and verified_text:
                                    recap_text = verified_text
                                    if selected_tags:
                                        update_rotation_history(selected_tags)
                                    if GIST_STORAGE_AVAILABLE:
                                        save_to_history(recap_text)
                                    return "\n" + recap_text + "\n"
                        except Exception as e_notools:
                            print(f"   Direct attempt without tools for {model_name} also failed: {e_notools}")

                    print(f"   ⏳ Model {model_name} quota/rate limited (429). Pausing 6s before cascading...")
                    time.sleep(6.0)
                    last_error = model_error
                    continue

                # 503 UNAVAILABLE at EU open (07:00 UTC) on gemini-2.5-flash typically
                # lasts 30-50 minutes. Retry with 10-minute intervals (up to 5 times = 50 min
                # max) before giving up and trying the next model.
                if '503' in error_msg or 'unavailable' in error_msg:
                    max_503_retries = 5
                    retry_wait_secs = 600  # 10 minutes
                    for attempt in range(1, max_503_retries + 1):
                        print(f"   503 on {model_name} (retry {attempt}/{max_503_retries}), waiting {retry_wait_secs}s...")
                        time.sleep(retry_wait_secs)
                        try:
                            response = client.models.generate_content(
                                model=model_name,
                                contents=prompt,
                                config=config
                            )
                            if response and response.text:
                                print(f"✅ AI news recap generated (after 503 retry {attempt}) using {model_name}!")
                                if API_TRACKER_AVAILABLE:
                                    log_api_request(model_name, True, "daily_recap")
                                recap_text = response.text.strip()
                                recap_text = _remove_intro_text(recap_text)
                                recap_text = _remove_market_section_tags(recap_text)
                                recap_text = _limit_tags_in_text(recap_text, all_allowed_for_validation, max_tags)
                                if selected_tags:
                                    update_rotation_history(selected_tags)
                                if GIST_STORAGE_AVAILABLE:
                                    save_to_history(recap_text)
                                return "\n" + recap_text + "\n"
                        except Exception as e2:
                            retry_msg = str(e2).lower()
                            if '503' not in retry_msg and 'unavailable' not in retry_msg:
                                print(f"   Non-503 error on 503-retry {attempt}: {e2}")
                                break  # different error, stop retrying this model
                    last_error = model_error
                    continue
                
                time.sleep(2)
                
                # 404 NOT_FOUND may include "not supported" in the message — check for actual
                # tool-compatibility issues (not just model not found) by excluding 404 errors
                is_tool_issue = ('not supported' in error_msg or 'invalid' in error_msg) and '404' not in error_msg
                if is_tool_issue:
                    print(f"   Model {model_name} might not support search tools, trying without...")
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt
                        )
                        if response and response.text:
                            print(f"✅ AI news recap generated successfully (without tools) using {model_name}!")
                            if API_TRACKER_AVAILABLE:
                                log_api_request(model_name, True, "daily_recap")
                            recap_text = response.text.strip()
                            
                            # Post-process
                            recap_text = _remove_intro_text(recap_text)
                            recap_text = _remove_market_section_tags(recap_text)
                            recap_text = _limit_tags_in_text(recap_text, all_allowed_for_validation, max_tags)
                            
                            # Update rotation history with the tags actually selected for the post
                            if selected_tags:
                                update_rotation_history(selected_tags)
                                
                            if GIST_STORAGE_AVAILABLE:
                                save_to_history(recap_text)
                            return "\n" + recap_text + "\n"
                    except Exception as e2:
                        print(f"   Retry failed: {e2}")
                
                if 'quota' in error_msg or 'resource_exhausted' in error_msg or '429' in error_msg:
                    print(f"   Quota exceeded for {model_name}, trying next model...")
                    last_error = model_error
                    continue
                else:
                    last_error = model_error
                    continue
        
        # All models failed
        print(f"❌ All models failed. Last error: {last_error}")
        print("💡 Tip: Wait a few minutes for quota reset, or check your API key at https://makersuite.google.com/")
        return ""
            
    except Exception as e:
        print(f"❌ Error generating AI news recap: {e}")
        print(f"Error type: {type(e).__name__}")
        return ""



def get_why_copy_message(five_year_return=200, avg_yearly_return=18, benchmark_performance=None, market_session=''):
    """
    Returns the fixed message explaining why to copy this portfolio.
    Only includes the @AndreaRavalli tag in U.S. market close session to avoid notification spam on other sessions.
    
    Args:
        five_year_return: Total return since strategy change (default 200%)
        avg_yearly_return: CAGR - Compound Annual Growth Rate (default 18%)
        benchmark_performance: Dict of {etoro_ticker: performance_value}
        market_session: Current market session name
    
    Returns:
        str: Formatted fixed message with performance data
    """
    # Calculate years to double using Rule of 72
    time_to_double = 72 / avg_yearly_return if avg_yearly_return > 0 else 0
    
    benchmark_lines = ""
    if benchmark_performance:
        for ticker, perf in benchmark_performance.items():
            # Calculate the difference (delta) between our return and benchmark
            delta = five_year_return - perf
            perf_label = "(sovraperformance)" if delta >= 0 else "(sottoperformance)"
            benchmark_lines += f"✓ VS {ticker} : {delta:+.0f}% {perf_label}\n"
    else:
        # Fallback if no data
        benchmark_lines = "✓ Sovraperformance vs S&P500\n✓ Sovraperformance vs MSCI World\n✓ Sovraperformance vs Euro Stoxx 50"

    message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 PERCHÈ COPIARE QUESTO PORTAFOGLIO?

📈 STORICO DELLE PERFORMANCE:
+{five_year_return:.0f}% dal cambio di strategia (2020)
~{avg_yearly_return:.0f}% CAGR (rendimento annuo composto)
Raddoppio del capitale stimato in ~{time_to_double:.1f} anni

✅ PUNTI DI FORZA DELLA STRATEGIA:
• Diversificazione intelligente su 3 continenti
• Focus sui megatrend del futuro: AI, Sanità ed Energia
• Mix bilanciato di ETF e azioni individuali ad alto potenziale
• Gestione attiva, trasparente e senza commissioni nascoste

📊 DIFFERENZIALE RISPETTO AI BENCHMARK (Dal 2020):
{benchmark_lines.strip()}

🌐 Hub & Analisi Completa Portafoglio (Dividendi, Metriche, Simulatori):
https://giga89.github.io/portfolio-daily-recap/

🎯 Strategia di lungo termine basata su fondamentali solidi
🔄 Ribilanciamento periodico per ottimizzare il rapporto rischio/rendimento
━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return message


def generate_decision_post(
    recent_closes_text: str,
    current_weights: dict = None,
    history_stats_text: str = '',
) -> str:
    """
    Generate a "decision of the week" post explaining recent trading choices.
    Uses Gemini to write an empathetic, transparent narrative for copiers.

    Args:
        recent_closes_text: Text summary of recently closed positions (from etoro_history)
        current_weights: Current portfolio weights {ticker: %} from BullAware
        history_stats_text: Short stats summary from etoro_history

    Returns:
        str: Formatted post text, or empty string on failure
    """
    if not GENAI_AVAILABLE:
        return ""

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return ""

    models_to_try = list(DEFAULT_GEMINI_MODELS)

    weights_context = ""
    if current_weights:
        top_holdings = sorted(current_weights.items(), key=lambda x: x[1], reverse=True)[:8]
        weights_context = "Current top holdings: " + ", ".join(
            f"{t} ({w:.1f}%)" for t, w in top_holdings
        )

    prompt = f"""You are Andrea Ravalli, an Italian private investor sharing your eToro portfolio journey with your copiers.
You are transparent, humble, and data-driven. You write in a warm, personal tone — like you're talking to friends who trust you with their money.

TODAY'S TASK: Write a "Decision of the Week" post explaining your recent trading decisions.

RECENT CLOSED POSITIONS (last 30 days):
{recent_closes_text if recent_closes_text else 'No recent closes.'}

{weights_context}

PORTFOLIO HISTORY CONTEXT:
{history_stats_text if history_stats_text else ''}

Write a post (max 1400 characters) in ITALIAN that:
1. Opens with a personal, relatable hook (1-2 sentences about the market mood this week)
2. Explains 1-2 specific decisions you made (why you exited or held, what you were thinking)
3. Connects emotionally with copiers ("so che vederlo in rosso fa male, ma...")
4. Ends with your forward-looking thesis (what you're watching next)

TONE: Transparent, confident but humble, empathetic. Never overconfident.
AVOID: Generic phrases, vague claims, percentage promises.
FORMAT: Plain text, no HTML. Use emojis naturally (2-3 max). No bullet lists.

Output ONLY the post text, no introduction or explanation."""

    try:
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(temperature=0.85)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                if response and response.text:
                    print(f"✅ Decision post generated with {model_name}")
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "decision_post")
                    raw_text = _clean_robotic_phrases(response.text.strip())
                    approved, verified_text = _run_post_verification(
                        raw_text,
                        session_name="Decision post",
                        generator_model=model_name,
                    )
                    if not approved or not verified_text:
                        print(f"⚠️ Decision post rejected by verifier ({model_name}), trying next model...")
                        continue
                    return verified_text
            except Exception as exc:
                print(f"⚠️ Decision post model {model_name} failed: {exc}")
                time.sleep(1)

        print("❌ All models failed for decision post")
        return ""

    except Exception as exc:
        print(f"❌ Error generating decision post: {exc}")
        return ""


def generate_empathy_post(
    portfolio_perf: float,
    weekly_perf: float = None,
    market_context: str = '',
    history_stats_text: str = '',
) -> str:
    """
    Generate an empathetic post for copiers during tough market periods or to celebrate gains.
    Connects emotionally, explains the long-term view, and reinforces trust.

    Args:
        portfolio_perf: Current cumulative portfolio performance % (e.g. 156.0)
        weekly_perf: Weekly performance % (negative = drawdown week)
        market_context: Brief market summary for context
        history_stats_text: Short stats from etoro history

    Returns:
        str: Formatted post text, or empty string on failure
    """
    if not GENAI_AVAILABLE:
        return ""

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return ""

    models_to_try = list(DEFAULT_GEMINI_MODELS)

    # Determine emotional context
    if weekly_perf is not None and weekly_perf < -2:
        mood = f"difficult week (portfolio: {weekly_perf:+.1f}% this week)"
        angle = "reassure copiers, explain the bigger picture, normalize short-term pain"
    elif weekly_perf is not None and weekly_perf > 3:
        mood = f"strong week (portfolio: {weekly_perf:+.1f}% this week)"
        angle = "celebrate the gain, remind that discipline drove it, stay humble and grounded"
    else:
        mood = "typical market week"
        angle = "check in with copiers, reinforce the strategy thesis, share your mindset"

    prompt = f"""You are Andrea Ravalli, an Italian private investor on eToro sharing your journey with your copiers.
You have been investing since 2020 and your portfolio is up ~{portfolio_perf:.0f}% cumulative.
You are transparent, humble, and human. You write like you're talking to friends.

TODAY'S TASK: Write a warm, empathetic weekly check-in post.

CURRENT CONTEXT:
- Portfolio cumulative return: +{portfolio_perf:.0f}%
- This week's mood: {mood}
- Your angle: {angle}
- Market context: {market_context if market_context else 'Mixed global markets'}
- Portfolio history note: {history_stats_text[:200] if history_stats_text else ''}

Write a post (max 1200 characters) in ITALIAN that:
1. Opens with a human, relatable moment (something you felt or observed this week)
2. Addresses how the week felt for copiers and validates their emotions
3. Zooms out to the bigger picture (the long-term strategy, the "why")
4. Closes with one concrete thing you are watching next week

TONE: Warm, honest, personal. Like a weekly letter to people who trust you.
AVOID: Generic motivational quotes, exaggerated claims, financial advice promises.
FORMAT: Plain text. 2-4 natural emojis. No bullet lists. Conversational paragraphs.

Output ONLY the post text, no introduction or explanation."""

    try:
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(temperature=0.90)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                if response and response.text:
                    print(f"✅ Empathy post generated with {model_name}")
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "empathy_post")
                    raw_text = _clean_robotic_phrases(response.text.strip())
                    approved, verified_text = _run_post_verification(
                        raw_text,
                        session_name="Empathy post",
                        generator_model=model_name,
                    )
                    if not approved or not verified_text:
                        print(f"⚠️ Empathy post rejected by verifier ({model_name}), trying next model...")
                        continue
                    return verified_text
            except Exception as exc:
                print(f"⚠️ Empathy post model {model_name} failed: {exc}")
                time.sleep(1)

        print("❌ All models failed for empathy post")
        return ""

    except Exception as exc:
        print(f"❌ Error generating empathy post: {exc}")
        return ""


def generate_copy_trading_post(
    history_stats_text: str = "",
    gain_history: list = None,
    portfolio_perf: float = None,
    rankings_data: dict = None,
) -> str:
    """
    Generate a daily Copy Trading education + persuasion post for eToro.

    Explains how Copy Trading works, why copying AndreaRavalli makes sense,
    and uses REAL historical performance data (P&L, win rate, copiers count,
    AUM, risk score, monthly gains) from the eToro account history and live rankings.

    Args:
        history_stats_text: Short stats summary from etoro_history (win rate, P&L, etc.)
        gain_history:       List of monthly gain dicts from fetch_gain_history()
        portfolio_perf:     Cumulative portfolio performance % (e.g. 156.0)
        rankings_data:      Dict with live eToro rankings, copiers, AUM, risk score

    Returns:
        str: Formatted post text in Italian, or fallback text on failure
    """
    if not GENAI_AVAILABLE:
        return _copy_trading_fallback(history_stats_text, gain_history, portfolio_perf, rankings_data)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _copy_trading_fallback(history_stats_text, gain_history, portfolio_perf, rankings_data)

    models_to_try = list(DEFAULT_GEMINI_MODELS)

    # Build rankings and copier context if available from live eToro API
    rankings_context = ""
    if rankings_data:
        copiers = rankings_data.get("copiers", 0)
        aum = rankings_data.get("aumValue", 0)
        risk = rankings_data.get("riskScore", 3)
        win_ratio = rankings_data.get("winRatio", 0.0)
        ytd_gain = rankings_data.get("gain", 0.0) * 100
        five_y_gain = rankings_data.get("fiveYearGain", 0.0) * 100
        weeks = rankings_data.get("weeksSinceRegistration", 0)
        years = round(weeks / 52, 1) if weeks else 0
        rankings_context = (
            f"STATISTICHE UFFICIALI eToro (da API):\n"
            f"- Copiatori attivi: {copiers}\n"
            f"- Asset in gestione (AUM): ~${aum:,.0f}\n"
            f"- Status: Popular Investor Elite\n"
            f"- Punteggio di Rischio: {risk}/10 (Basso rischio, profilo prudente e disciplinato)\n"
            f"- Win Ratio: {win_ratio:.1f}%\n"
            f"- Rendimento YTD 2026: +{ytd_gain:.2f}%\n"
            f"- Rendimento 5 Anni: +{five_y_gain:.1f}%\n"
            f"- Anni di esperienza e presenza su eToro: ~{years} anni\n"
            f"- Profilo Leva: 100% posizioni a zero/bassa leva (no trading con leva speculativa)\n"
        )

    # Build gain history context (last 12 months)
    gain_context = ""
    if gain_history:
        recent = gain_history[-12:] if len(gain_history) > 12 else gain_history
        lines = []
        for entry in recent:
            month = entry.get("date", entry.get("month", "?"))
            gain = entry.get("gain", entry.get("value", 0.0))
            sign = "+" if float(gain) >= 0 else ""
            lines.append(f"  {month}: {sign}{float(gain):.1f}%")
        gain_context = "GUADAGNO MENSILE (ultimi 12 mesi):\n" + "\n".join(lines)

    perf_context = ""
    if portfolio_perf is not None:
        sign = "+" if portfolio_perf >= 0 else ""
        perf_context = f"Performance cumulativa portafoglio: {sign}{portfolio_perf:.1f}%"

    # Rotate post angle to avoid repetition (based on weekday)
    from datetime import datetime as _dt
    weekday = _dt.utcnow().weekday()  # 0=Mon … 6=Sun
    angles = [
        "Come funziona il Copy Trading step-by-step + perché è diverso da un fondo",
        "I miei numeri reali su eToro: performance storica, win rate e trasparenza totale",
        "Domande frequenti sul Copy Trading: rischi, costi, gestione della liquidità e come iniziare",
        "Il mio approccio di investimento prudente: zero leva e diversificazione globale",
        "Copy Trading vs ETF: i vantaggi di una gestione attiva trasparente",
        "Cosa succede al tuo capitale quando mi copi: controllo e libertà totale in ogni momento",
        "I miei principi d'investimento: lungo periodo, gestione del rischio e disciplina",
    ]
    angle = angles[weekday % len(angles)]

    prompt = f"""Sei Andrea Ravalli, Popular Investor Elite italiano su eToro con un portfolio reale, trasparente e prudente.
Il tuo obiettivo oggi è scrivere un post educativo e persuasivo sul Copy Trading di eToro per la tua community.

ANGOLO DEL POST DI OGGI: "{angle}"

DATI REALI DEL PORTAFOGLIO & COPIATORI (usali con naturalezza per dare massima credibilità):
{rankings_context if rankings_context else ''}

{history_stats_text if history_stats_text else 'Portafoglio attivo su eToro da molti anni con risultati costanti.'}

{perf_context}

{gain_context}

OBIETTIVO DEL POST:
1. Spiegare in modo limpido come funziona il Copy Trading su eToro
2. Mostrare perché ha senso copiare la tua strategia (lungo termine, basso rischio score 3, 100% no leva, win rate solido, oltre 8 anni di storico)
3. Essere totalmente onesto e trasparente: il Copy Trading non garantisce profitti, i mercati oscillano
4. Concludere con una domanda aperta stimolante per invitare i lettori a commentare

REGOLE OBBLIGATORIE:
- Scrivi in ITALIANO, tono caldo, accogliente, professionale e autorevole ma mai arrogante
- MAX 1400 caratteri (deve essere compatibile con i limiti eToro senza tagli)
- NO promesse di rendimento futuro
- Usa 2-4 emoji in modo armonioso
- Testo discorsivo a paragrafi, NO lunghi elenchi puntati
- Includi 2-3 cashtag rilevanti del portafoglio: es. $PLTR $NVDA $CCJ $MSFT $AMZN
- Post autonomo e completo

Output ONLY the Italian post text, no introduction or wrapping."""

    try:
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(temperature=0.88)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                if response and response.text:
                    print(f"✅ Copy trading post generated with {model_name}")
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "copy_trading_post")
                    raw_text = _clean_robotic_phrases(response.text.strip())
                    approved, verified_text = _run_post_verification(
                        raw_text,
                        session_name="Copy trading post",
                        generator_model=model_name,
                    )
                    if not approved or not verified_text:
                        print(f"⚠️ Copy trading post rejected by verifier ({model_name}), trying next model...")
                        continue
                    return verified_text
            except Exception as exc:
                print(f"⚠️ Copy trading post model {model_name} failed: {exc}")
                time.sleep(1)

        print("❌ All models failed for copy trading post — using fallback")
        return _copy_trading_fallback(history_stats_text, gain_history, portfolio_perf, rankings_data)

    except Exception as exc:
        print(f"❌ Error generating copy trading post: {exc}")
        return _copy_trading_fallback(history_stats_text, gain_history, portfolio_perf, rankings_data)


def _copy_trading_fallback(
    history_stats_text: str = "",
    gain_history: list = None,
    portfolio_perf: float = None,
    rankings_data: dict = None,
) -> str:
    """Fallback copy trading post when Gemini is unavailable — uses real stats data."""
    perf_line = ""
    if portfolio_perf is not None:
        sign = "+" if portfolio_perf >= 0 else ""
        perf_line = f"\n📈 Performance cumulativa: {sign}{portfolio_perf:.1f}%"

    copier_line = ""
    if rankings_data:
        copiers = rankings_data.get("copiers", 0)
        risk = rankings_data.get("riskScore", 3)
        if copiers > 0:
            copier_line = f"\n👥 {copiers} copiatori attivi | 🛡️ Risk Score {risk}/10 (basso rischio)"

    win_line = ""
    if rankings_data and rankings_data.get("winRatio"):
        win_line = f"\n🎯 Win Ratio: {rankings_data.get('winRatio'):.1f}%"
    elif history_stats_text:
        for line in history_stats_text.splitlines():
            if "win rate" in line.lower():
                win_line = f"\n🎯 {line.strip()}"
                break

    return (
        "💡 Sai come funziona il Copy Trading su eToro?\n\n"
        "Con il Copy Trading puoi replicare in tempo reale e in proporzione tutte le mie operazioni di portafoglio, "
        "con il capitale che scegli tu — mantenendo sempre il pieno controllo e potendo fermare la copia in qualsiasi istante.\n\n"
        f"La mia strategia punta su fondamentali solidi, diversificazione globale e zero leva speculativa.{perf_line}{copier_line}{win_line}\n\n"
        "Investire con metodo e disciplina nel lungo periodo fa la differenza.\n\n"
        "⚠️ Ricorda: i rendimenti passati non sono garanzia di risultati futuri. Investire comporta rischi.\n\n"
        "Hai curiosità o dubbi sul funzionamento della copia? Scrivimelo nei commenti qui sotto 👇"
    )


# ── 1. Daily Stock Focus Deep-Dive Post ────────────────────────────────────────

def generate_stock_focus_post(ticker: str = None) -> tuple[str, str]:
    """
    Generates a deep-dive asset post for eToro & Telegram:
    "Perché ho il titolo X, possibili upside e possibili downside".
    Includes primary tags across exchanges (e.g. $ENI.MI and $E) + 2-3 related competitor tags.

    Returns:
        tuple: (ticker_symbol, formatted_post_text)
    """
    from portfolio_manager import load_config, get_ticker_all_tags, get_related_tickers
    from portfolio_manager import load_config, get_ticker_all_tags, get_related_tickers, get_asset_metadata
    from gist_storage import get_used_stock_focus_tickers, save_used_stock_focus_ticker
    import random

    config = load_config()
    tickers = config.get("tickers", {})

    if not tickers:
        print("⚠️ No tickers in portfolio config for stock focus post")
        return "", ""

    import time

    # Case-insensitive ticker lookup dictionary for robustness
    ticker_map = {t.upper(): t for t in tickers.keys()}

    # Exclude money market ETFs, physical metal ETFs, and frozen Russian assets from stock focus candidates
    stock_candidates = sorted([t for t in tickers.keys() if t not in ['IB01.L', 'PPFB.DE', 'MNODL.L', 'NVTKL.L']])
    stock_candidates = sorted([t for t in tickers.keys() if t not in ['IB01.L', 'XEON.DE', 'PPFB.DE', 'MNODL.L', 'NVTKL.L']])
    if not stock_candidates:
        stock_candidates = sorted(list(tickers.keys()))

    if ticker and ticker.upper() in ticker_map:
        ticker = ticker_map[ticker.upper()]
    else:
        used_tickers = get_used_stock_focus_tickers()
        unused = [t for t in stock_candidates if t not in used_tickers]
        if unused:
            seed_idx = int(time.time_ns()) % len(unused)
            ticker = unused[seed_idx]
        else:
            # All have been used at least once; pick from the ones least recently used
            least_recent = [t for t in stock_candidates if t not in used_tickers[-len(stock_candidates)//2:]]
            pool = least_recent if least_recent else stock_candidates
            seed_idx = int(time.time_ns()) % len(pool)
            ticker = pool[seed_idx]

    save_used_stock_focus_ticker(ticker)
    meta = get_asset_metadata(ticker)
    yahoo_ticker = meta.get("yahoo_ticker", ticker)
    company_name = meta.get("name", tickers.get(ticker, [ticker, ticker])[1])
    primary_tags = meta.get("primary_tags") or get_ticker_all_tags(ticker)
    related_tags = meta.get("related_tickers") or get_related_tickers(ticker)

    primary_tags_str = " ".join(primary_tags)
    related_tags_str = " ".join(related_tags)

    sector_str = meta.get("sector", "Settore")
    asset_class_str = meta.get("asset_class", "Stock")
    thesis_str = meta.get("thesis", "")
    dividend_policy_str = meta.get("dividend_policy", "Nessuna informazione")
    is_dividend = meta.get("is_dividend_paying", False)
    upsides = meta.get("upside_catalysts", [])
    downsides = meta.get("downside_risks", [])

    upsides_formatted = "\n".join([f"• {u}" for u in upsides]) if upsides else "• Crescita fondamentale e posizionamento competitivo"
    downsides_formatted = "\n".join([f"• {d}" for d in downsides]) if downsides else "• Rischi macroeconomici e di settore"

    print(f"📌 Generating Stock Focus post for {ticker} ({company_name})...")
    print(f"   Sector: {sector_str} | Asset Class: {asset_class_str} | Div Paying: {is_dividend}")
    print(f"   Primary tags: {primary_tags_str} | Related tags: {related_tags_str}")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ GEMINI_API_KEY not set, skipping stock focus post generation")
        return ticker, ""

    models_to_try = list(DEFAULT_GEMINI_MODELS)

    # Fetch live weight for this specific ticker
    weight_str = ""
    try:
        from finance_fetcher import fetch_portfolio_weights
        weights = fetch_portfolio_weights()
        w = weights.get(ticker, 0.0)
        if w > 0:
            weight_str = f"- Peso attuale certificato in portafoglio: {w:.2f}%\n"
    except Exception:
        pass

    dividend_constraint = (
        "DIVIETO ASSOLUTO DI PARLARE DI DIVIDENDI O CEDOLE: questo asset è ad ACCUMULAZIONE (Acc) o non stacca dividendi. NON usare mai parole come 'dividendo', 'cedola', 'flusso cedolare', 'income', 'rendimento da dividendo' o 'payout'! Concentrati al 100% sulla crescita del capitale, trend industriale e tesi fondamentale."
        if not is_dividend
        else f"POLITICA DIVIDENDI CERTIFICATA: {dividend_policy_str}. Se citi i dividendi, attieniti scrupolosamente a questi dati senza esagerare."
    )

    prompt = f"""Sei un investitore privato esperto su eToro.
Scrivi un post di approfondimento e analisi fondamentale su un singolo strumento presente nel nostro portafoglio.

DATI VERIFICATI E CERTIFICATI DELLO STRUMENTO IN FOCUS:
- Strumento: {company_name}
- Ticker: {ticker} (Yahoo: {yahoo_ticker})
{weight_str}- Tipo Asset: {asset_class_str}
- Settore / Industria: {sector_str}
- Politica Dividendi Reale: {dividend_policy_str}
- Tesi di Investimento Reale: {thesis_str}
- Catalizzatori di Crescita Certificati (Upside):
{upsides_formatted}
- Rischi di Mercato Certificati (Downside):
{downsides_formatted}
- Tag principali da includere nel testo: {primary_tags_str}
- Tag di titoli correlati/competitor da includere nel testo: {related_tags_str}

REGOLE MANDATARIE PER IL TESTO (in ITALIANO):
1. Titolo iniziale accattivante: "🔍 FOCUS ASSET: Perché ho in portafoglio {company_name} {primary_tags[0]}" (SENZA parentesi tonde attorno al tag!)
2. Spiega con precisione LA TESI DI INVESTIMENTO ("Perché ho questo strumento in portafoglio"). Se indicato il peso, citalo con precisione ({weight_str.strip() if weight_str else ''}).
3. IMPORTANTE: Parla in prima persona in modo naturale ("Nel mio portafoglio...", "Punto su questo asset perché..."). È SEVERAMENTE VIETATO usare formule come "Come Andrea Ravalli..." o presentarti per nome!
4. Sezione "🚀 POSSIBILI UPSIDE": 2-3 catalizzatori principali basati rigorosamente sui punti forniti sopra.
5. Sezione "⚠️ POSSIBILI DOWNSIDE": 2-3 rischi principali basati rigorosamente sui rischi forniti sopra.
6. GUARDRAIL ANTI-ALLUCINAZIONE DIVIDENDI:
   {dividend_constraint}
7. GUARDRAIL ANTI-ALLUCINAZIONE SETTORE & IDENTITÀ:
   È SEVERAMENTE VIETATO alterare il settore dell'asset o confonderlo con altri strumenti. Parla solo ed esclusivamente del business/settore certificato ({sector_str}). Se l'asset è $WDEF.L, si tratta di WisdomTree Europe Defence UCITS ETF (difesa e aerospazio UE ad accumulazione, ZERO dividendi), MAI Equity Income o 'Windows Europe'.
8. Inserisci in modo fluido ed organico i tag principali ({primary_tags_str}) e i tag dei titoli correlati ({related_tags_str}) nel testo.
9. Mantieni un tono trasparente, professionale ed esaustivo ma facile da leggere (massimo 1400 caratteri).
10. Usa solo emoji standard universalmente supportate (🔍, 🚀, ⚠️, 📊, 👇, 👤, 🎁).
11. REGOLE CASHTAG ETORO: Ogni cashtag (es. {primary_tags_str}) DEVE avere sempre uno spazio prima e dopo per essere cliccabile su eToro. NON racchiudere MAI i cashtag tra parentesi tonde (scrivi ad es. "...competitor come $IBE.MC e $RWE.DE" invece di "($IBE.MC)") e NON incollare punteggiatura al tag (scrivi "$EDP.LS ?" invece di "$EDP.LS?").

Output ONLY the post text in Italian, no extra conversational preamble."""

    try:
        client = genai.Client(api_key=api_key)
        config_gen = types.GenerateContentConfig(temperature=0.7)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config_gen,
                )
                if response and response.text:
                    print(f"✅ Stock Focus post generated for {ticker} using {model_name}")
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "stock_focus_post")
                    cleaned_post = _clean_robotic_phrases(response.text.strip())
                    approved, verified_text = _run_post_verification(
                        cleaned_post,
                        primary_ticker=ticker,
                        session_name=f"Stock focus ({ticker})",
                        generator_model=model_name,
                    )
                    if not approved or not verified_text:
                        print(f"⚠️ Stock focus post on {ticker} rejected by verifier ({model_name}), trying next model...")
                        continue
                    save_used_stock_focus_ticker(ticker)
                    cleaned_post = _clean_robotic_phrases(response.text.strip())
                    return ticker, cleaned_post
                    return ticker, verified_text
            except Exception as exc:
                print(f"⚠️ Stock focus model {model_name} failed: {exc}")
                time.sleep(1)

        print(f"❌ All models failed for stock focus post on {ticker}")
        return ticker, ""

    except Exception as exc:
        print(f"❌ Error generating stock focus post: {exc}")
        return ticker, ""


# ── 2. Saturday Afternoon: Weekly Portfolio Outlook ───────────────────────────

def generate_weekly_portfolio_outlook() -> str:
    """
    Generates Saturday afternoon post:
    "Cosa ci aspetta nella prossima settimana per i titoli in portafoglio" (earnings, catalysts, events).

    Returns:
        str: Formatted post in Italian
    """
    from portfolio_manager import load_config
    config = load_config()
    tickers = config.get("tickers", {})
    ticker_names = [f"{name} (${t})" for t, (_, name) in list(tickers.items())[:15]]
    context_str = ", ".join(ticker_names)

    print("📅 Generating Saturday Portfolio Outlook post...")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ GEMINI_API_KEY not set, skipping portfolio outlook post")
        return ""

    models_to_try = list(DEFAULT_GEMINI_MODELS)

    prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro.
Scrivi il post del Sabato pomeriggio per i tuoi follower e copier focalizzato su:
"COSA CI ASPETTA NELLA PROSSIMA SETTIMANA PER I TITOLI IN PORTAFOGLIO".

Usa il tuo strumento di ricerca Google per cercare le notizie, le trimestrali (earnings), gli eventi societari e i catalizzatori previsti per la prossima settimana relativi ai titoli del nostro portafoglio.

PORTAFOGLIO PRINCIPALE:
{context_str}

REGOLE PER IL TESTO (in ITALIANO):
1. Inizio caldo ed empatico: "📅 ANTEPRIMA SETTIMANALE: I catalizzatori dei nostri titoli per la prossima settimana"
2. Analizza 3-4 appuntamenti o eventi chiave previsti per i nostri titoli nella prossima settimana (es. risultati trimestrali, lanci prodotti, assemblee, date ex-dividendo o attesa per dati di settore).
3. Spiega in modo chiaro ed esaustivo cosa monitoreremo e come questi eventi si inseriscono nella nostra tesi di investimento.
4. Usa i tag delle aziende menzionate (es. $NVDA, $LLY, $MSFT, $AZN.L).
5. Mantieni la lunghezza totale sotto i 1500 caratteri.
6. Stile trasparente, appassionato ed empatico.

Output ONLY the post text in Italian."""

    try:
        client = genai.Client(api_key=api_key)
        config_gen = types.GenerateContentConfig(temperature=0.85)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config_gen,
                )
                if response and response.text:
                    print(f"✅ Portfolio Outlook post generated using {model_name}")
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "portfolio_outlook_post")
                    return response.text.strip()
                    raw_text = response.text.strip()
                    approved, verified_text = _run_post_verification(
                        raw_text,
                        session_name="Weekly portfolio outlook",
                        generator_model=model_name,
                    )
                    if not approved or not verified_text:
                        print(f"⚠️ Portfolio outlook rejected by verifier ({model_name}), trying next model...")
                        continue
                    return verified_text
            except Exception as exc:
                print(f"⚠️ Portfolio outlook model {model_name} failed: {exc}")
                time.sleep(1)

        print("❌ All models failed for portfolio outlook post")
        return ""

    except Exception as exc:
        print(f"❌ Error generating portfolio outlook post: {exc}")
        return ""


# ── 3. Saturday Afternoon: Global Macro Outlook ───────────────────────────────

def generate_weekly_macro_outlook() -> str:
    """
    Generates Saturday afternoon post:
    "Cosa ci aspetta nella prossima settimana a livello macroeconomico globale" (FED/ECB, CPI, NFP, GDP).

    Returns:
        str: Formatted post in Italian
    """
    print("🌍 Generating Saturday Global Macro Outlook post...")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ GEMINI_API_KEY not set, skipping macro outlook post")
        return ""

    models_to_try = list(DEFAULT_GEMINI_MODELS)

    prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro.
Scrivi il post del Sabato pomeriggio per i tuoi follower e copier focalizzato su:
"COSA CI ASPETTA NELLA PROSSIMA SETTIMANA A LIVELLO MACROECONOMICO GLOBALE".

Usa il tuo strumento di ricerca Google per consultare il calendario macroeconomico globale della prossima settimana (dati USA, Europa, Cina, banche centrali FED/BCE).

REGOLE PER IL TESTO (in ITALIANO):
1. Inizio chiaro e d'impatto: "🌍 MACRO OUTLOOK: Il calendario e gli eventi chiave della prossima settimana sui mercati"
2. Elenca e spiega i 3-4 principali appuntamenti macroeconomici previsti per la settimana in arrivo (es. decisioni sui tassi di interesse FED o BCE, dati sull'inflazione CPI/PCE, report sul lavoro NFP, PIL, stime di crescita o tensioni geopolitiche).
3. Fornisci la tua interpretazione di come questi dati potrebbero influenzare i mercati globali e l'impatto potenziale sul nostro portafoglio.
4. OBBLIGATORIO - INSERISCI I TAG NEL TESTO: Devi obbligatoriamente includere ed integrare nel testo i tag degli indici di mercato principali (es. $SPX500, $NSDQ100, $EuroStoxx) E ALMENO 2-3 TAG di titoli del nostro portafoglio particolarmente sensibili ai dati macro (es. $NVDA, $ENI.MI, $NOVO-B.CO, $MSFT, $CCJ, $ABBV).
5. Mantieni la lunghezza totale sotto i 1500 caratteri.
6. Stile lucido, professionale, accessibile ed esaustivo.

Output ONLY the post text in Italian."""

    try:
        client = genai.Client(api_key=api_key)
        config_gen = types.GenerateContentConfig(temperature=0.85)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config_gen,
                )
                if response and response.text:
                    print(f"✅ Global Macro Outlook post generated using {model_name}")
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "macro_outlook_post")
                    return response.text.strip()
                    raw_text = response.text.strip()
                    approved, verified_text = _run_post_verification(
                        raw_text,
                        session_name="Weekly macro outlook",
                        generator_model=model_name,
                    )
                    if not approved or not verified_text:
                        print(f"⚠️ Macro outlook rejected by verifier ({model_name}), trying next model...")
                        continue
                    return verified_text
            except Exception as exc:
                print(f"⚠️ Macro outlook model {model_name} failed: {exc}")
                time.sleep(1)

        print("❌ All models failed for macro outlook post")
        return ""

    except Exception as exc:
        print(f"❌ Error generating macro outlook post: {exc}")
        return ""


# ── 4. Daily Crypto Market & Sentiment Recap ─────────────────────────────────

def generate_crypto_daily_post(crypto_data: dict = None) -> tuple[str, str]:
    """
    Generates a daily cryptocurrency recap for eToro & Telegram:
    - Analyzes 4 crypto assets ($BTC, $ETH, $SOL, $TRX)
    - Incorporates exact live spot prices, 24h % change, 24h volumes, and Fear & Greed Index
    - Factual analysis of daily catalysts and market sentiment
    - Concludes with an engaging question to spark discussion on eToro

    Returns:
        tuple: (title, formatted_post_text)
    """
    import crypto_fetcher
    if not crypto_data:
        crypto_data = crypto_fetcher.fetch_crypto_daily_data()

    sentiment = crypto_data.get("sentiment", {})
    sent_score = sentiment.get("score", 50)
    sent_cls = sentiment.get("classification_it", "Neutrale")
    sent_emoji = sentiment.get("emoji", "⚖️")

    cryptos = crypto_data.get("cryptos", {})
    crypto_list = list(cryptos.values())

    # Build dynamic crypto cards string for fallback and prompt
    blocks = []
    cashtags_list = []
    hashtags_list = ["#Crypto", "#eToro", "#Investimenti"]

    for d in crypto_list:
        sym = d.get("symbol", "")
        name = d.get("name", sym)
        emoji = d.get("emoji", "🪙")
        cashtag = d.get("cashtag", f"${sym}")
        cashtags_list.append(cashtag)
        hashtags_list.append(f"#{name.replace(' ', '')}")

        portfolio_note = " | Posizione attiva in portafoglio" if sym == "TRX" else ""
        block = (
            f"{emoji} {cashtag} ({name}): {d.get('price_formatted', 'N/D')} ({d.get('change_24h', 0.0):+.2f}%)\n"
            f"↳ Volume 24h: {d.get('volume_formatted', 'N/D')} | Range: {d.get('low_formatted', 'N/D')} - {d.get('high_formatted', 'N/D')}{portfolio_note}"
        )
        blocks.append(block)

    blocks_str = "\n\n".join(blocks)
    cashtags_str = " ".join(cashtags_list)
    hashtags_str = " ".join(hashtags_list)

    # Build factual summary metrics string
    facts_list = []
    for sym, d in cryptos.items():
        portfolio_tag = " [IN PORTAFOGLIO ANDREA]" if sym == "TRX" else ""
        facts_list.append(
            f"• {d.get('emoji', '🪙')} {d.get('name', sym)} ({d.get('cashtag', f'${sym}')}){portfolio_tag}: "
            f"Prezzo {d.get('price_formatted', 'N/D')}, Variazione 24h: {d.get('change_24h', 0.0):+.2f}%, "
            f"Volume 24h: {d.get('volume_formatted', 'N/D')}, Range: {d.get('low_formatted', 'N/D')} - {d.get('high_formatted', 'N/D')}"
        )
    facts_str = "\n".join(facts_list)

    # Fallback template if Gemini is unavailable
    fallback_text = f"""⚡ FLASH CRYPTO DEL GIORNO & SENTIMENT 🪙

📊 Indice Crypto Fear & Greed: {sent_score}/100 · {sent_cls} {sent_emoji}

Ecco i dati certi e i livelli chiave della sessione sulle 4 crypto monitorate:

{blocks_str}

💡 SINTESI DI MERCATO:
La sessione evidenzia una fase di consolidamento con volumi e sentiment allineati all'attuale contesto macro. $BTC e $ETH continuano a dettare la direzione della liquidità globale, mentre i principali altcoin monitorati e $TRX (detenuto in portafoglio) mostrano dinamiche di transazione e adozione on-chain resilienti.

💬 Quale di questi 4 asset ritenete abbia il miglior rapporto rischio/rendimento nei prossimi mesi? Avete posizioni crypto aperte? 👇

{hashtags_str}"""

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ℹ️ GEMINI_API_KEY missing, using high-quality fallback template for crypto recap")
        return "Daily crypto recap", fallback_text

    models_to_try = list(DEFAULT_GEMINI_MODELS)

    prompt = f"""Sei Andrea Ravalli, un Popular Investor italiano su eToro.
Scrivi un post giornaliero in ITALIANO dedicato all'aggiornamento del mercato CRYPTO da pubblicare su eToro e Telegram.

DATI CERTI E REALI DELLA SESSIONE:
- Indice Crypto Fear & Greed: {sent_score}/100 ({sent_cls} {sent_emoji})
- Dati di mercato verificati per le 4 crypto su eToro:
{facts_str}

REGOLE PER IL POST:
1. Titolo d'impatto: "⚡ FLASH CRYPTO DEL GIORNO & SENTIMENT 🪙"
2. Cita subito il punteggio esatto del Crypto Fear & Greed Index ({sent_score}/100) spiegando cosa significa per il sentiment attuale.
3. Riporta i dati certi per ciascuna delle 4 crypto ({cashtags_str}): prezzo esatto, variazione 24h % e volume 24h. Ricorda che $TRX è detenuto anche nel nostro portafoglio.
4. Fornisci un commento sintetico, lucido e professionale sui fatti del giorno, sui flussi di liquidità e sui driver di mercato.
5. Includi OBBLIGATORIAMENTE i cashtag ({cashtags_str}) nel testo e gli hashtag finali ({hashtags_str}).
6. Concludi con una domanda aperta e stimolante per invitare i follower di eToro a commentare.
7. Lunghezza: 900-1400 caratteri. Tono autorevole, equilibrato e non da "hype" finanziario.

Output ONLY the post text in Italian."""

    try:
        client = genai.Client(api_key=api_key)
        config_gen = types.GenerateContentConfig(temperature=0.8)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config_gen,
                )
                if response and response.text:
                    print(f"✅ Crypto Daily Recap post generated using {model_name}")
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "crypto_daily_post")
                    cleaned_post = _clean_robotic_phrases(response.text.strip())
                    return "Daily crypto recap", cleaned_post
                    approved, verified_text = _run_post_verification(
                        cleaned_post,
                        session_name="Daily crypto recap",
                        generator_model=model_name,
                    )
                    if not approved or not verified_text:
                        print(f"⚠️ Crypto recap rejected by verifier ({model_name}), trying next model...")
                        continue
                    return "Daily crypto recap", verified_text
            except Exception as exc:
                err_str = str(exc).lower()
                is_quota = '429' in err_str or 'quota' in err_str or 'resource_exhausted' in err_str
                print(f"⚠️ Crypto recap model {model_name} failed: {exc}")
                if is_quota:
                    print(f"   ⏳ Model {model_name} rate limited (429). Pausing 6s before cascading...")
                    time.sleep(6.0)
                else:
                    time.sleep(1.0)

        print("❌ All models failed for crypto recap post, using fallback")
        return "Daily crypto recap", fallback_text

    except Exception as exc:
        print(f"❌ Error generating crypto recap post: {exc}")
        return "Daily crypto recap", fallback_text


