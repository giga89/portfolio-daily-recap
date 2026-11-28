#!/usr/bin/env python3
"""
AI Community Comment Responder for eToro (Auto-Pilot & High Conviction)
=====================================================================
Scans recent eToro posts (up to 7 days back) for genuine community comments without a reply,
and generates point-first, portfolio-grounded responses aligned with
Andrea Ravalli's Popular Investor strategy and real holdings.

Features & Strict Quality Control:
  • Two-Pass Generation Architecture:
      - Pass 1 (Drafting): Contextual draft generation grounded in full post text,
        verified portfolio metadata/weights, and authentic non-DCA voice.
      - Pass 2 (Validator / Judge): Adversarial editorial, specificity & compliance evaluation.
  • Strict Deterministic Guardrails:
      - Categorically blocks any mention of DCA, Dollar-Cost Averaging, PAC, or periodic buying.
      - Enforces accurate classification of $WDEF.L (European Defence sector ETF, NOT defensive).
      - Rejects truncated / cut-off sentences, trailing prepositions, and markdown bold (**).
  • Anti-Duplication & Safe Skip-on-Failure:
      - Uses Gist & local answered_comments.json state.
      - If all AI providers fail or fail verification, safely skips without publishing
        generic static templates so the comment is retried cleanly on the next cycle.
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

# Ensure unbuffered output in CI / background executions
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

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
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

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

# Multi-model priority hierarchy imported cleanly from centralized cascade
try:
    from ai_model_cascade import (
        DEFAULT_GEMINI_MODELS,
        COMMENT_GEMINI_MODELS,
        FAST_GEMINI_MODELS,
        REVIEWER_GEMINI_MODELS,
        build_http_options,
        build_thinking_config,
    )
except ImportError:
    try:
        from src.ai_model_cascade import (
            DEFAULT_GEMINI_MODELS,
            COMMENT_GEMINI_MODELS,
            FAST_GEMINI_MODELS,
            REVIEWER_GEMINI_MODELS,
            build_http_options,
            build_thinking_config,
        )
    except ImportError:
        DEFAULT_GEMINI_MODELS = [
            'gemini-4-hydrogen',
            'gemini-3.6-flash',
            'gemini-3-flash-preview',
            'gemini-3.5-flash',
            'gemini-3.5-flash-lite',
            'gemini-3.1-flash-lite',
            'gemini-2.5-flash',
        ]
        COMMENT_GEMINI_MODELS = list(DEFAULT_GEMINI_MODELS)
        FAST_GEMINI_MODELS = [
            'gemini-3.5-flash-lite',
            'gemini-3.1-flash-lite',
            'gemini-3.5-flash',
            'gemini-4-hydrogen',
            'gemini-3.6-flash',
            'gemini-2.5-flash',
        ]
        REVIEWER_GEMINI_MODELS = [
            'gemini-3.6-flash',
            'gemini-4-hydrogen',
            'gemini-3-flash-preview',
            'gemini-3.5-flash',
            'gemini-3.5-flash-lite',
            'gemini-2.5-flash',
        ]
        def build_http_options(types_module, timeout_seconds=45.0, api_version="v1beta"):
            if types_module is None or not hasattr(types_module, "HttpOptions"):
                return None
            ms = int(max(1000, round(float(timeout_seconds) * 1000)))
            try:
                return types_module.HttpOptions(timeout=ms, api_version=api_version)
            except TypeError:
                return types_module.HttpOptions(timeout=ms)
        def build_thinking_config(types_module, model_name, fast_mode=False, budget=None):
            return None


PORTFOLIO_SYSTEM_PROMPT = """
You are Andrea Ravalli's Official AI Co-Pilot for the eToro Popular Investor Program.
Your job is to draft specific, grounded, authentic, and disciplined replies to user comments on eToro posts.

CORE PROFILE & OPERATIONAL PHILOSOPHY:
1. Track Record & Active Management Style:
   - +200% cumulative gain since 2020.
   - Active long-term investing (3-5+ years time horizon) based on fundamental conviction, calibrated position sizing, discretionary rebalancing, and dividend reinvestment.
   - Certified eToro Risk Score 3/10 (conservative/moderate risk) and zero leverage (1x real stocks/ETFs only, no CFD leverage gambling, no shorting).
   - Risk buffers & cash reserves: short-term US Treasury reserve ($IB01.L) for liquidity/dry powder, Physical Gold ETC ($PPFB.DE) as a safe-haven hedge, plus defensive sectors in Healthcare ($LLY, $ABBV, $ABT.US, $AZN.L, $HUM) and Consumer Staples ($WMT, $ULVR.L).

2. STRICT PROHIBITIONS (ZERO TOLERANCE):
   - NEVER mention, suggest, or imply DCA, Dollar-Cost Averaging, PAC, "piano di accumulo", "ingressi periodici", "ingressi frazionati", or recurring deposits. We do NOT practice DCA/PAC and NEVER will. If a user asks about PAC or periodic buying, state plainly (without using those forbidden terms) that we do not follow automated periodic buying schedules, but manage positions actively based on fundamentals, valuations, and risk balance.
   - NEVER call $WDEF.L (WisdomTree Europe Defence UCITS ETF) a defensive stock, defensive hedge, or safe haven: it is a thematic European Defence & Aerospace sector ETF (accumulating, zero dividends), NOT a defensive/safe-haven cushion.
   - NEVER mention purged assets (XEON, MAU, SPCX, MELI, WCLD, RACE/Ferrari, ANT.24-7/Anthropic).
   - NEVER attribute dividends to accumulating assets ($WDEF.L, $INDO.PA, $IB01.L, $PPFB.DE) or non-dividend holdings ($ETOR, $TRX, $PLTR, $AMZN, $01211.HK).

3. ANTI-GENERICITY & POINT-FIRST RULES:
   - FIRST SUBSTANTIVE SENTENCE: Directly address the exact point, company, figure, timeframe, or criticism raised by the user, grounded in the actual post content provided below.
   - OWNED HOLDINGS: When a ticker/company is marked IN PORTAFOGLIO in the grounding context, write from the perspective of an active shareholder (e.g. referencing its real role/weight in the portfolio). NEVER say "monitoriamo realtà come..." as if we didn't own it. If an asset is marked NON IN PORTAFOGLIO, never claim we hold it.
   - NO CANNED PR LITANY: Do NOT repeat "Risk Score 3/10 + zero leva + 3-5+ anni + rumore di breve termine" in every reply. Cite risk/horizon ONLY when directly relevant to the user's point (e.g. drawdown anxiety, volatility, leverage, copying).
   - HANDLING CRITICISM OR SARCASM: Stay calm, respectful, and address the substance of the critique directly without robotic praise like "Grazie mille per il riscontro!".
   - LANGUAGE & FORMATTING: Match the user's language (Italian or English). Keep to 1-2 crisp paragraphs (55-120 words for substantive comments). Plain clean text only: NO markdown bold (**). Use 1-2 natural emojis. Never give individualized financial advice or guarantee returns. Vary openings and closings naturally.
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
VALID_TERMINAL_EMOJIS = (
    '🤝', '📈', '🚀', '✨', '💼', '🎯', '📊', '🛡️', '👋', '🙏', '🔥', '💡',
    '🥇', '🚢', '💵', '🪙', '🌍', '🔋', '⛽', '💊', '💉', '🏥', '🧬', '🔬',
    '⚡', '⛏️', '🔍', '🌬️', '🛒', '🚗', '📦', '🔌', '🏛️', '🏦', '🌏', '🤖', '💻',
)


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


