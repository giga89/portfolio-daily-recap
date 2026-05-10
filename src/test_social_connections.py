#!/usr/bin/env python3
"""
Social Connections Tester
Tests credentials for all configured social platforms WITHOUT posting anything.
Sends a summary report to Telegram.

Run via GitHub Actions: workflow_dispatch (manual trigger)
"""

import os
import sys
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))


# ── Test results accumulator ─────────────────────────────────────────────────
results = {}  # platform -> (ok: bool, detail: str)


def _check(platform: str, ok: bool, detail: str):
    results[platform] = (ok, detail)
    icon = "✅" if ok else "❌"
    print(f"{icon} {platform}: {detail}")


# ── Telegram ──────────────────────────────────────────────────────────────────
def test_telegram():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        _check("Telegram", False, "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe", timeout=10
        )
        if r.ok:
            bot_name = r.json().get("result", {}).get("username", "?")
            _check("Telegram", True, f"Bot @{bot_name} — chat_id {chat_id}")
        else:
            _check("Telegram", False, f"HTTP {r.status_code}: {r.text[:100]}")
    except Exception as e:
        _check("Telegram", False, str(e)[:100])


# ── Twitter / X ───────────────────────────────────────────────────────────────
def test_twitter():
    api_key    = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    token      = os.environ.get("TWITTER_ACCESS_TOKEN")
    secret     = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, token, secret]):
        _check("Twitter/X", False, "One or more TWITTER_* secrets missing")
        return
    try:
        from requests_oauthlib import OAuth1
        auth = OAuth1(api_key, api_secret, token, secret)
        r = requests.get(
            "https://api.twitter.com/2/users/me",
            auth=auth, timeout=10
        )
        if r.ok:
            username = r.json().get("data", {}).get("username", "?")
            _check("Twitter/X", True, f"@{username}")
        else:
            _check("Twitter/X", False, f"HTTP {r.status_code}: {r.text[:150]}")
    except Exception as e:
        _check("Twitter/X", False, str(e)[:100])


# ── Bluesky ───────────────────────────────────────────────────────────────────
def test_bluesky():
    handle   = os.environ.get("BLUESKY_HANDLE")
    app_pass = os.environ.get("BLUESKY_APP_PASS")
    if not handle or not app_pass:
        _check("Bluesky", False, "BLUESKY_HANDLE or BLUESKY_APP_PASS not set")
        return
    try:
        r = requests.post(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": app_pass},
            timeout=10
        )
        if r.ok:
            did = r.json().get("did", "?")
            _check("Bluesky", True, f"handle={handle} did={did}")
        else:
            _check("Bluesky", False, f"HTTP {r.status_code}: {r.text[:150]}")
    except Exception as e:
        _check("Bluesky", False, str(e)[:100])


# ── LinkedIn ──────────────────────────────────────────────────────────────────
def test_linkedin():
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        _check("LinkedIn", False, "LINKEDIN_ACCESS_TOKEN not set")
        return
    try:
        r = requests.get(
            "https://api.linkedin.com/v2/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if r.ok:
            data = r.json()
            first = data.get("localizedFirstName", "")
            last  = data.get("localizedLastName", "")
            uid   = data.get("id", "?")
            _check("LinkedIn", True, f"{first} {last} (id={uid})")
        else:
            _check("LinkedIn", False, f"HTTP {r.status_code}: {r.text[:150]}")
    except Exception as e:
        _check("LinkedIn", False, str(e)[:100])


# ── Threads ───────────────────────────────────────────────────────────────────
def test_threads():
    token   = os.environ.get("THREADS_ACCESS_TOKEN")
    user_id = os.environ.get("THREADS_USER_ID")
    if not token or not user_id:
        _check("Threads", False, "THREADS_ACCESS_TOKEN or THREADS_USER_ID not set")
        return
    try:
        r = requests.get(
            f"https://graph.threads.net/v1.0/{user_id}",
            params={"fields": "id,username", "access_token": token},
            timeout=10
        )
        if r.ok:
            username = r.json().get("username", "?")
            _check("Threads", True, f"@{username}")
        else:
            _check("Threads", False, f"HTTP {r.status_code}: {r.text[:150]}")
    except Exception as e:
        _check("Threads", False, str(e)[:100])


# ── Facebook ──────────────────────────────────────────────────────────────────
def test_facebook():
    token   = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
    page_id = os.environ.get("FACEBOOK_PAGE_ID")
    if not token or not page_id:
        _check("Facebook", False, "FACEBOOK_PAGE_ACCESS_TOKEN or FACEBOOK_PAGE_ID not set")
        return
    try:
        r = requests.get(
            f"https://graph.facebook.com/v19.0/{page_id}",
            params={"fields": "id,name", "access_token": token},
            timeout=10
        )
        if r.ok:
            name = r.json().get("name", "?")
            _check("Facebook", True, f"Page: {name} (id={page_id})")
        else:
            _check("Facebook", False, f"HTTP {r.status_code}: {r.text[:150]}")
    except Exception as e:
        _check("Facebook", False, str(e)[:100])


# ── Instagram ─────────────────────────────────────────────────────────────────
def test_instagram():
    token   = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID")
    imgbb   = os.environ.get("IMGBB_API_KEY")
    if not token or not user_id:
        _check("Instagram", False, "INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_USER_ID not set")
        return
    try:
        r = requests.get(
            f"https://graph.instagram.com/v19.0/{user_id}",
            params={"fields": "id,username", "access_token": token},
            timeout=10
        )
        if r.ok:
            username = r.json().get("username", "?")
            imgbb_ok = "✅ imgbb key set" if imgbb else "⚠️ IMGBB_API_KEY missing"
            _check("Instagram", True, f"@{username} — {imgbb_ok}")
        else:
            _check("Instagram", False, f"HTTP {r.status_code}: {r.text[:150]}")
    except Exception as e:
        _check("Instagram", False, str(e)[:100])


# ── Telegram report ───────────────────────────────────────────────────────────
def send_telegram_report():
    token   = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️  Cannot send Telegram report: credentials missing")
        return

    now = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
    lines = [f"🔌 <b>SOCIAL CONNECTIONS TEST</b> — {now}\n"]

    all_ok = True
    for platform, (ok, detail) in results.items():
        icon = "✅" if ok else "❌"
        lines.append(f"{icon} <b>{platform}</b>: {detail}")
        if not ok:
            all_ok = False

    lines.append("")
    if all_ok:
        lines.append("🎉 <b>Tutte le connessioni funzionano!</b>")
    else:
        failed = [p for p, (ok, _) in results.items() if not ok]
        lines.append(f"⚠️ <b>Platforms da configurare:</b> {', '.join(failed)}")

    message = "\n".join(lines)

    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
        timeout=10,
    )
    if r.ok:
        print("\n✅ Report sent to Telegram!")
    else:
        print(f"\n❌ Telegram report failed: {r.text[:200]}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("🔌 Testing social platform connections...")
    print("=" * 50)

    test_telegram()
    test_twitter()
    test_bluesky()
    test_linkedin()
    test_threads()
    test_facebook()
    test_instagram()

    print("=" * 50)
    print("Sending report to Telegram...")
    send_telegram_report()

    # Exit with error code if any platform that has credentials fails
    configured_failed = [p for p, (ok, d) in results.items()
                         if not ok and "not set" not in d]
    if configured_failed:
        print(f"\n❌ Failures on configured platforms: {configured_failed}")
        sys.exit(1)
    else:
        print("\n✅ All configured platforms OK.")
        sys.exit(0)
