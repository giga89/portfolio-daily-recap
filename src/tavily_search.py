"""
Tavily Search & Live Ground Truth Verification Provider
======================================================
Queries Tavily Search API for real-time, verified financial news
to ground Gemini generation and Groq/Mistral compliance fact-checking.
"""

import os
import time
from typing import Optional, List, Dict, Any

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


from concurrent.futures import ThreadPoolExecutor

TAVILY_API_URL = "https://api.tavily.com/search"

# Company name mapping for precise financial search
TICKER_NAME_MAP = {
    'TSM': 'Taiwan Semiconductor TSMC TSM',
    'CCJ': 'Cameco CCJ uranium',
    'NVDA': 'NVIDIA',
    'AMD': 'AMD Advanced Micro Devices semiconductor',
    'MSFT': 'Microsoft',
    'AMZN': 'Amazon',
    'PLTR': 'Palantir',
    'AVGO': 'Broadcom',
    'LLY': 'Eli Lilly',
    'ABBV': 'AbbVie',
    'ABT': 'Abbott Laboratories ABT',
    'NET': 'Cloudflare',
    'PYPL': 'PayPal',
    'ENEL': 'Enel',
    'ENI': 'Eni',
    'PRY': 'Prysmian',
    'VOW3': 'Volkswagen',
    'GLEN': 'Glencore',
    'AZN': 'AstraZeneca',
    'WDEF': 'WisdomTree Europe Defence ETF',
    'SX7PEX': 'European Banks ETF STOXX 600',
    'IQQL': 'iShares Listed Private Equity ETF',
    'PPFB': 'Physical Gold ETC',
    'IB01': 'Treasury Bond 0-1yr ETF',
    'ETOR': 'eToro Group',
    'MRVL': 'Marvell Technology',
    'HUM': 'Humana',
    'WMT': 'Walmart',
    '1211': 'BYD electric vehicles',
    '1919': 'COSCO Shipping Holdings',
    '2318': 'Ping An Insurance',
    'TRIG': 'Greencoat UK Wind',
    'ULVR': 'Unilever',
    'VOF': 'VinaCapital Vietnam',
    'INDO': 'Lyxor MSCI Indonesia',
}