def _normalize_ticker_alias(raw_ticker: str) -> str:
    """Normalize ticker variants and aliases to canonical portfolio keys."""
    clean = str(raw_ticker or "").replace("$", "").strip().rstrip(".,;:!?").upper()
    alias_map = {
        "GOOGL": "GOOG",
        "ABT": "ABT.US",
        "1211.HK": "01211.HK",
        "BESI": "BESI.NV",
        "WDEF": "WDEF.L",
        "PPFB": "PPFB.DE",
        "IB01": "IB01.L",
        "PRY": "PRY.MI",
        "ENI": "ENI.MI",
        "ENEL": "ENEL.MI",
        "TRIG": "TRIG.L",
        "AZN": "AZN.L",
        "GLEN": "GLEN.L",
        "ULVR": "ULVR.L",
        "VOF": "VOF.L",
        "VOW3": "VOW3.DE",
        "INDO": "INDO.PA",
        "IQQL": "IQQL.DE",
        "SX7PEX": "SX7PEX.DE",
        "EXV1.DE": "SX7PEX.DE",
        "TSMC": "TSM",
    }
    return alias_map.get(clean, clean)


def _is_valid_ticker_token(sym: str) -> bool:
    """Filter out numeric currency tokens like 440, 0.3085, 115.23M, 70K."""
    clean = str(sym or "").replace("$", "").strip().rstrip(".,;:!?").upper()
    if not clean or clean in ("M", "B", "K"):
        return False
    if re.match(r'^\d+(?:[.,]\d+)?[KMBT%]?$', clean):
        return False
    if re.match(r'^\d{4,5}\.[A-Z]{2}$', clean):
        return True
    return bool(re.match(r'^[A-Z][A-Z0-9.-]{0,11}$', clean))


_PORTFOLIO_WEIGHTS_CACHE: Optional[Dict[str, float]] = None
_PORTFOLIO_METADATA_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def _get_portfolio_metadata_and_weights() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, float]]:
    """Load and cache PORTFOLIO_ASSETS_METADATA and data/portfolio_weights.json."""
    global _PORTFOLIO_WEIGHTS_CACHE, _PORTFOLIO_METADATA_CACHE
    if _PORTFOLIO_METADATA_CACHE is None:
        try:
            from portfolio_manager import PORTFOLIO_ASSETS_METADATA
            _PORTFOLIO_METADATA_CACHE = dict(PORTFOLIO_ASSETS_METADATA)
        except ImportError:
            try:
                from src.portfolio_manager import PORTFOLIO_ASSETS_METADATA
                _PORTFOLIO_METADATA_CACHE = dict(PORTFOLIO_ASSETS_METADATA)
            except ImportError:
                _PORTFOLIO_METADATA_CACHE = {}

    if _PORTFOLIO_WEIGHTS_CACHE is None:
        weights_path = os.path.join(DATA_DIR, "portfolio_weights.json")
        loaded: Dict[str, float] = {}
        if os.path.exists(weights_path):
            try:
                with open(weights_path, "r", encoding="utf-8") as f:
                    raw_w = json.load(f)
                    if isinstance(raw_w, dict):
                        for k, v in raw_w.items():
                            try:
                                loaded[_normalize_ticker_alias(k)] = float(v)
                            except (TypeError, ValueError):
                                pass
            except Exception:
                pass
        _PORTFOLIO_WEIGHTS_CACHE = loaded

    return _PORTFOLIO_METADATA_CACHE, _PORTFOLIO_WEIGHTS_CACHE


_NAME_TO_PORTFOLIO_TICKER: List[Tuple[str, str]] = [
    (r'\bnvidia\b', 'NVDA'),
    (r'\bamd\b|advanced\s+micro\s+devices', 'AMD'),
    (r'\bmicrosoft\b', 'MSFT'),
    (r'\bamazon\b|\baws\b', 'AMZN'),
    (r'\balphabet\b|\bgoogle\b', 'GOOG'),
    (r'\bpalantir\b', 'PLTR'),
    (r'\bbroadcom\b', 'AVGO'),
    (r'\btsmc\b|taiwan\s+semiconductor', 'TSM'),
    (r'\bmarvell\b', 'MRVL'),
    (r'\bbesi\b|be\s+semiconductor', 'BESI.NV'),
    (r'\beli\s+lilly\b|\blilly\b', 'LLY'),
    (r'\babbvie\b', 'ABBV'),
    (r'\babbott\b', 'ABT.US'),
    (r'\bhumana\b', 'HUM'),
    (r'\bastrazeneca\b', 'AZN.L'),
    (r'\bcameco\b', 'CCJ'),
    (r'\benel\b', 'ENEL.MI'),
    (r'\beni\b', 'ENI.MI'),
    (r'\bprysmian\b', 'PRY.MI'),
    (r'\bglencore\b', 'GLEN.L'),
    (r'\btrig\b|renewables\s+infrastructure', 'TRIG.L'),
    (r'\bwalmart\b', 'WMT'),
    (r'\bvolkswagen\b', 'VOW3.DE'),
    (r'\bunilever\b', 'ULVR.L'),
    (r'\bbyd\b', '01211.HK'),
    (r'\bcosco(?:\s+shipping)?\b', '1919.HK'),
    (r'\bping\s+an\b', '2318.HK'),
    (r'\bvinacapital\b|\bvietnam\b', 'VOF.L'),
    (r'\bindonesia\b', 'INDO.PA'),
    (r'\bwisdomtree\s+europe\s+defence\b|\bwdef\b', 'WDEF.L'),
    (r'\bphysical\s+gold\b|\bppfb\b', 'PPFB.DE'),
    (r'\bib01\b|treasury\s+bond\s+0-1', 'IB01.L'),
    (r'\bieur\b', 'IEUR'),
    (r'\biqql\b|listed\s+private\s+equity', 'IQQL.DE'),
    (r'\bsx7pex\b|stoxx\s+europe\s+600\s+banks', 'SX7PEX.DE'),
    (r'\btron\b', 'TRX'),
    (r'\betoro\s+group\b', 'ETOR'),
]


def _extract_portfolio_and_external_tickers(
    texts: List[str],
    seed_tickers: Optional[List[str]] = None,
) -> Tuple[List[str], List[str]]:
    """
    Resolve all portfolio holdings and external market tickers mentioned across texts
    (via $cashtags, seed tickers, and company/ETF names without '$').
    Returns: (in_portfolio_tickers, external_tickers)
    """
    metadata, _ = _get_portfolio_metadata_and_weights()
    ordered_candidates: List[str] = []

    def _add_candidate(raw_sym: str) -> None:
        if not _is_valid_ticker_token(raw_sym):
            return
        canon = _normalize_ticker_alias(raw_sym)
        if canon and canon not in ordered_candidates:
            ordered_candidates.append(canon)

    for t in (seed_tickers or []):
        _add_candidate(t)

    combined = "\n".join(str(x or "") for x in texts)
    for m in re.findall(r'\$([A-Za-z0-9_.-]+)', combined):
        _add_candidate(m)

    for pattern, canon in _NAME_TO_PORTFOLIO_TICKER:
        if re.search(pattern, combined, flags=re.IGNORECASE):
            if canon not in ordered_candidates:
                ordered_candidates.append(canon)

    in_portfolio: List[str] = []
    external: List[str] = []
    for sym in ordered_candidates:
        if sym in metadata:
            if sym not in in_portfolio:
                in_portfolio.append(sym)
        else:
            if sym not in external:
                external.append(sym)
    return in_portfolio, external


