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


TAVILY_API_URL = "https://api.tavily.com/search"


def is_tavily_available() -> bool:
    """Check if Tavily API key is configured."""
    return bool(os.environ.get("TAVILY_API_KEY")) and REQUESTS_AVAILABLE


def search_tavily(
    query: str,
    search_depth: str = "basic",
    topic: str = "news",
    days: int = 2,
    max_results: int = 3,
    api_key: Optional[str] = None,
    timeout: int = 10,
) -> Optional[List[Dict[str, Any]]]:
    """
    Executes a real-time web search via Tavily Search API.
    
    Args:
        query: Search query (e.g. "Wall Street close today", "NVDA stock news")
        search_depth: "basic" or "advanced"
        topic: "news" or "general"
        days: Limit results to the last N days (default 2 for recent financial news)
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
    max_results: int = 4,
    days: int = 2,
) -> str:
    """
    Fetches real-time financial ground truth context from Tavily for injection
    into AI news prompts and fact-checker audits.
    
    Returns:
        Clean formatted string with recent verified articles and snippets.
    """
    if not is_tavily_available():
        return ""

    session_str = (session_name or "Wall Street market close").lower()
    ticker_focus = " ".join(tickers[:3]) if tickers else "S&P 500 Nasdaq"

    # Build targeted financial query
    if "open" in session_str:
        query = f"stock market opening futures news {ticker_focus}"
    elif "close" in session_str:
        query = f"Wall Street stock market close today {ticker_focus}"
    elif "weekly" in session_str:
        query = f"weekly stock market recap {ticker_focus}"
    else:
        query = f"financial market news today {ticker_focus}"

    results = search_tavily(
        query=query,
        topic="news",
        days=days,
        max_results=max_results,
    )

    if not results:
        return ""

    formatted_items = []
    for r in results:
        title = r.get("title", "News")
        content = r.get("content", "").strip().replace("\n", " ")
        pub = r.get("published_date") or "Oggi"
        url = r.get("url", "")
        source_str = f" ({url})" if url else ""
        if content:
            snippet = content[:250] + "..." if len(content) > 250 else content
            formatted_items.append(f"• [{pub}] {title}{source_str}\n  Sintesi: {snippet}")

    if not formatted_items:
        return ""

    return "\n".join(formatted_items)