# Auto-load local .env if present
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    try:
        with open(_env_path, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
    except Exception:
        pass

# Track exhausted keys (e.g. 432 usage limit or 401 invalid) with expiry
_EXHAUSTED_KEYS: Dict[str, float] = {}


def get_tavily_api_keys() -> List[str]:
    """
    Returns an ordered list of configured Tavily API keys (primary + secondaries/fallbacks).
    Supports:
      1. TAVILY_API_KEYS (comma-separated list)
      2. TAVILY_API_KEY (primary)
      3. TAVILY_API_KEY_SECONDARY, TAVILY_API_KEY_FALLBACK, TAVILY_API_KEY_2, etc.
    """
    keys: List[str] = []

    # 1. Comma-separated list
    raw_list = os.environ.get("TAVILY_API_KEYS", "")
    if raw_list:
        for k in raw_list.split(","):
            k_clean = k.strip()
            if k_clean and k_clean not in keys:
                keys.append(k_clean)

    # 2. Primary key
    primary = os.environ.get("TAVILY_API_KEY", "").strip()
    if primary and primary not in keys:
        keys.append(primary)

    # 3. Secondary and fallback environment variables
    fallback_env_vars = [
        "TAVILY_API_KEY_SECONDARY",
        "TAVILY_API_KEY_FALLBACK",
        "TAVILY_API_KEY_2",
        "TAVILY_API_KEY_BACKUP",
    ]
    for env_var in fallback_env_vars:
        val = os.environ.get(env_var, "").strip()
        if val and val not in keys:
            keys.append(val)

    # 4. Any other TAVILY_API_KEY_* variables
    for k, v in os.environ.items():
        if k.startswith("TAVILY_API_KEY_") and k not in fallback_env_vars:
            v_clean = v.strip()
            if v_clean and v_clean not in keys:
                keys.append(v_clean)

    return keys


def is_tavily_available() -> bool:
    """Check if at least one Tavily API key is configured."""
    return bool(get_tavily_api_keys()) and REQUESTS_AVAILABLE


def search_tavily(
    query: str,
    search_depth: str = "basic",
    topic: str = "news",
    days: int = 3,
    max_results: int = 2,
    api_key: Optional[str] = None,
    timeout: int = 8,
) -> Optional[List[Dict[str, Any]]]:
    """
    Executes a real-time web search via Tavily Search API with multi-key auto-failover.
    
    If the primary key hits quota limits (HTTP 432 / 429) or fails, it automatically
    fails over to the secondary key without interruption.
    
    Args:
        query: Search query (e.g. "Wall Street close today", "NVDA stock news")
        search_depth: "basic" or "advanced"
        topic: "news" or "general"
        days: Limit results to the last N days (default 3 for recent financial news)
        max_results: Max number of search results to return
        api_key: Optional API key override
        timeout: Request timeout in seconds
        
    Returns:
        List of dicts with title, url, content, published_date, or empty list on error.
    """
    if not REQUESTS_AVAILABLE:
        return []

    # Build candidate keys list
    if api_key:
        configured = [api_key]
        for k in get_tavily_api_keys():
            if k != api_key and k not in configured:
                configured.append(k)
    else:
        configured = get_tavily_api_keys()

    if not configured:
        return []

    now = time.time()
    # Order candidate keys: non-exhausted first, then exhausted
    active_keys = [k for k in configured if _EXHAUSTED_KEYS.get(k, 0) <= now]
    exhausted_keys = [k for k in configured if _EXHAUSTED_KEYS.get(k, 0) > now]
    ordered_keys = active_keys + exhausted_keys

    for idx, key in enumerate(ordered_keys):
        payload = {
            "api_key": key,
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "days": days,
            "max_results": max_results,
        }

        key_masked = (key[:8] + "..." + key[-4:]) if len(key) > 12 else "***"
        try:
            t0 = time.time()
            resp = requests.post(TAVILY_API_URL, json=payload, timeout=timeout)
            elapsed = time.time() - t0

            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                key_info = f" (chiave {idx + 1}/{len(ordered_keys)}: {key_masked})" if len(ordered_keys) > 1 else ""
                print(f"   🌐 Tavily Live Search{key_info}: {len(results)} risultati in {elapsed:.2f}s per query: '{query[:45]}...'")
                return results
            elif resp.status_code in (429, 432, 401, 403):
                # Quota exceeded (432/429) or auth error (401/403)
                _EXHAUSTED_KEYS[key] = now + 3600  # 1 hour cooldown
                if idx < len(ordered_keys) - 1:
                    next_masked = (ordered_keys[idx + 1][:8] + "..." + ordered_keys[idx + 1][-4:]) if len(ordered_keys[idx + 1]) > 12 else "***"
                    print(f"   ⚠️ Tavily chiave {key_masked} esaurita/limitata (HTTP {resp.status_code}). Failover automatico su chiave successiva ({next_masked})...")
                    continue
                else:
                    print(f"   ⚠️ Tavily chiave {key_masked} esaurita (HTTP {resp.status_code}) e nessun'altra chiave di riserva disponibile.")
                    return []
            else:
                print(f"   ⚠️ Tavily Search returned HTTP {resp.status_code} ({key_masked}): {resp.text[:100]}")
                if idx < len(ordered_keys) - 1:
                    continue
                return []
        except Exception as exc:
            print(f"   ⚠️ Tavily Search exception con chiave {key_masked}: {exc}")
            if idx < len(ordered_keys) - 1:
                continue
            return []

    return []


def filter_live_news_for_topic(
    live_news_context: str,
    topic_text: str,
    topic_type: str = "full_post",
) -> str:
    """
    Filters Tavily live news context according to the micro-topic type so that
    single-stock paragraphs do not get cross-contaminated by global macro headlines
    (e.g. a previous day's index drop being injected into an individual stock paragraph).
    """
    if (
        not live_news_context
        or topic_type not in ("stock_paragraph", "stock_bullet")
        or ("📊 NOTIZIE E DATI REALI PER $" not in live_news_context and "🌍 CONTESTO MACRO" not in live_news_context)
    ):
        return live_news_context

    import re
    raw_tags = re.findall(r'\$([A-Za-z0-9\-\.]+)', topic_text or "")
    target_bases = {t.split(".")[0].upper() for t in raw_tags if t}
    if not target_bases:
        # Also detect exchange-suffixed tickers when '$' was stripped (e.g. 1919.HK, PRY.MI, VOW3.DE)
        suffixed = re.findall(r'\b([0-9]{4}\.HK|[A-Z0-9]{2,8}\.[A-Z]{1,4})\b', topic_text or "")
        for s_tok in suffixed:
            target_bases.add(s_tok.split(".")[0].upper())
    if not target_bases:
        # Check plain uppercase ticker tokens or company names if $ was stripped
        for known_base, comp_desc in TICKER_NAME_MAP.items():
            first_word = comp_desc.split()[0] if comp_desc else ""
            if re.search(rf'\b{re.escape(known_base)}\b', topic_text or ""):
                target_bases.add(known_base)
            elif len(first_word) >= 4 and re.search(rf'\b{re.escape(first_word)}\b', topic_text or "", flags=re.IGNORECASE):
                target_bases.add(known_base)

    if not target_bases:
        return ""

    # Extract only matching "📊 NOTIZIE E DATI REALI PER $<TAG>" blocks
    blocks = re.split(r'(?=\n?📊 NOTIZIE E DATI REALI PER \$)', live_news_context)
    matched_blocks = []
    for blk in blocks:
        blk_strip = blk.strip()
        if not blk_strip.startswith("📊 NOTIZIE E DATI REALI PER $"):
            continue
        m = re.match(r'^📊 NOTIZIE E DATI REALI PER \$([A-Za-z0-9\-\.]+)', blk_strip)
        if m and m.group(1).split(".")[0].upper() in target_bases:
            matched_blocks.append(blk_strip)

    if not matched_blocks:
        return ""
    return "🏢 CATALIZZATORI E NOTIZIE SOCIETARIE SUL TITOLO IN ESAME:\n" + "\n\n".join(matched_blocks)


def _format_pub_date_label(pub_raw: Optional[str], today_iso: str, default_label: str = "Recente") -> str:
    """
    Formats article publication date and adds an explicit warning if the article
    is from a previous calendar day so LLMs/auditors never mistake stale price % moves for today's close.
    """
    if not pub_raw:
        return default_label
    pub_str = str(pub_raw).strip()
    # Try to parse YYYY-MM-DD or RFC-2822 / ISO date
    iso_match = None
    import re
    m = re.search(r'(\d{4}-\d{2}-\d{2})', pub_str)
    if m:
        iso_match = m.group(1)
    else:
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_str)
            iso_match = dt.strftime("%Y-%m-%d")
        except Exception:
            iso_match = None

    if iso_match and iso_match < today_iso:
        return (
            f"DATA ARTICOLO PRECEDENTE: {iso_match} — NON È OGGI ({today_iso}): "
            f"usa SOLO fatti societari strutturali, IGNORA variazioni % di prezzo/indici di quella seduta!"
        )
    if iso_match == today_iso:
        return f"OGGI {iso_match}"
    return pub_str