def _build_portfolio_grounding_context(
    user_comment: str,
    post_context: str = "",
    relevant_tickers: Optional[List[str]] = None,
    candidate_reply: str = "",
) -> str:
    """
    Build verified grounding metadata (ownership status, real weights, sector,
    dividend policy, thesis, and catalysts) across comment, post, and draft reply.
    """
    metadata, weights = _get_portfolio_metadata_and_weights()
    # Prioritize tickers explicitly mentioned in user_comment first, then post_context/reply
    in_comment, ext_comment = _extract_portfolio_and_external_tickers([user_comment], [])
    in_other, ext_other = _extract_portfolio_and_external_tickers(
        [post_context, candidate_reply],
        relevant_tickers or [],
    )
    in_portfolio = in_comment + [t for t in in_other if t not in in_comment]
    external = ext_comment + [t for t in ext_other if t not in ext_comment]

    lines: List[str] = []
    for t in in_portfolio[:8]:
        meta = metadata.get(t, {})
        w_val = weights.get(t)
        weight_str = f"peso: {w_val:.2f}%" if w_val is not None else "posizione attiva"
        div_str = "SÌ" if meta.get("is_dividend_paying") else "NO (ACCUMULAZIONE / ZERO CEDOLE DISTRIBUITE)"
        catalysts = meta.get("upside_catalysts") or []
        top_cat = catalysts[0] if catalysts else ""
        entry = (
            f"• ${t} ({meta.get('name', t)}) — IN PORTAFOGLIO ({weight_str})\n"
            f"  - Settore: {meta.get('sector', 'N/D')}\n"
            f"  - Dividendi: {div_str}\n"
            f"  - Tesi: {meta.get('thesis', '')}"
        )
        if top_cat:
            entry += f"\n  - Driver/Catalyst: {top_cat}"
        if t == "WDEF.L":
            entry += "\n  - NOTA CRITICA: ETF settoriale Difesa & Aerospazio (NON definirlo mai 'titolo difensivo' o 'bene rifugio')."
        lines.append(entry)

    if external:
        ext_list = ", ".join(f"${t}" for t in external[:6])
        lines.append(
            f"• Riferimenti esterni / benchmark ({ext_list}): NON IN PORTAFOGLIO "
            f"(non descriverli mai come posizioni detenute)."
        )

    ib01_w = weights.get("IB01.L")
    ppfb_w = weights.get("PPFB.DE")
    ib01_str = f"~{ib01_w:.1f}%" if ib01_w is not None else "quota dedicata"
    ppfb_str = f"~{ppfb_w:.1f}%" if ppfb_w is not None else "quota dedicata"
    baseline_note = (
        f"Riepilogo portafoglio reale ({len(weights) or 37} posizioni, 100% 1x zero leva): "
        f"riserva di liquidità in $IB01.L (Treasury USA 0-1yr, {ib01_str}) e scudo safe-haven in $PPFB.DE "
        f"(Oro fisico, {ppfb_str}), affiancati da settori difensivi (Healthcare, Consumer Staples) e pilastri AI/Tech, Energia/Nucleare e Difesa ($WDEF.L)."
    )

    if not lines:
        return (
            "Contesto generale/macro sul portafoglio (nessun singolo titolo obbligatorio; "
            "citare titoli reali del portafoglio o del post è consentito quando pertinente al commento).\n"
            + baseline_note
        )

    lines.append(baseline_note)
    return "\n".join(lines)


_FALLBACK_DCA_PATTERNS: List[Tuple[str, str]] = [
    (r'\bdca\b', "Riferimento vietato a 'DCA'"),
    (r'\bdollar[- ]cost\s+averag\w*\b', "Riferimento vietato a 'Dollar-Cost Averaging'"),
    (r'(?<![a-zA-Z0-9-])pac\b(?!-)', "Riferimento vietato a 'PAC'"),
    (r'\bpian[oi]\s+d[i\'\u2019]\s*accumul\w*\b', "Riferimento vietato a 'piano di accumulo'"),
    (r'\bingress[oi]\s+(?:periodici|frazionati|programmati|ricorrenti)\b', "Riferimento vietato a ingressi periodici/frazionati"),
    (r'\bversament[oi]\s+(?:periodici|mensili|ricorrenti|costanti)\b', "Riferimento vietato a versamenti periodici"),
    (r'\b(?:monthly|periodic|recurring)\s+(?:contribution|contributions|deposits|purchases)\b', "Riferimento vietato a versamenti periodici"),
]

_FALLBACK_WDEF_PATTERNS: List[Tuple[str, str]] = [
    (r'(?:\$?wdef(?:\.l)?|europe\s+defence)(?:(?!\.(?:\s|$))[^\n]){0,60}\b(?:titol[oi]\s+difensiv[oi]|asset\s+difensiv[oi]|copertur[ae]\s+difensiv[ae]|bene\s+rifugio|safe\s+haven)\b', "WDEF.L è Difesa & Aerospazio, NON difensivo o bene rifugio"),
    (r'\b(?:titol[oi]\s+difensiv[oi]|asset\s+difensiv[oi]|copertur[ae]\s+difensiv[ae]|bene\s+rifugio|safe\s+haven)\b(?:(?!\.(?:\s|$))[^\n]){0,60}(?:\$?wdef(?:\.l)?|europe\s+defence)', "WDEF.L è Difesa & Aerospazio, NON difensivo o bene rifugio"),
]


def _contains_forbidden_dca(text: str) -> Tuple[bool, str]:
    """Check whether text references forbidden DCA / PAC / periodic buying concepts."""
    if not text:
        return False, ""
    try:
        from post_verifier import FORBIDDEN_DCA_STRATEGY_PATTERNS as patterns
    except ImportError:
        try:
            from src.post_verifier import FORBIDDEN_DCA_STRATEGY_PATTERNS as patterns
        except ImportError:
            patterns = _FALLBACK_DCA_PATTERNS
    for pat, reason in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            return True, reason
    return False, ""


def _contains_wdef_defensive_mislabel(text: str) -> Tuple[bool, str]:
    """Check whether text mislabels WDEF.L as a defensive stock or safe haven."""
    if not text:
        return False, ""
    try:
        from post_verifier import ASSET_IDENTITY_FORBIDDEN_TERMS
        patterns = ASSET_IDENTITY_FORBIDDEN_TERMS.get("WDEF.L", _FALLBACK_WDEF_PATTERNS)[-2:]
    except ImportError:
        try:
            from src.post_verifier import ASSET_IDENTITY_FORBIDDEN_TERMS
            patterns = ASSET_IDENTITY_FORBIDDEN_TERMS.get("WDEF.L", _FALLBACK_WDEF_PATTERNS)[-2:]
        except ImportError:
            patterns = _FALLBACK_WDEF_PATTERNS
    for pat, reason in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            return True, reason
    return False, ""


def _is_simple_gratitude(text: str) -> bool:
    """Check if message is just a simple thanks, praise, or courtesy acknowledgment."""
    msg = text.lower().strip()
    if not msg or "?" in msg or "$" in msg:
        return False
    if "view on" in msg or "poco capac" in msg or "fino alle" in msg:
        return False
    topic_pattern = (
        r'\b(?:'
        r'cosa|come|quanto|perch\w*|target|prezzo|consigli\w*|chiuso|aperto|entr\w*|'
        r'tenut[ae]|rally|mes[ei]|rosso|paura|sbagl\w*|pac|dca|copi\w*|leva|'
        r'divid\w*|rimbalz\w*|croll\w*|volatil\w*|sangue|jensen|ceo|'
        r'btc|eth|crypto|cripto|bitcoin|nvda|nvidia|pltr|palantir|ccj|cameco|'
        r'lly|amzn|amazon|cosco|abbv|tsm|avgo|msft|goog|wdef|ppfb|ib01|trx|'
        r'ritracci\w*|multipl\w*'
        r')\b'
    )
    if re.search(topic_pattern, msg):
        return False
    in_p, ext_p = _extract_portfolio_and_external_tickers([text], [])
    if in_p or ext_p:
        return False
    courtesy_words = [
        "grazie", "grazie mille", "thanks", "thank you", "ok", "chiaro",
        "perfetto", "top", "good luck", "buona giornata", "complimenti",
        "ottimo", "capito", "d'accordo", "condivido", "a presto", "buon trading",
        "valore aggiunto", "ben curat", "bel lavoro", "bravo", "ottimi contenuti",
        "ottimo lavoro", "piacere leggere", "👍", "🙏", "🤝", "👌", "🌟", "👏",
    ]
    if len(msg) < 85 and any(cw in msg for cw in courtesy_words):
        return True
    return False


# ─── Andrea Ravalli Style Archive & Few-Shot Learning ──────────────────────────

