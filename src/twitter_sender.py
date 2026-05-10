#!/usr/bin/env python3
"""
Twitter / X Sender
Posts portfolio recap to Twitter (X) via API v2.

Free tier: 500 tweets/month (write), BUT only ~1 free app post/month on Basic.
Set TWITTER_POST_MONTHLY=true to only post once per calendar month.

Required env vars:
  TWITTER_BEARER_TOKEN        — app-only bearer token (for read)
  TWITTER_API_KEY             — consumer key
  TWITTER_API_SECRET          — consumer secret
  TWITTER_ACCESS_TOKEN        — user access token
  TWITTER_ACCESS_TOKEN_SECRET — user access token secret

Optional:
  TWITTER_POST_MONTHLY        — "true" to limit to 1 post/month (default: true)
"""

import os
import json
import requests
from datetime import datetime
from requests_oauthlib import OAuth1

TWEET_URL = "https://api.twitter.com/2/tweets"
MONTHLY_FLAG_FILE = "/tmp/twitter_last_post_month.txt"


def _get_oauth() -> OAuth1:
    return OAuth1(
        os.environ["TWITTER_API_KEY"],
        os.environ["TWITTER_API_SECRET"],
        os.environ["TWITTER_ACCESS_TOKEN"],
        os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )


def _already_posted_this_month() -> bool:
    """Check if we already posted to Twitter this calendar month."""
    try:
        with open(MONTHLY_FLAG_FILE, "r") as f:
            last_month = f.read().strip()
        current_month = datetime.utcnow().strftime("%Y-%m")
        return last_month == current_month
    except FileNotFoundError:
        return False


def _mark_posted_this_month() -> None:
    current_month = datetime.utcnow().strftime("%Y-%m")
    with open(MONTHLY_FLAG_FILE, "w") as f:
        f.write(current_month)


def send_twitter_post(text: str) -> bool:
    """
    Send a tweet to Twitter/X.

    Args:
        text: Tweet text (max 280 chars)

    Returns:
        bool: True if posted, False otherwise
    """
    required_keys = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET",
    ]

    print("=" * 50)
    print("🐦 Posting to Twitter/X...")

    missing = [k for k in required_keys if not os.environ.get(k)]
    if missing:
        print(f"   ⚠️  Missing Twitter credentials: {', '.join(missing)} — skipping.")
        return False

    # Truncate to 280 chars
    tweet_text = text[:277] + "..." if len(text) > 280 else text

    auth = _get_oauth()
    payload = {"text": tweet_text}

    try:
        response = requests.post(
            TWEET_URL,
            auth=auth,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        print(f"   Response status: {response.status_code}")
        if response.ok:
            tweet_id = response.json().get("data", {}).get("id")
            print(f"   ✅ Tweet posted! ID: {tweet_id}")
            return True
        else:
            print(f"   ❌ Twitter error: {response.text[:300]}")
            return False
    except Exception as e:
        print(f"   ❌ Twitter exception: {e}")
        return False

