#!/usr/bin/env python3
"""
Bluesky Sender
Posts portfolio recap to Bluesky via AT Protocol (atproto).

Setup:
  1. Log in to bsky.app
  2. Settings → Privacy and Security → App Passwords → Add App Password
  3. Name it "PortfolioRecap" and save the generated password

Required env vars:
  BLUESKY_HANDLE   — your handle, e.g. "andrearavalli.bsky.social"
  BLUESKY_APP_PASS — app password generated in Bluesky settings (NOT your login password)
"""

import os
import requests
from datetime import datetime, timezone


BSKY_API = "https://bsky.social/xrpc"


def _create_session(handle: str, app_pass: str) -> tuple[str, str] | tuple[None, None]:
    """Create a Bluesky session. Returns (did, access_jwt) or (None, None)."""
    r = requests.post(
        f"{BSKY_API}/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_pass},
        timeout=15,
    )
    if r.ok:
        data = r.json()
        print(f"   ✅ Bluesky session created for {handle}")
        return data["did"], data["accessJwt"]
    print(f"   ❌ Bluesky login failed {r.status_code}: {r.text[:200]}")
    return None, None


def _detect_facets(text: str) -> list:
    """
    Detect URLs and hashtags in text and create AT Protocol facets
    (rich-text annotations for links/tags).
    """
    import re
    facets = []
    text_bytes = text.encode("utf-8")

    # URLs
    url_pattern = re.compile(r"https?://[^\s]+")
    for m in url_pattern.finditer(text):
        start = len(text[:m.start()].encode("utf-8"))
        end = len(text[:m.end()].encode("utf-8"))
        facets.append({
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group()}],
        })

    # Hashtags
    tag_pattern = re.compile(r"#(\w+)")
    for m in tag_pattern.finditer(text):
        start = len(text[:m.start()].encode("utf-8"))
        end = len(text[:m.end()].encode("utf-8"))
        facets.append({
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": m.group(1)}],
        })

    return facets


def _post_record(did: str, jwt: str, text: str) -> bool:
    """Create a post record on Bluesky."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    facets = _detect_facets(text)

    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": now,
    }
    if facets:
        record["facets"] = facets

    r = requests.post(
        f"{BSKY_API}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {jwt}"},
        json={
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": record,
        },
        timeout=15,
    )
    if r.ok:
        uri = r.json().get("uri", "")
        print(f"   ✅ Bluesky post published! URI: {uri}")
        return True
    print(f"   ❌ Bluesky post failed {r.status_code}: {r.text[:300]}")
    return False


def send_bluesky_post(text: str) -> bool:
    """
    Post to Bluesky. Handles auth, rich-text facets, and 300-char limit.

    Bluesky limit: 300 graphemes per post. For longer text we post a thread
    (first post + reply with the rest).

    Args:
        text: Post text

    Returns:
        bool: True if at least the first post succeeded
    """
    handle = os.environ.get("BLUESKY_HANDLE")
    app_pass = os.environ.get("BLUESKY_APP_PASS")

    print("=" * 50)
    print("🦋 Posting to Bluesky...")
    print(f"   Handle present: {bool(handle)}")
    print(f"   App password present: {bool(app_pass)}")

    if not handle or not app_pass:
        print("   ⚠️  BLUESKY_HANDLE or BLUESKY_APP_PASS not set — skipping.")
        return False

    did, jwt = _create_session(handle, app_pass)
    if not did:
        return False

    # Bluesky limit: 300 graphemes
    MAX = 300
    if len(text) <= MAX:
        return _post_record(did, jwt, text)

    # Split into chunks for a thread
    chunks = []
    words = text.split(" ")
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if len(candidate) > MAX - 5:  # -5 for "..." or numbering
            if current:
                chunks.append(current.strip())
            current = word
        else:
            current = candidate
    if current:
        chunks.append(current.strip())

    print(f"   📝 Text split into {len(chunks)} posts (thread)")
    success = True
    for i, chunk in enumerate(chunks[:5]):  # max 5 posts in thread
        part_text = chunk if i == 0 else f"({i+1}/{len(chunks)}) {chunk}"
        ok = _post_record(did, jwt, part_text[:MAX])
        if not ok:
            success = False
            break
    return success