DEFAULT_ANDREA_STYLE_SEEDS = [
    {
        "id": "seed_drawdown_active_it",
        "user_comment": "Secondo mese difficile sui mercati, ho paura che continui a scendere...",
        "andrea_reply": "Ciao @utente, capisco la tensione dopo due mesi complicati. È proprio in queste fasi che lavorano le nostre difese reali in portafoglio: la riserva liquida in Treasury USA ($IB01.L) e l'oro fisico ($PPFB.DE) attenuano la volatilità azionaria, permettendoci di riequilibrare i pesi in modo attivo sulle società con fondamentali più solidi anziché reagire d'impulso. Un saluto e buon proseguimento! 🛡️📊",
        "language": "it",
        "source": "seed"
    },
    {
        "id": "seed_cosco_holding_it",
        "user_comment": "Cosco Shipping ($1919.HK) garantisce una posizione diretta sui flussi del commercio globale marittimo 🚢",
        "andrea_reply": "Ottima sintesi @utente! Nel nostro portafoglio $1919.HK pesa intorno al 2,2% proprio per quel motivo: oltre all'esposizione diretta ai volumi container e ai terminal portuali globali, apprezziamo la solidissima posizione di cassa netta e la capacità di remunerare gli azionisti con dividendi generosi lungo il ciclo marittimo. Un caro saluto! 🚢📊",
        "language": "it",
        "source": "seed"
    },
    {
        "id": "seed_criticism_calm_it",
        "user_comment": "4 mesi fa tutti vedevate Nvidia come un super investimento e ora scende, sparate a caso!",
        "andrea_reply": "Ciao @utente, capisco la frustrazione sulle oscillazioni di breve, ma la valutazione di un'azienda come $NVDA non si misura su 4 mesi di prezzo: contano l'adozione Blackwell, la domanda di calcolo nei data center e i margini operativi reali. Proprio per gestire i fisiologici ritracciamenti manteniamo un peso controllato (circa 3,5%), zero leva e riserve liquide per ribilanciare solo quando i fondamentali lo giustificano. Un saluto! 📊🤝",
        "language": "it",
        "source": "seed"
    },
    {
        "id": "seed_copy_minimum_it",
        "user_comment": "Quanto capitale consigli per iniziare a copiare il portafoglio?",
        "andrea_reply": "Ciao @utente! Il minimo tecnico su eToro è 200$, ma per replicare in proporzione tutte le ~37 posizioni del portafoglio senza escludere i titoli più piccoli ti consiglio di partire da 500$-1000$, spuntando 'Copia operazioni aperte'. Benvenuto a bordo e un caro saluto! 🤝✨",
        "language": "it",
        "source": "seed"
    },
    {
        "id": "seed_cameco_energy_en",
        "user_comment": "Why are you holding Cameco and Prysmian in the portfolio?",
        "andrea_reply": "Hi @user! Cameco ($CCJ) and Prysmian ($PRY.MI) target the physical bottleneck of AI expansion: data centers need 24/7 carbon-free nuclear baseload and high-voltage grid cabling to connect new capacity. Both hold strong market share and multi-year order visibility, which is why we keep them as active core positions in our portfolio. Best regards! 📈🤝",
        "language": "en",
        "source": "seed"
    }
]


def load_andrea_style_archive() -> List[Dict[str, Any]]:
    """
    Loads authentic Andrea Ravalli replies from Gist storage, filtering out any legacy
    DCA/PAC or mislabeled WDEF entries. Falls back to clean seed dataset if empty.
    """
    archive = []
    try:
        gist_archive = gist_storage.get_andrea_style_archive()
        if gist_archive and isinstance(gist_archive, list):
            for item in gist_archive:
                if not isinstance(item, dict):
                    continue
                q_txt = str(item.get("user_comment", ""))
                a_txt = str(item.get("andrea_reply", ""))
                if _contains_forbidden_dca(q_txt)[0] or _contains_forbidden_dca(a_txt)[0]:
                    continue
                if _contains_wdef_defensive_mislabel(a_txt)[0]:
                    continue
                archive.append(item)
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
        for kw in ["copi", "copy", "leva", "leverage", "drawdown", "rosso", "ribass", "mese", "divid", "multipl", "risk", "rischio", "cameco", "pltr", "nvda", "cosco", "oro", "cash", "critica", "blackwell", "capex"]:
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

    # Strict deterministic block on DCA / PAC / periodic buying references
    has_dca, dca_reason = _contains_forbidden_dca(cleaned)
    if has_dca:
        return False, cleaned, f"Contains forbidden DCA/PAC strategy reference: {dca_reason}"

    # Strict deterministic block on mislabeling $WDEF.L as defensive / safe-haven
    has_wdef_err, wdef_reason = _contains_wdef_defensive_mislabel(cleaned)
    if has_wdef_err:
        return False, cleaned, wdef_reason

    return True, cleaned, "OK"


