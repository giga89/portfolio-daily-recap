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
    'RACE': 'Ferrari',
    'VOW3': 'Volkswagen',
    'GLEN': 'Glencore',
    'AZN': 'AstraZeneca',
    'NOVO-B': 'Novo Nordisk',
    'WDEF': 'WisdomTree Europe Defence ETF',
    'SX7PEX': 'European Banks ETF STOXX 600',
    'IQQL': 'iShares Listed Private Equity ETF',
    'PPFB': 'Physical Gold ETC',
    'IB01': 'Treasury Bond 0-1yr ETF',
    'ETOR': 'eToro Group',
    'MELI': 'MercadoLibre',
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


def is_tavily_available() -> bool:
    """Check if Tavily API key is configured."""
    return bool(os.environ.get("TAVILY_API_KEY")) and REQUESTS_AVAILABLE


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
    Executes a real-time web search via Tavily Search API.
    
    Args:
        query: Search query (e.g. "Wall Street close today", "NVDA stock news")
        search_depth: "basic" or "advanced"
        topic: "news" or "general"
        days: Limit results to the last N days (default 3 for recent financial news)
        max_results: Max number of search results to return
        api_key: Optional API key override (defaults to TAVILY_API_KEY env var)
        timeout: Request timeout in seconds
        
    Returns:
        List of dicts with title, url, content, published_date, or empty list on error.
    """
    if not REQUESTS_AVAILABLE:
        return []

    key = api_key or os.environ.get("TAVILY_API_KEY")
    if not key:
        return []

    payload = {
        "api_key": key,
        "query": query,
        "search_depth": search_depth,
        "topic": topic,
        "days": days,
        "max_results": max_results,
    }

    try:
        t0 = time.time()
        resp = requests.post(TAVILY_API_URL, json=payload, timeout=timeout)
        elapsed = time.time() - t0

        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            print(f"   🌐 Tavily Live Search: {len(results)} risultati in {elapsed:.2f}s per query: '{query[:45]}...'")
            return results
        elif resp.status_code == 429:
            print(f"   ℹ️ Tavily Search rate-limited (429).")
            return []
        else:
            print(f"   ⚠️ Tavily Search returned HTTP {resp.status_code}: {resp.text[:100]}")
            return []
    except Exception as exc:
        print(f"   ⚠️ Tavily Search exception: {exc}")
        return []


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
    2. Targeted individual queries for up to 3 specific portfolio tickers to fetch
       genuine catalysts, quarterly earnings, orders, analyst upgrades, or operational figures.
    
    Returns:
        Clean formatted string with recent verified articles and snippets.
    """
    if not is_tavily_available():
        return ""

    session_str = (session_name or "Wall Street market close").lower()

    # 1. Determine macro query
    if "open" in session_str and "eu" in session_str:
        macro_query = "European stock market open Stoxx 600 DAX today"
    elif "open" in session_str:
        macro_query = "Wall Street stock market opening futures today S&P 500"
    elif "close" in session_str:
        macro_query = "Wall Street stock market close today S&P 500 Nasdaq"
    elif "weekly" in session_str:
        macro_query = "weekly stock market recap Wall Street S&P 500"
    else:
        macro_query = "financial stock market news today Wall Street"

    # 2. Build list of queries to run in parallel
    search_tasks = [("macro", macro_query, days, 2)]

    clean_tickers = []
    for t in (tickers or [])[:4]:
        raw_t = t.replace("$", "").strip()
        clean_t = raw_t.split(".")[0].upper()
        if clean_t not in clean_tickers:
            clean_tickers.append(clean_t)
            company_name = TICKER_NAME_MAP.get(clean_t, clean_t)
            t_query = f"{company_name} stock news earnings" if clean_t in company_name else f"{company_name} {clean_t} stock news earnings"
            search_tasks.append((clean_t, t_query, 5, 2))

    def _execute_search(task):
        tag, query, d, m = task
        res = search_tavily(query=query, topic="news", days=d, max_results=m)
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
                pub = r.get("published_date") or "Oggi"
                url = r.get("url", "")
                source_str = f" ({url})" if url else ""
                snippet = content[:250] + "..." if len(content) > 250 else content
                macro_items.append(f"• [{pub}] {title}{source_str}\n  Sintesi: {snippet}")
        else:
            company_name = TICKER_NAME_MAP.get(tag, tag)
            sub_items = [f"\n📊 NOTIZIE E DATI REALI PER ${tag} ({company_name}):"]
            for r in results:
                title = r.get("title", "News")
                content = r.get("content", "").strip().replace("\n", " ")
                pub = r.get("published_date") or "Recente"
                url = r.get("url", "")
                source_str = f" ({url})" if url else ""
                snippet = content[:280] + "..." if len(content) > 280 else content
                sub_items.append(f"• [{pub}] {title}{source_str}\n  Fatto/Dato concreto: {snippet}")
            ticker_items.append("\n".join(sub_items))

    output_sections = []
    if macro_items:
        output_sections.append("🌍 CONTESTO MACRO E APERTURA/CHIUSURA MERCATI:\n" + "\n".join(macro_items))
    if ticker_items:
        output_sections.append("🏢 CATALIZZATORI E NOTIZIE SOCIETARIE SUI NOSTRI TITOLI:\n" + "\n".join(ticker_items))

    return "\n\n".join(output_sections)