def get_live_market_news_context(
    session_name: Optional[str] = None,
    tickers: Optional[List[str]] = None,
    max_results: int = 2,
    days: int = 3,
) -> str:
    """
    Fetches real-time financial ground truth context from Tavily for injection
    into AI news prompts and fact-checker audits.
    
    Executes parallel queries:
    1. One macro session query (e.g. Wall Street open/close, European open)
    2. Targeted individual queries for up to 4 specific portfolio tickers to fetch
       genuine catalysts, quarterly earnings, orders, analyst upgrades, or operational figures.
    
    Returns:
        Clean formatted string with recent verified articles and snippets.
    """
    if not is_tavily_available():
        return ""

    from datetime import datetime as _dt, timezone as _tz
    try:
        from zoneinfo import ZoneInfo as _ZI
        today_iso = _dt.now(_ZI("America/New_York")).strftime("%Y-%m-%d")
    except Exception:
        today_iso = _dt.now(_tz.utc).strftime("%Y-%m-%d")

    session_str = (session_name or "Wall Street market close").lower()

    # 1. Determine macro query (use days=1 for close sessions to avoid yesterday's market crash/rally headlines)
    is_close_macro = False
    if "monthly" in session_str:
        current_month = _dt.now().strftime('%B %Y')
        macro_query = f"{current_month} stock market monthly recap Federal Reserve inflation ECB interest rates Wall Street"
        days = 30
    elif "open" in session_str and "eu" in session_str:
        macro_query = "European stock market open Stoxx 600 DAX today"
        days = 1
    elif "open" in session_str:
        macro_query = "Wall Street stock market opening futures today S&P 500"
        days = 1
    elif "close" in session_str:
        macro_query = "Wall Street stock market close today S&P 500 Nasdaq"
        days = 1
        is_close_macro = True
    elif "weekly" in session_str:
        macro_query = "weekly stock market recap Wall Street S&P 500"
        days = 5
    else:
        macro_query = "financial stock market news today Wall Street"
        days = 2

    # 2. Build list of queries to run in parallel
    search_tasks = [("macro", macro_query, days, 2)]

    ticker_days = 2 if ("monthly" not in session_str and "weekly" not in session_str) else min(days, 7)
    clean_tickers = []
    for t in (tickers or [])[:4]:
        raw_t = t.replace("$", "").strip()
        clean_t = raw_t.split(".")[0].upper()
        if clean_t not in clean_tickers:
            clean_tickers.append(clean_t)
            company_name = TICKER_NAME_MAP.get(clean_t, clean_t)
            # Prioritize live breaking news of the day (contracts, deals, ratings, catalysts) instead of hardcoding stale earnings
            t_query = f"{company_name} stock latest news today" if clean_t in company_name else f"{company_name} {clean_t} stock news today"
            search_tasks.append((clean_t, t_query, ticker_days, 2))

    def _execute_search(task):
        tag, query, d, m = task
        res = search_tavily(query=query, topic="news", days=d, max_results=m)
        if not res and tag == "macro" and d == 1:
            res = search_tavily(query=query, topic="news", days=2, max_results=m)
        return tag, res

    try:
        with ThreadPoolExecutor(max_workers=min(5, len(search_tasks))) as executor:
            task_results = list(executor.map(_execute_search, search_tasks))
    except Exception as e:
        print(f"   ⚠️ Parallel Tavily search failed: {e}")
        return ""

    macro_items = []
    ticker_items = []

    for tag, results in task_results:
        if not results:
            continue
        if tag == "macro":
            for r in results:
                title = r.get("title", "News")
                content = r.get("content", "").strip().replace("\n", " ")
                pub_raw = r.get("published_date")
                # On daily close sessions, skip macro index articles explicitly dated from previous days
                # so yesterday's Wall Street close never masquerades as today's session!
                pub_label = _format_pub_date_label(pub_raw, today_iso, default_label="Oggi")
                if is_close_macro and "DATA ARTICOLO PRECEDENTE:" in pub_label:
                    continue
                url = r.get("url", "")
                source_str = f" ({url})" if url else ""
                snippet = content[:250] + "..." if len(content) > 250 else content
                macro_items.append(f"• [{pub_label}] {title}{source_str}\n  Sintesi: {snippet}")
        else:
            company_name = TICKER_NAME_MAP.get(tag, tag)
            sub_items = [f"\n📊 NOTIZIE E DATI REALI PER ${tag} ({company_name}):"]
            for r in results:
                title = r.get("title", "News")
                content = r.get("content", "").strip().replace("\n", " ")
                pub_label = _format_pub_date_label(r.get("published_date"), today_iso, default_label="Recente")
                url = r.get("url", "")
                source_str = f" ({url})" if url else ""
                snippet = content[:280] + "..." if len(content) > 280 else content
                sub_items.append(f"• [{pub_label}] {title}{source_str}\n  Fatto/Dato concreto: {snippet}")
            ticker_items.append("\n".join(sub_items))

    output_sections = []
    if macro_items:
        output_sections.append(
            "🌍 CONTESTO MACRO E APERTURA/CHIUSURA MERCATI (solo per contesto qualitativo; per i numeri % di chiusura valgono SOLO i Ground Truth Yahoo Finance):\n"
            + "\n".join(macro_items)
        )
    if ticker_items:
        output_sections.append(
            "🏢 CATALIZZATORI E NOTIZIE SOCIETARIE SUI NOSTRI TITOLI (solo per catalizzatori qualitativi; per la variazione % odierna del titolo vale SOLO il Ground Truth Yahoo Finance):\n"
            + "\n".join(ticker_items)
        )

    return "\n\n".join(output_sections)