def verify_and_refine_reply(
    user_comment: str,
    user_author: str,
    candidate_reply: str,
    post_context: Optional[str] = None,
    lang: str = "it",
    api_key: Optional[str] = None,
    generator_model: Optional[str] = None,
    relevant_tickers: Optional[List[str]] = None,
) -> Tuple[bool, str, str]:
    """
    Pass 2: Double-Verification Judge (Independent Editorial, Specificity & Compliance Review).
    Evaluates:
      1. Zero DCA / PAC: Hard rejection for any DCA / Dollar-Cost Averaging / PAC / periodic buying reference.
      2. Point-First Specificity & Substance: Directly addresses the user's specific point using full post & portfolio grounding.
      3. Factual Accuracy & Grounding: Respects ownership status, real weights, dividends, and $WDEF.L sector classification.
      4. Authentic Tone & Completeness: No robotic PR litany, complete ending, no markdown bold.
    Returns: (is_approved, perfected_reply, reason)
    """
    if not HAS_GENAI or not api_key:
        return True, candidate_reply, "Pass 2 skipped (no API key/SDK)"

    try:
        from post_verifier import verify_post_deterministic
    except ImportError:
        try:
            from src.post_verifier import verify_post_deterministic
        except ImportError:
            verify_post_deterministic = None

    # Stage 1: Deterministic verification on candidate reply
    det_ok = True
    det_issues = []
    if verify_post_deterministic:
        det_ok, det_issues, _ = verify_post_deterministic(candidate_reply)

    meta_context = _build_portfolio_grounding_context(
        user_comment=user_comment,
        post_context=post_context or "",
        relevant_tickers=relevant_tickers or [],
        candidate_reply=candidate_reply,
    )

    criticism_note = ""
    if not det_ok:
        criticism_note = f"\n⚠️ CRITICAL WARNING FOR REVIEWER: Deterministic fast-gate flagged violations in candidate reply: {det_issues}. You MUST rectify these in 'perfected_reply' or reject."

    full_post_snippet = (post_context or "General Portfolio Post")[:1500]

    judge_prompt = f"""
You are the Senior Compliance and Editorial Director for Andrea Ravalli's official eToro Popular Investor Channel (+200% gain, active long-term multi-asset investing, Risk Score 3/10, zero leverage).

Review the following proposed reply to a community comment on eToro:

USER COMMENT (from @{user_author}):
"{user_comment}"

ORIGINAL POST CONTEXT (FULL TEXT):
"{full_post_snippet}"

PROPOSED CANDIDATE REPLY:
"{candidate_reply}"

OFFICIAL CERTIFIED PORTFOLIO GROUNDING (SINGLE SOURCE OF TRUTH):
{meta_context}
{criticism_note}

EVALUATION RUBRIC:
1. ZERO DCA / PAC (HARD REJECT, score <= 2): Reject IMMEDIATELY if the reply mentions, suggests, or implies DCA, Dollar-Cost Averaging, PAC, "piano di accumulo", "ingressi periodici/frazionati", or recurring monthly deposits. We NEVER do DCA/PAC.
2. Point-First Specificity & Substance (HARD REJECT, score <= 6): Does the first substantive sentence directly engage the exact point, company, metric, timeframe, or criticism raised by @{user_author}, grounded in the full post context? Reject generic, interchangeable PR replies that dodge the user's point!
3. Factual Accuracy & Portfolio Grounding:
   - Holdings marked IN PORTAFOGLIO must be referenced as active owned positions (never "monitoriamo" as if external). Mentioning real holdings from the post/portfolio is encouraged whenever relevant to the user's comment.
   - Assets marked NON IN PORTAFOGLIO must never be described as owned.
   - Accumulating ETFs ($WDEF.L, $INDO.PA, $IB01.L, $PPFB.DE) NEVER pay dividends.
   - $WDEF.L is a thematic European Defence & Aerospace sector ETF, NEVER a "titolo difensivo" or "bene rifugio" / safe haven. True defensive/safe-haven cushions are $PPFB.DE (physical gold), $IB01.L (short-term US Treasuries), and Healthcare/Consumer Staples.
   - Purged assets (XEON, MAU, SPCX, MELI, WCLD, RACE/Ferrari, ANT.24-7/Anthropic) are strictly forbidden.
4. Authentic Tone & Completeness: Natural human tone without repeating the canned "Risk 3/10 + 3-5 anni + rumore di breve termine" mantra unless directly relevant; dignified handling of criticism/sarcasm (no robotic gratitude); 100% complete ending; NO markdown bold asterisks (**).

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

    http_opts = build_http_options(types, timeout_seconds=45.0) if HAS_GENAI else None
    client = genai.Client(api_key=api_key, http_options=http_opts) if http_opts else genai.Client(api_key=api_key)

    # Prefer a distinct flagship/reviewer model for true dual-model verification
    base_reviewers = list(dict.fromkeys(REVIEWER_GEMINI_MODELS + FAST_GEMINI_MODELS))
    if generator_model and len(base_reviewers) > 1:
        reviewers = [m for m in base_reviewers if m != generator_model] + [generator_model]
    else:
        reviewers = base_reviewers

    for model_name in reviewers:
        try:
            print(f"   🔍 Community Reply Auditor running on model: {model_name}...")
            cfg_kwargs: Dict[str, Any] = {
                "temperature": 0.1,
                "max_output_tokens": 3072,
            }
            think_cfg = build_thinking_config(types, model_name, fast_mode=True)
            if think_cfg is not None:
                cfg_kwargs["thinking_config"] = think_cfg
            response = client.models.generate_content(
                model=model_name,
                contents=judge_prompt,
                config=types.GenerateContentConfig(**cfg_kwargs),
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
                        if verify_post_deterministic:
                            f_ok, f_issues, clean_final = verify_post_deterministic(clean_final)
                            if not f_ok:
                                print(f"⚠️ Pass 2 Perfected text failed deterministic gate: {f_issues}")
                                return False, "", f"Deterministic rule violation: {f_issues}"
                        return True, clean_final, f"Validated by {model_name} (Score: {score}/10 - {reason})"
                    else:
                        print(f"⚠️ Pass 2 Perfected text failed syntax guardrails: {err}")
                        return False, "", f"Syntax violation in perfected reply: {err}"

                print(f"⚠️ Pass 2 Validator ({model_name}) rejected reply (Score {score}/10): {reason}")
                return False, "", f"Validator rejected (Score {score}/10): {reason}"

        except Exception as e:
            print(f"⚠️ Pass 2 Validator error with {model_name}: {e}")
            err_s = str(e).lower()
            if ("429" in err_s or "quota" in err_s or "resource_exhausted" in err_s) and "limit: 0" not in err_s:
                print(f"   ⏳ Reviewer {model_name} quota/rate limit (429). Pausing 2s...")
                time.sleep(2.0)
            continue

    if not det_ok:
        return False, "", f"Deterministic rule violation on fallback: {det_issues}"
    return True, candidate_reply, "Pass 2 fallback (validator model timeout)"


def _generate_reply_with_groq_or_mistral(prompt: str) -> Tuple[Optional[str], Optional[str]]:
    """Resilient fallback reply generator via Groq LPUs or Mistral when Gemini is unavailable."""
    if not HAS_REQUESTS:
        return None, None

    try:
        from independent_fact_checker import GROQ_MODELS as _GROQ_LIST, MISTRAL_MODELS as _MISTRAL_LIST
    except ImportError:
        _GROQ_LIST = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
        _MISTRAL_LIST = ["ministral-14b-latest", "ministral-8b-latest", "codestral-latest"]

    providers = []
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_key:
        providers.append((
            "Groq",
            "https://api.groq.com/openai/v1/chat/completions",
            groq_key,
            [(m, {"reasoning_effort": "low"} if "gpt-oss" in m else {}) for m in _GROQ_LIST],
        ))
    mistral_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if mistral_key:
        providers.append((
            "Mistral",
            "https://api.mistral.ai/v1/chat/completions",
            mistral_key,
            [(m, {}) for m in _MISTRAL_LIST[:3]],
        ))

    for pname, url, key, model_specs in providers:
        for idx, (model_id, extra) in enumerate(model_specs):
            if pname == "Mistral" and idx > 0:
                time.sleep(1.1)
            try:
                payload = {
                    "model": model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 700,
                    **extra,
                }
                resp = requests.post(
                    url,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=20,
                )
                if resp.status_code == 200:
                    text = (resp.json()["choices"][0]["message"].get("content") or "").strip()
                    if text:
                        print(f"   ✅ Fallback Pass 1 generated via {pname}/{model_id}")
                        return text, f"{pname.lower()}:{model_id}"
                elif pname == "Mistral" and resp.status_code in (401, 402, 403):
                    print(f"   ℹ️ Mistral {model_id} HTTP {resp.status_code} (API non attiva/non autorizzata), skip Mistral.")
                    break
            except Exception as exc:
                print(f"   ⚠️ {pname}/{model_id} fallback reply error: {exc}")
    return None, None



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

    # 4. Gestione volatilità / paura di ritracciamenti (NO DCA/PAC, solo gestione attiva)
    elif "accumul" in msg_lower or "paura" in msg_lower or "rintracci" in msg_lower or "ritracci" in msg_lower or "drop" in msg_lower or "crash" in msg_lower or "fear" in msg_lower:
        if lang == "en":
            return (
                f"I hear you on market volatility, @{user_author}! 📊\n\n"
                "We handle pullbacks through active risk management rather than guesswork: keeping a certified Risk Score 3/10, zero leverage, physical gold ($PPFB.DE), and ultra-short Treasury cash reserves ($IB01.L) lets us rebalance selectively around company fundamentals.\n\n"
                "Wishing you all the best in life and trading! 🚀🤝"
            )
        else:
            return (
                f"Capisco bene la preoccupazione nelle fasi di volatilità, @{user_author}! 📊\n\n"
                "Affrontiamo i ritracciamenti con gestione attiva e controllo del rischio (Risk Score 3/10, zero leva): la riserva liquida in Treasury USA ($IB01.L) e l'oro fisico ($PPFB.DE) ci permettono di attenuare gli scossoni e riequilibrare i pesi in base ai fondamentali.\n\n"
                "Un caro saluto e i migliori auguri per la tua vita e per il tuo percorso di investimenti! 📈🤝"
            )

    # 5. Copy Trading / Minimum Capital / Strategy
    elif "copi" in msg_lower or "copy" in msg_lower or "minim" in msg_lower or "capitale" in msg_lower or "start" in msg_lower:
        if lang == "en":
            return (
                f"Hello @{user_author}, welcome to the community! 👋\n\n"
                "To ensure proportional replication across all ~37 portfolio positions, starting with $500–$1,000 and 'Copy Open Trades' selected is recommended (platform minimum is $200). "
                "Our focus is active long-term compounding (+200% since 2020) with Risk Score 3/10 and zero leverage.\n\n"
                "Wishing you great success in life and trading! 🚀💼"
            )
        else:
            return (
                f"Ciao @{user_author} e benvenuto/a nella community! 👋\n\n"
                "Per replicare proporzionalmente tutte le circa 37 posizioni del portafoglio, il capitale ideale per iniziare è tra 500$ e 1.000$ con spunta su 'Copia operazioni aperte' (il minimo tecnico è 200$). "
                "La nostra è una gestione attiva di lungo termine (+200% dal 2020) con Risk Score 3/10 e zero leva.\n\n"
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
) -> Optional[str]:
    """
    Two-Pass Generation Engine with Grounded Portfolio Context & Strict Guardrails:
      1. Short courtesy bypass for simple thank-yous and pure feed compliments.
      2. Pass 1: Generates a point-first, grounded draft across Gemini models using full post text & portfolio weights.
      3. Strict Deterministic Guardrails (syntax, zero DCA/PAC, $WDEF.L sector accuracy).
      4. Pass 2: Adversarial Validator Judge review.
      5. Retry loop + Groq/Mistral fallback; if all AI models fail, returns None so the comment is safely retried later.
    """
    clean_text = _extract_text(user_comment_text)
    api_key = os.environ.get("GEMINI_API_KEY")
    lang = _detect_language(clean_text)

    # Short courtesy / pure compliment check
    if _is_simple_gratitude(clean_text):
        msg_l = clean_text.lower()
        is_feed_praise = any(
            k in msg_l
            for k in ["valore aggiunto", "ben curat", "complimenti", "bel lavoro", "bravo", "ottimi contenuti", "ottimo lavoro", "piacere leggere"]
        )
        if lang == "en":
            if is_feed_praise:
                return f"Thank you for the kind words, @{user_author}! Glad you find the feed updates useful—wishing you all the best! 🤝✨"
            return f"You're very welcome, @{user_author}! Wishing you all the best in life and trading! 📈🤝"
        else:
            if is_feed_praise:
                return f"Grazie di cuore @{user_author}! Fa davvero piacere sapere che trovi utili gli aggiornamenti sul feed. Un caro saluto e buon proseguimento! 🤝✨"
            return f"Grazie a te, @{user_author}! Un caro saluto e i migliori auguri per la vita e per il tuo trading! 📈🤝"

    clean_seed_tickers = [
        _normalize_ticker_alias(t)
        for t in (relevant_tickers or [])
        if _is_valid_ticker_token(t)
    ]
    tickers_str = ", ".join(dict.fromkeys(clean_seed_tickers)) if clean_seed_tickers else "Multi-Asset Portfolio"
    full_post_text = (post_context or "").strip()
    context_snippet = full_post_text[:1500] if full_post_text else "General Portfolio Post"

    grounding_block = _build_portfolio_grounding_context(
        user_comment=clean_text,
        post_context=full_post_text,
        relevant_tickers=clean_seed_tickers,
    )
    few_shot_block = format_style_examples_for_prompt(clean_text, lang=lang, relevant_tickers=clean_seed_tickers)

    prompt = f"""
{PORTFOLIO_SYSTEM_PROMPT}

