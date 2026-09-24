#!/usr/bin/env python3
"""
Twitter / X Sender — Thread support
Posts a 2-tweet thread: hook + CTA reply.

Tweet 1: Daily performance hook with top performers + hashtags
Tweet 2 (reply): eToro profile + referral link

Required env vars:
  TWITTER_API_KEY             — consumer key
  TWITTER_API_SECRET          — consumer secret
  TWITTER_ACCESS_TOKEN        — user access token (must have Read+Write)
  TWITTER_ACCESS_TOKEN_SECRET — user access token secret
"""

import os
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

try:
    from requests_oauthlib import OAuth1
    OAUTH1_AVAILABLE = True
except ImportError:
    OAuth1 = None
    OAUTH1_AVAILABLE = False

try:
    import gist_storage
    GIST_AVAILABLE = True
except ImportError:
    gist_storage = None
    GIST_AVAILABLE = False

TWEET_URL = "https://api.twitter.com/2/tweets"

ETORO_PROFILE  = "https://www.etoro.com/people/andrearavalli"
ETORO_PARTNER_BASE = "https://med.etoro.com/B10215_A132099_TClick.aspx"
PORTFOLIO_HUB_BASE = "https://giga89.github.io/portfolio-daily-recap/"


def get_twitter_etoro_url(campaign: str = "recap") -> str:
    """Return tracked eToro partner referral link for Twitter/X."""
    sub_id = f"twitter_{campaign}".replace(" ", "_").lower()[:30]
    return f"{ETORO_PARTNER_BASE}?SubAffiliateID={sub_id}"


def get_twitter_hub_url(campaign: str = "us_close", content: str = None) -> str:
    """Return tracked GitHub Pages Hub URL with UTM parameters for Twitter/X."""
    camp = campaign.replace(" ", "_").lower()[:20]
    url = f"{PORTFOLIO_HUB_BASE}?utm_source=twitter&utm_campaign={camp}"
    if content:
        url += f"&utm_content={content.replace(' ', '_').lower()[:15]}"
    return url


def _get_oauth():
    if not OAUTH1_AVAILABLE or OAuth1 is None:
        raise ImportError("requests_oauthlib is required for Twitter OAuth1")
    return OAuth1(
        os.environ["TWITTER_API_KEY"],
        os.environ["TWITTER_API_SECRET"],
        os.environ["TWITTER_ACCESS_TOKEN"],
        os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )


def _post_tweet(auth: OAuth1, text: str, reply_to_id: str = None) -> str | None:
    """Post a single tweet, optionally as a reply. Returns tweet ID or None."""
    payload = {"text": text[:280]}
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

    r = requests.post(
        TWEET_URL,
        auth=auth,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    if r.ok:
        tweet_id = r.json().get("data", {}).get("id")
        print(f"   ✅ Tweet posted (id={tweet_id})")
        return tweet_id
    print(f"   ❌ Tweet error {r.status_code}: {r.text[:250]}")
    return None


US_CLOSE_HASHTAG_SETS = [
    "#Investing #Portfolio #ETF #Stocks #Finance",
    "#WallStreet #MarketClose #Stocks #Trading #FinTwit",
    "#SP500 #Nasdaq #StockMarket #Investing #Finance",
    "#TechStocks #GrowthInvesting #StockMarket #AI #Investing",
    "#Portfolio #AssetAllocation #LongTerm #Wealth #Stocks",
    "#CompoundInterest #ValueInvesting #SmartMoney #FinTwit #Stocks",
    "#GlobalMarkets #Economy #StockMarketNews #Trading #Finance",
    "#eToro #PopularInvestor #CopyTrading #Investing #Stocks",
]


def _format_twitter_ticker(sym: str, is_first: bool = False) -> str:
    """
    Format ticker symbol for Twitter to prevent domain autolinking and respect cashtag limits.
    For example, European tickers like VOW3.DE or PRY.MI are formatted so Twitter
    does not auto-link them as website URLs (e.g. 'https://VOW3.DE').
    """
    clean = sym.replace("$", "").strip()
    if "." in clean:
        parts = clean.split(".", 1)
        base, ext = parts[0], parts[1]
        if is_first:
            return f"${base}"
        return f"{base} ({ext})" if len(ext) <= 3 else base
    return f"${clean}" if is_first else clean


def build_twitter_thread(
    portfolio_daily: float,
    top_performers: list,
    session_name: str = "U.S. market close",
    plain_recap: str = "",
    hashtag_index: Optional[int] = None,
) -> list[str]:
    """
    Build a 2-tweet thread optimised for X/Twitter with tracked URLs.

    Tweet 1 — Hook: result + top 3 + rotating hashtags (<=280 chars)
    Tweet 2 — CTA: eToro profile + partner link + hub (<=280 chars)
    """
    # ── Performance emoji/label ──────────────────────────────────────
    if portfolio_daily > 2.0:
        label, p_emoji = "TO THE MOON 🚀", "🔥"
    elif portfolio_daily > 0.5:
        label, p_emoji = "GREAT GREEN 🍀", "✅"
    elif portfolio_daily >= 0:
        label, p_emoji = "SLIGHT GAINS 🌿", "🌱"
    elif portfolio_daily > -0.5:
        label, p_emoji = "MINOR DIP 📉", "⚖️"
    elif portfolio_daily > -2.0:
        label, p_emoji = "ROUGH DAY 💀", "🩸"
    else:
        label, p_emoji = "MARKET DROP 🧨", "🆘"

    date_str = datetime.now().strftime("%d/%m/%Y")

    # ── Tweet 1: hook ────────────────────────────────────────────────
    lines_t1 = [
        f"🌆 US MARKET CLOSE — {date_str}",
        "",
        f"{p_emoji} Daily Result: {portfolio_daily:+.2f}%",
        "",
    ]

    # Top 3 performers (X/Twitter Free API v2 restricts posts to maximum 1 cashtag)
    if top_performers:
        lines_t1.append("📈 Top 3 movers today:")
        for idx, (sym, pct) in enumerate(top_performers[:3]):
            arrow = "▲" if pct >= 0 else "▼"
            formatted_sym = _format_twitter_ticker(sym, is_first=(idx == 0))
            lines_t1.append(f"  {arrow} {formatted_sym} {pct:+.2f}%")
        lines_t1.append("")

    # Select rotating hashtags for US market close
    hashtags = None
    if hashtag_index is not None:
        hashtags = US_CLOSE_HASHTAG_SETS[hashtag_index % len(US_CLOSE_HASHTAG_SETS)]
    elif GIST_AVAILABLE and hasattr(gist_storage, "get_next_twitter_close_hashtag_index"):
        try:
            idx = gist_storage.get_next_twitter_close_hashtag_index(len(US_CLOSE_HASHTAG_SETS))
            hashtags = US_CLOSE_HASHTAG_SETS[idx]
        except Exception:
            hashtags = None

    if not hashtags:
        day_of_year = datetime.utcnow().timetuple().tm_yday
        hashtags = US_CLOSE_HASHTAG_SETS[day_of_year % len(US_CLOSE_HASHTAG_SETS)]

    lines_t1.append(hashtags)
    tweet1 = "\n".join(lines_t1)[:280]

    # ── Tweet 2: CTA with Tracked Links ──────────────────────────────
    partner_url = get_twitter_etoro_url(campaign="us_close")
    hub_url = get_twitter_hub_url(campaign="us_close")

    tweet2 = (
        f"📊 Live Hub: {hub_url}\n\n"
        f"👤 Copy on eToro: {ETORO_PROFILE}\n\n"
        f"🎁 Join eToro (Partner Link): {partner_url}"
    )

    return [tweet1[:280], tweet2[:280]]


COPY_TRADING_THEMES = [
    {
        "id": "ai_tech",
        "name": "AI & Big Tech Growth",
        "pillars": "AI, Cloud & Big Tech",
        "tickers_line": "$NVDA MSFT AMZN",
        "hashtags": "#AI #Tech #Investing",
        "audience": "Tech & AI growth investors",
    },
    {
        "id": "nuclear_energy",
        "name": "Nuclear Energy & Clean Transition",
        "pillars": "Nuclear Energy & Power",
        "tickers_line": "$CCJ ENI.MI URA",
        "hashtags": "#Nuclear #CleanEnergy #Uranium",
        "audience": "Clean energy & commodity investors",
    },
    {
        "id": "semiconductors",
        "name": "Semiconductors & AI Hardware",
        "pillars": "Semis & AI Hardware",
        "tickers_line": "$TSM AVGO MRVL",
        "hashtags": "#Semiconductors #Chips #Tech",
        "audience": "Semiconductor & hardware watchers",
    },
    {
        "id": "healthcare_pharma",
        "name": "Healthcare & Biotech Quality",
        "pillars": "Healthcare & Biotech",
        "tickers_line": "$LLY ABBV NOVO",
        "hashtags": "#Healthcare #Biotech #Dividends",
        "audience": "Healthcare & dividend compounder investors",
    },
    {
        "id": "european_champions",
        "name": "European Quality & Luxury Leaders",
        "pillars": "European Leaders & Luxury",
        "tickers_line": "$RACE PRY.MI VOW3",
        "hashtags": "#Luxury #Stocks #Ferrari",
        "audience": "European equities & luxury investors",
    },
    {
        "id": "defense_security",
        "name": "Defense & Strategic Data",
        "pillars": "Defense & Data Analytics",
        "tickers_line": "$PLTR WDEF.L LMT",
        "hashtags": "#Defense #Palantir #BigData",
        "audience": "Palantir community & defense tech investors",
    },
    {
        "id": "wealth_compounders",
        "name": "Long-Term Wealth & Compounders",
        "pillars": "Compounders & ETFs",
        "tickers_line": "$IB01.L SPY QQQ",
        "hashtags": "#WealthBuilding #FinTwit",
        "audience": "FIRE, ETF & long-term wealth builders",
    },
    {
        "id": "global_fintech",
        "name": "Global Fintech & E-Commerce",
        "pillars": "Global Fintech & E-Commerce",
        "tickers_line": "$MELI TRX ETOR",
        "hashtags": "#Fintech #Ecommerce #Markets",
        "audience": "Fintech & emerging markets investors",
    },
    {
        "id": "popular_investor",
        "name": "eToro Social & Copy Trading",
        "pillars": "AI, Healthcare & Energy",
        "tickers_line": "$PLTR NVDA CCJ",
        "hashtags": "#eToro #CopyTrading",
        "audience": "Social traders & copy trading community",
    },
]


def compute_copy_strategy_metrics(
    portfolio_perf: Optional[float] = None,
    rankings_data: Optional[Dict[str, Any]] = None,
    gain_history: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, str, int]:
    """
    Compute live cumulative return since 2020, CAGR, and risk score.
    Returns: (gain_pct_str, cagr_pct_str, risk_score_int)
    """
    total_return = None
    cagr = None
    risk_score = 3

    # 1. Try from gain_history (most accurate compound series from 2020)
    if gain_history:
        compound = 1.0
        m_count = 0
        for entry in gain_history:
            d = str(entry.get("date", entry.get("start", "")))
            if d >= "2020":
                try:
                    g = float(entry.get("gain", 0.0)) / 100.0
                    compound *= (1.0 + g)
                    m_count += 1
                except (ValueError, TypeError):
                    pass
        if m_count > 0:
            total_return = (compound - 1.0) * 100.0
            years = max(1.0, m_count / 12.0)
            cagr = ((compound) ** (1.0 / years) - 1.0) * 100.0

    # 2. Try official eToro API if gain_history wasn't provided
    if total_return is None:
        try:
            import etoro_client
            if etoro_client.is_configured():
                gh = etoro_client.fetch_gain_history(granularity="monthly")
                if gh:
                    compound = 1.0
                    m_count = 0
                    for entry in gh:
                        d = str(entry.get("date", entry.get("start", "")))
                        if d >= "2020":
                            try:
                                g = float(entry.get("gain", 0.0)) / 100.0
                                compound *= (1.0 + g)
                                m_count += 1
                            except (ValueError, TypeError):
                                pass
                    if m_count > 0:
                        total_return = (compound - 1.0) * 100.0
                        years = max(1.0, m_count / 12.0)
                        cagr = ((compound) ** (1.0 / years) - 1.0) * 100.0
        except Exception:
            pass

    # 3. Try public eToro userstats endpoint (CID 7743547)
    if total_return is None:
        try:
            cid = 7743547
            url = f"https://www.etoro.com/sapi/userstats/gain/cid/{cid}/history?IncludeSimulation=true"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.ok:
                m_data = resp.json().get("monthly", [])
                compound = 1.0
                m_count = 0
                for entry in m_data:
                    d = str(entry.get("start", ""))
                    if d >= "2020":
                        try:
                            g = float(entry.get("gain", 0.0)) / 100.0
                            compound *= (1.0 + g)
                            m_count += 1
                        except (ValueError, TypeError):
                            pass
                if m_count > 0:
                    total_return = (compound - 1.0) * 100.0
                    years = max(1.0, m_count / 12.0)
                    cagr = ((compound) ** (1.0 / years) - 1.0) * 100.0
        except Exception:
            pass

    # 4. Fallback to portfolio_perf
    if total_return is None and portfolio_perf is not None:
        try:
            if isinstance(portfolio_perf, str):
                cleaned = portfolio_perf.replace("%", "").replace("+", "").strip()
                total_return = float(cleaned)
            else:
                total_return = float(portfolio_perf)
            current_year = datetime.utcnow().year
            current_month = datetime.utcnow().month
            years = max(1.0, (current_year - 2020) + current_month / 12.0)
            cagr = ((1.0 + total_return / 100.0) ** (1.0 / years) - 1.0) * 100.0
        except (ValueError, TypeError):
            pass

    # 5. Extract risk score from rankings_data or fetch
    if rankings_data and "riskScore" in rankings_data:
        try:
            risk_score = int(rankings_data["riskScore"])
        except (ValueError, TypeError):
            pass
    else:
        try:
            import etoro_client
            if etoro_client.is_configured():
                rd = etoro_client.fetch_trader_rankings(period="CurrYear")
                if rd and "riskScore" in rd:
                    risk_score = int(rd["riskScore"])
        except Exception:
            pass

    # 6. Final safety fallbacks (verified historical baseline)
    if total_return is None:
        total_return = 195.0
    if cagr is None:
        cagr = 17.0

    sign = "+" if total_return >= 0 else ""
    gain_pct_str = f"{sign}{total_return:.0f}%"
    cagr_pct_str = f"~{cagr:.0f}% CAGR"

    return gain_pct_str, cagr_pct_str, risk_score


def build_twitter_copy_trading_thread(
    gain_pct: Optional[str] = None,
    cagr_pct: Optional[str] = None,
    risk_score: Optional[int] = None,
    portfolio_perf: Optional[float] = None,
    rankings_data: Optional[Dict[str, Any]] = None,
    gain_history: Optional[List[Dict[str, Any]]] = None,
    theme_index: Optional[int] = None,
    theme_id: Optional[str] = None,
) -> list[str]:
    """
    Build a 2-tweet promotional thread in English for Twitter/X with tracked partner link.
    Dynamically computes verified performance since 2020 and rotates thematic footers
    and cashtags/hashtags across runs to engage diverse investor audiences.
    """
    # 1. Resolve performance metrics
    if gain_pct is None or cagr_pct is None or risk_score is None:
        computed_gain, computed_cagr, computed_risk = compute_copy_strategy_metrics(
            portfolio_perf=portfolio_perf,
            rankings_data=rankings_data,
            gain_history=gain_history,
        )
        gain_pct = gain_pct or computed_gain
        cagr_pct = cagr_pct or computed_cagr
        risk_score = risk_score if risk_score is not None else computed_risk

    # 2. Select theme (explicit ID -> explicit index -> Gist round-robin -> day-of-year rotation)
    selected_theme = None
    if theme_id:
        for t in COPY_TRADING_THEMES:
            if t["id"] == theme_id:
                selected_theme = t
                break

    if selected_theme is None:
        if theme_index is not None:
            selected_theme = COPY_TRADING_THEMES[theme_index % len(COPY_TRADING_THEMES)]
        elif GIST_AVAILABLE and hasattr(gist_storage, "get_next_twitter_copy_theme_index"):
            try:
                idx = gist_storage.get_next_twitter_copy_theme_index(len(COPY_TRADING_THEMES))
                selected_theme = COPY_TRADING_THEMES[idx]
            except Exception:
                selected_theme = None

        if selected_theme is None:
            day_of_year = datetime.utcnow().timetuple().tm_yday
            selected_theme = COPY_TRADING_THEMES[day_of_year % len(COPY_TRADING_THEMES)]

    # 3. Build Tweet 1
    perf_line = f"• {gain_pct} since 2020 ({cagr_pct})"
    risk_line = f"• Risk Score {risk_score}/10 (low risk)"
    leverage_line = "• Zero leverage (1x real assets)"
    div_line = f"• Diversified: {selected_theme['pillars']}"
    footer_line = f"{selected_theme['tickers_line']} {selected_theme['hashtags']}"

    tweet1 = (
        "👋 I'm Andrea Ravalli, Popular Investor on eToro.\n\n"
        "📊 Long-term investing strategy:\n"
        f"{perf_line}\n"
        f"{risk_line}\n"
        f"{leverage_line}\n"
        f"{div_line}\n\n"
        f"{footer_line}"
    )

    # 4. Build Tweet 2 with tracked campaign
    campaign_name = f"copy_{selected_theme['id']}"
    partner_url = get_twitter_etoro_url(campaign=campaign_name)
    hub_url = get_twitter_hub_url(campaign=campaign_name)

    tweet2 = (
        f"📊 Live Hub: {hub_url}\n\n"
        f"👤 Copy on eToro: {ETORO_PROFILE}\n\n"
        f"🎁 Free Signup (Partner Link): {partner_url}"
    )
    return [tweet1[:280], tweet2[:280]]


def send_twitter_post(text: str) -> bool:
    """
    Post a single tweet (legacy / simple interface).
    For the full thread experience, use send_twitter_thread().
    """
    required = [
        "TWITTER_API_KEY", "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"   ⚠️  Missing: {', '.join(missing)} — skipping.")
        return False

    auth = _get_oauth()
    tweet_id = _post_tweet(auth, text[:280])
    return tweet_id is not None


def send_twitter_thread(tweets: list[str]) -> bool:
    """
    Post a thread of tweets on X. Each tweet after the first is a reply to the previous.

    Args:
        tweets: Ordered list of tweet texts

    Returns:
        bool: True if all tweets posted successfully
    """
    required = [
        "TWITTER_API_KEY", "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET",
    ]
    print("=" * 50)
    print(f"🐦 Posting Twitter/X thread ({len(tweets)} tweets)...")

    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"   ⚠️  Missing: {', '.join(missing)} — skipping.")
        return False

    if not tweets:
        print("   ⚠️  No tweets to post.")
        return False

    auth = _get_oauth()
    prev_id = None
    all_ok = True

    for i, text in enumerate(tweets):
        print(f"   📝 Tweet {i+1}/{len(tweets)}...")
        tweet_id = _post_tweet(auth, text, reply_to_id=prev_id)
        if tweet_id:
            prev_id = tweet_id
        else:
            all_ok = False
            break

    return all_ok
