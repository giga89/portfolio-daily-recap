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

try:
    from requests_oauthlib import OAuth1
    OAUTH1_AVAILABLE = True
except ImportError:
    OAuth1 = None
    OAUTH1_AVAILABLE = False

TWEET_URL = "https://api.twitter.com/2/tweets"

ETORO_PROFILE  = "https://www.etoro.com/people/andrearavalli"
ETORO_REFERRAL = "https://med.etoro.com/B10215_A132099_TClick.aspx"


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


def build_twitter_thread(
    portfolio_daily: float,
    top_performers: list,
    session_name: str = "U.S. market close",
    plain_recap: str = "",
) -> list[str]:
    """
    Build a 2-tweet thread optimised for X/Twitter.

    Tweet 1 — Hook: result + top 3 + hashtags (≤280 chars)
    Tweet 2 — CTA: eToro profile + referral (≤280 chars)
    """
    from datetime import datetime

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

    # Top 3 performers
    if top_performers:
        lines_t1.append("📈 Top 3 movers today:")
        for sym, pct in top_performers[:3]:
            arrow = "▲" if pct >= 0 else "▼"
            lines_t1.append(f"  {arrow} ${sym} {pct:+.2f}%")
        lines_t1.append("")

    lines_t1.append("#Investing #Portfolio #ETF #Stocks #Finance")
    tweet1 = "\n".join(lines_t1)[:280]

    # ── Tweet 2: CTA ─────────────────────────────────────────────────
    tweet2 = (
        f"👤 Follow & copy my portfolio on eToro:\n"
        f"{ETORO_PROFILE}\n"
        f"\n"
        f"🎁 Join eToro with my official Partner Link:\n"
        f"{ETORO_REFERRAL}\n"
        f"\n"
        f"#eToro #CopyTrading #Investing #Finance"
    )

    return [tweet1, tweet2[:280]]


def build_twitter_copy_trading_thread() -> list[str]:
    """
    Build a 2-tweet promotional thread in English for Twitter/X with the partner link.
    """
    tweet1 = (
        "👋 I'm Andrea Ravalli, Popular Investor on eToro.\n\n"
        "📊 Transparent long-term investing strategy:\n"
        "• +200% since 2020\n"
        "• Risk Score 3/10 (low risk)\n"
        "• Zero leverage (1x real assets)\n"
        "• Global diversification (AI, Healthcare, Nuclear)\n\n"
        "$PLTR $NVDA $CCJ #eToro #CopyTrading"
    )
    tweet2 = (
        "👤 Portfolio & Live Stats:\n"
        f"{ETORO_PROFILE}\n\n"
        "🎁 Join eToro for free via my official Partner Link:\n"
        f"{ETORO_REFERRAL}\n\n"
        "#Investing #Finance #Portfolio"
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