{few_shot_block}

PORTFOLIO & ASSET GROUNDING (SINGLE SOURCE OF TRUTH):
{grounding_block}

TASK:
Draft a specific, point-first reply to this eToro community user comment:
- User: @{user_author}
- Comment: "{clean_text}"
- Detected Language: {'English' if lang == 'en' else 'Italian'}
- Post Tickers: {tickers_str}
- Full Original Post Text:
\"\"\"
{context_snippet}
\"\"\"

CRITICAL RULES:
1. Directly address the SPECIFIC point, question, holding, metric, timeframe, or criticism raised in the comment, using concrete facts from the Original Post and Portfolio Grounding above.
2. NEVER mention DCA, Dollar-Cost Averaging, PAC, "piano di accumulo", or periodic/recurring buying. NEVER describe $WDEF.L as defensive or a safe haven.
3. For any asset marked IN PORTAFOGLIO, speak as an active shareholder holding it (never "monitoriamo realtà come..."). Do NOT copy-paste generic PR slogans ("Risk 3/10 + 3-5 anni + rumore") unless directly relevant.
4. Write 1 to 2 complete paragraphs (55-120 words). Start mentioning @{user_author}, conclude naturally with 1-2 emojis, and NEVER use markdown bold (**).
"""

    if HAS_GENAI and api_key:
        http_opts = build_http_options(types, timeout_seconds=45.0)
        client = genai.Client(api_key=api_key, http_options=http_opts) if http_opts else genai.Client(api_key=api_key)

        for attempt in range(2):
            for model_name in COMMENT_GEMINI_MODELS:
                try:
                    # Pass 1: Draft Generation
                    print(f"   🤖 [Pass 1/Tentativo {attempt+1}] Interrogazione {model_name}...")
                    cfg_kwargs: Dict[str, Any] = {
                        "temperature": 0.35,
                        "max_output_tokens": 3072,  # Generous token budget + ThinkingLevel.LOW prevents thinking choke
                    }
                    think_cfg = build_thinking_config(types, model_name, fast_mode=True)
                    if think_cfg is not None:
                        cfg_kwargs["thinking_config"] = think_cfg

                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(**cfg_kwargs),
                    )
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "comment_reply_draft")

                    if response and response.text:
                        raw_draft = response.text.strip()

                        # Deterministic Syntax & Anti-DCA Check
                        is_valid, cleaned_draft, syntax_err = validate_response_syntax(raw_draft, user_author)
                        if not is_valid:
                            print(f"⚠️ Pass 1 Draft rejected by syntax guardrails ({model_name}): {syntax_err}")
                            continue

                        # Pass 2: Double-Verification Judge
                        is_approved, final_reply, judge_reason = verify_and_refine_reply(
                            user_comment=clean_text,
                            user_author=user_author,
                            candidate_reply=cleaned_draft,
                            post_context=full_post_text,
                            lang=lang,
                            api_key=api_key,
                            generator_model=model_name,
                            relevant_tickers=clean_seed_tickers,
                        )

                        if is_approved:
                            print(f"✅ Pass 2 Double-Check Passed! ({judge_reason})")
                            return final_reply
                        else:
                            print(f"⚠️ Pass 2 Double-Check Failed: {judge_reason}. Retrying...")
                            prompt += (
                                f"\n\nPREVIOUS ATTEMPT WAS REJECTED: {judge_reason}. "
                                "Make sure the answer is 100% specific to the user's point, strictly avoids DCA/PAC/periodic buying, "
                                "uses real portfolio grounding, and contains no generic PR filler."
                            )

                except Exception as e:
                    print(f"⚠️ Gemini API attempt failed with {model_name}: {e}")
                    err_s = str(e).lower()
                    if ("429" in err_s or "quota" in err_s or "resource_exhausted" in err_s) and "limit: 0" not in err_s:
                        wait_t = 3.0 * (attempt + 1)
                        print(f"   ⏳ Model {model_name} quota/rate limit (429). Pausing {wait_t:.1f}s before trying next...")
                        time.sleep(wait_t)
                    continue

    # Secondary AI fallback (Groq / Mistral) if Gemini quota/API failed
    fallback_draft, _ = _generate_reply_with_groq_or_mistral(prompt)
    if fallback_draft:
        is_valid, cleaned_draft, syntax_err = validate_response_syntax(fallback_draft, user_author)
        if is_valid:
            try:
                from post_verifier import verify_post_deterministic
            except ImportError:
                try:
                    from src.post_verifier import verify_post_deterministic
                except ImportError:
                    verify_post_deterministic = None

            if verify_post_deterministic:
                det_ok, det_issues, cleaned_draft = verify_post_deterministic(cleaned_draft)
                if det_ok:
                    return cleaned_draft
                print(f"⚠️ Groq/Mistral fallback blocked by deterministic gate: {det_issues}")
            else:
                return cleaned_draft
        else:
            print(f"⚠️ Groq/Mistral fallback failed syntax guardrails: {syntax_err}")

    print("⏭️ Tutti i modelli AI non disponibili o respinti dai guardrail: commento saltato (nessun template statico pubblicato, ritenteremo al prossimo ciclo).")
    return None


def is_third_party_mention(text: str, my_username: str = "AndreaRavalli") -> bool:
    """
    Check if a comment starts by tagging another user (e.g. '@xm49fvqjtm ...')
    and is not addressed to Andrea Ravalli.
    """
    clean = _extract_text(text).strip()
    if not clean.startswith('@'):
        return False

    match = re.match(r'^@([a-zA-Z0-9_.-]+)', clean)
    if not match:
        return False

    tagged_user = match.group(1).lower()
    self_names = [my_username.lower(), "andrearavalli", "andrea ravalli", "andrea"]
    return tagged_user not in self_names


def is_ignore_or_opt_out(text: str) -> bool:
    """
    Check if a comment is purely emojis, non-verbal, or an explicit opt-out
    (e.g. 'non era rivolto a te', 'non parlavo con te', '👍', '🤔').
    """
    clean = _extract_text(text).strip()
    if not clean:
        return True

    # Strip leading @mentions
    stripped = re.sub(r'^(@[a-zA-Z0-9_.-]+\s*)+', '', clean).strip()
    if not stripped:
        return True

    # Opt-out / dismissal phrases
    opt_out_phrases = [
        "non era rivolto a te",
        "non era per te",
        "non parlavo con te",
        "non mi riferivo a te",
        "non a te",
        "sbagliato persona",
        "not for you",
        "not talking to you",
        "not meant for you",
        "stop",
    ]
    stripped_lower = stripped.lower()
    for phrase in opt_out_phrases:
        if phrase in stripped_lower:
            return True

    # Check if text contains only emojis/symbols and no letters or numbers
    has_alphanumeric = bool(re.search(r'[a-zA-Z0-9]', stripped))
    if not has_alphanumeric:
        return True

    return False


def _extract_comment_details(c: Dict[str, Any], my_username: str = "AndreaRavalli") -> Tuple[str, str, str, bool, List[Dict[str, Any]]]:
    """Helper to extract (comment_id, author_username, text, is_author_self, replies) across eToro JSON formats."""
    c_id = str(c.get("id") or c.get("commentId") or c.get("entity", {}).get("id") or "")
    owner_dict = (
        c.get("owner")
        or c.get("user")
        or c.get("author")
        or c.get("entity", {}).get("owner")
        or c.get("entity", {}).get("user")
        or c.get("entity", {}).get("author")
        or {}
    )
    if isinstance(owner_dict, str):
        owner_username = owner_dict.strip()
    elif isinstance(owner_dict, dict):
        owner_username = (
            owner_dict.get("username")
            or owner_dict.get("userName")
            or owner_dict.get("nickname")
            or owner_dict.get("nickName")
            or owner_dict.get("name")
            or owner_dict.get("displayName")
            or c.get("username")
            or c.get("userName")
            or c.get("author")
            or ""
        ).strip()
    else:
        owner_username = ""

    raw_text = (
        c.get("message")
        or c.get("content")
        or c.get("text")
        or c.get("comment")
        or c.get("entity", {}).get("content")
        or c.get("entity", {}).get("message")
        or c.get("entity", {}).get("text")
        or ""
    )
    text = _extract_text(raw_text)

    # Strictly check username and self flags to determine if it was posted by Andrea
    is_self_flag = bool(c.get("isSelf") or c.get("isMyComment") or c.get("isAuthor") or c.get("isOwner"))
    is_owner = bool(
        is_self_flag
        or (
            owner_username
            and (
                owner_username.lower() in [
                    my_username.lower(),
                    "andrearavalli",
                    "andrea ravalli",
                    "andrea",
                ]
            )
        )
    )

    replies = c.get("replies") or c.get("entity", {}).get("replies") or []
    if isinstance(replies, dict):
        replies = replies.get("items", []) or replies.get("comments", []) or []
    return c_id, owner_username or "Utente", text, is_owner, replies


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
    comments by other users needing a reply (STRICT 1-shot: max 1 reply per thread, no loops/duplicates).
    Discovers posts dynamically from live eToro feed (all posts on user profile: automated + manual),
    complemented by local post_analytics.json and Gist storage.
    """
    unreplied = []

    if not etoro_client.is_configured():
        print("⚠️ eToro API not configured.")
        return unreplied

    answered_db = load_answered_comments()

    # 1. Fetch live posts directly from user's eToro feed (includes manual and automated posts)
    posts_candidates = []
    try:
        live_feed_posts = etoro_client.get_user_feed_posts(days_back=days_back)
        if live_feed_posts:
            print(f"📡 Recuperati {len(live_feed_posts)} post direttamente dal live feed eToro di @{my_username}.")
            posts_candidates.extend(live_feed_posts)
    except Exception as e:
        print(f"⚠️ Errore nel recupero del feed eToro: {e}")

    # 2. Complement with posts from local analytics & gist
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

    # Deduplicate posts by ID, preserving richer metadata
    unique_posts = {}
    for p in posts_candidates:
        p_id = p.get("id") or p.get("post_id")
        if not p_id:
            continue
        if p_id not in unique_posts:
            unique_posts[p_id] = p
        else:
            existing = unique_posts[p_id]
            # Merge tickers if existing is empty
            if not existing.get("tickers") and p.get("tickers"):
                existing["tickers"] = p.get("tickers")
            # Preserve comments_count if present in one of them
            if "comments_count" in p and "comments_count" not in existing:
                existing["comments_count"] = p["comments_count"]
            # Preserve richer full post content when available
            if p.get("content") and len(str(p.get("content"))) > len(str(existing.get("content") or "")):
                existing["content"] = p["content"]

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

    print(f"🔍 Trovati {len(recent_posts)} post unici pubblicati negli ultimi {days_back} giorni (live feed + archivio).")

    total_comments_scanned = 0
    total_user_comments_found = 0

    for p in recent_posts:
        post_id = p.get("id") or p.get("post_id")
        if not post_id:
            continue

        # Fast path 1: if live feed confirmed 0 comments, skip API call to save rate limit
        if p.get("comments_count") == 0:
            continue

        # Fast path 2: if all comments are already embedded in live feed, use them directly
        embedded = p.get("embedded_comments", [])
        comments_cnt = p.get("comments_count")
        if embedded and comments_cnt is not None and len(embedded) >= comments_cnt:
            raw_comments = embedded
        else:
            time.sleep(0.3)  # Gentle delay to prevent eToro API HTTP 429 rate limit
            raw_comments = etoro_client.get_post_comments(post_id)

        if not raw_comments:
            continue

        total_comments_scanned += len(raw_comments)
        self_names = {my_username.lower(), "andrearavalli", "andrea ravalli", "andrea"}

        def _resolve_post_content(post_obj: Dict[str, Any], pid: str) -> str:
            content = str(post_obj.get("content") or "").strip()
            if not content and len(str(pid)) >= 20 and post_obj.get("source") != "etoro_live_feed":
                try:
                    p_metrics = etoro_client.get_post_metrics(pid, exclude_author=False, fetch_comments=False)
                    raw_post = (p_metrics or {}).get("raw", {}) if isinstance(p_metrics, dict) else {}
                    raw_inner = raw_post.get("post", raw_post) if isinstance(raw_post, dict) else {}
                    msg_obj = raw_inner.get("message", {}) if isinstance(raw_inner, dict) else {}
                    extracted = msg_obj.get("text") if isinstance(msg_obj, dict) else str(msg_obj or "")
                    if extracted and extracted.strip():
                        content = extracted.strip()
                        post_obj["content"] = content
                except Exception:
                    pass
            return content

        for c in raw_comments:
            c_id, owner, c_text, is_self, replies = _extract_comment_details(c, my_username=my_username)
            print(f"🔎 Commento {c_id[:8]} su post {post_id[:8]}: autore='{owner}' | is_self={is_self} | testo='{c_text[:35]}...' | replies={len(replies)}")

            replies_cnt = int((c.get("repliesCount") or c.get("entity", {}).get("repliesCount") or 0)) if isinstance(c, dict) else 0

            # 1. If this is Andrea's own root comment (e.g. 1/3, 2/3, 3/3 Focus), inspect external user sub-replies!
            if is_self or (owner and owner.lower() in self_names):
                if (not replies or len(replies) < replies_cnt) and replies_cnt > 0:
                    live_replies = etoro_client.get_comment_replies(post_id, c_id)
                    if live_replies:
                        replies = live_replies

                for r_idx, r in enumerate(replies):
                    r_id, r_owner, r_text, r_is_self, _ = _extract_comment_details(r, my_username=my_username)
                    if not r_id or r_is_self or (r_owner and r_owner.lower() in self_names):
                        continue
                    print(f"🔎 Sub-reply {r_id[:8]} sotto commento {c_id[:8]} su post {post_id[:8]}: autore='{r_owner}' | testo='{r_text[:35]}...'")

                    if r_id in answered_db:
                        print(f"ℹ️ Sub-reply {r_id[:8]} da @{r_owner} già evasa in memoria persistente.")
                        continue

                    # Check if Andrea already replied after this sub-reply in the same thread
                    has_reply_after = False
                    owner_tag = f"@{r_owner}".lower()
                    seen_other_ext = False
                    for later_r in replies[r_idx + 1:]:
                        _, l_owner, l_text, l_is_self, _ = _extract_comment_details(later_r, my_username=my_username)
                        if l_is_self or (l_owner and l_owner.lower() in self_names):
                            if owner_tag in l_text.lower() or not seen_other_ext:
                                has_reply_after = True
                                break
                        else:
                            seen_other_ext = True

                    if has_reply_after:
                        record_answered_comment(r_id, post_id, r_owner)
                        print(f"ℹ️ Sub-reply {r_id[:8]} da @{r_owner}: già presente una risposta di Andrea successiva. Skip.")
                        continue

                    if is_third_party_mention(r_text, my_username=my_username):
                        record_answered_comment(r_id, post_id, r_owner)
                        print(f"ℹ️ Sub-reply {r_id[:8]} da @{r_owner} rivolto a terzi. Skip.")
                        continue

                    if is_ignore_or_opt_out(r_text):
                        record_answered_comment(r_id, post_id, r_owner)
                        print(f"ℹ️ Sub-reply {r_id[:8]} da @{r_owner} è un'emoji o opt-out. Skip.")
                        continue

                    total_user_comments_found += 1
                    print(f"🎯 Trovata sub-reply da rispondere! @{r_owner} sotto commento {c_id[:8]} su post {post_id[:8]}: \"{r_text[:50]}...\"")

                    base_post_content = _resolve_post_content(p, post_id)
                    sub_post_content = (
                        f"{base_post_content}\n\n[Commento di Andrea a cui l'utente risponde]:\n{c_text}".strip()
                        if c_text else base_post_content
                    )
                    merged_tickers = list(dict.fromkeys(
                        list(p.get("tickers", []))
                        + [
                            _normalize_ticker_alias(tok)
                            for tok in re.findall(r'\$([A-Za-z0-9._-]+)', c_text or "")
                            if _is_valid_ticker_token(tok)
                        ]
                    ))
                    r_created = (
                        (r.get("created") or r.get("createdAt") or r.get("entity", {}).get("created") or "")
                        if isinstance(r, dict) else ""
                    )
                    unreplied.append({
                        "post_id": post_id,
                        "comment_id": r_id,
                        "reply_target_comment_id": c_id,
                        "author": r_owner,
                        "message": r_text,
                        "post_title": p.get("title") or p.get("session_name") or "Post Recap",
                        "post_content": sub_post_content,
                        "session_name": p.get("session") or p.get("session_name") or "",
                        "tickers": merged_tickers,
                        "published_at": p.get("published_at") or "",
                        "created_at": r_created,
                        "is_follow_up": False,
                        "turn": 1
                    })
                continue

            # 2. Strict check: already answered in persistent storage -> SKIP
            if c_id in answered_db:
                print(f"ℹ️ Commento {c_id[:8]} da @{owner} già evaso in memoria persistente.")
                continue

            # Fetch live replies if not embedded and replies exist
            if (not replies or len(replies) < replies_cnt) and replies_cnt > 0:
                live_replies = etoro_client.get_comment_replies(post_id, c_id)
                if live_replies:
                    replies = live_replies

            # 3. Check if Andrea has already replied anywhere in the thread (immediate or subsequent)
            has_my_reply = False
            for r in replies:
                _, r_owner, _, r_is_self, _ = _extract_comment_details(r, my_username=my_username)
                if r_is_self or (r_owner and r_owner.lower() in self_names):
                    has_my_reply = True
                    break

            if has_my_reply:
                # Mark in persistent storage to avoid re-fetching replies on future runs
                record_answered_comment(c_id, post_id, owner)
                print(f"ℹ️ Commento {c_id[:8]} da @{owner}: già presente una risposta di Andrea nel thread. Skip.")
                continue

            # 4. Filter third-party tag mentions (e.g. '@someone_else ...')
            if is_third_party_mention(c_text, my_username=my_username):
                record_answered_comment(c_id, post_id, owner)
                print(f"ℹ️ Commento {c_id[:8]} da @{owner} rivolto a terzi. Skip.")
                continue

            # 5. Filter pure emojis / non-verbal / opt-out comments
            if is_ignore_or_opt_out(c_text):
                record_answered_comment(c_id, post_id, owner)
                print(f"ℹ️ Commento {c_id[:8]} da @{owner} è un'emoji o opt-out. Skip.")
                continue

            total_user_comments_found += 1

            print(f"🎯 Trovato commento da rispondere! @{owner} su post {post_id[:8]}: \"{c_text[:50]}...\"")

            post_content = _resolve_post_content(p, post_id)

            unreplied.append({
                "post_id": post_id,
                "comment_id": c_id,
                "author": owner,
                "message": c_text,
                "post_title": p.get("title") or p.get("session_name") or "Post Recap",
                "post_content": post_content,
                "session_name": p.get("session") or p.get("session_name") or "",
                "tickers": p.get("tickers", []),
                "published_at": p.get("published_at") or "",
                "created_at": c.get("created") or c.get("createdAt") or "",
                "is_follow_up": False,
                "turn": 1
            })

    print(f"📊 Statistiche scansione: {total_comments_scanned} commenti totali esaminati | {total_user_comments_found} commenti idonei di utenti esterni | {len(unreplied)} in attesa di risposta.")

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

        full_post_ctx = item.get('post_content') or item['post_title']
        reply_text = generate_ai_comment_reply(
            user_comment_text=item['message'],
            user_author=item['author'],
            post_context=full_post_ctx,
            relevant_tickers=item.get('tickers', []),
            is_follow_up=item.get('is_follow_up', False)
        )

        if not reply_text:
            print(f"⏭️ Nessuna risposta AI valida generata per @{item['author']}: commento saltato, verrà riprovato al prossimo ciclo.")
            results.append({"status": "skipped_ai_unavailable", "item": item})
            continue

        print(f"\n💡 Risposta Verificata dall'IA:\n{reply_text}\n")

        if not dry_run:
            # Pre-flight Gatekeeper Check
            try:
                from post_verifier import verify_and_clean_comment
                ok_gate, reply_text, gate_audit = verify_and_clean_comment(
                    text=reply_text,
                    user_comment=item.get('message'),
                    user_author=item.get('author'),
                    run_ai_review=False
                )
                if not ok_gate:
                    print(f"🛑 COMMUNITY REPLY BLOCKED BY PRE-FLIGHT GATEKEEPER: {gate_audit.get('issues')}")
                    results.append({"status": "blocked_by_gatekeeper", "item": item, "issues": gate_audit.get('issues')})
                    continue
            except Exception as gate_err:
                print(f"⚠️ Pre-flight gatekeeper check warning: {gate_err}")

            print(f"🚀 Pubblicazione automatica in corso per @{item['author']}...")
            target_comment_id = item.get('reply_target_comment_id') or item['comment_id']
            res = etoro_client.reply_to_comment(
                post_id=item['post_id'],
                comment_id=target_comment_id,
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
