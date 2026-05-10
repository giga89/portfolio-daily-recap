#!/usr/bin/env python3
"""
Threads Sender
Posts portfolio recap to Threads via Meta Graph API.

Required env vars:
  THREADS_ACCESS_TOKEN  — long-lived user token with threads_basic + threads_content_publish
  THREADS_USER_ID       — numeric Threads user ID (e.g. "1234567890")
"""

import os
import requests

GRAPH_BASE = "https://graph.threads.net/v1.0"


def _create_text_container(user_id: str, token: str, text: str) -> str | None:
    """Create a Threads media container for a text-only post. Returns container ID."""
    url = f"{GRAPH_BASE}/{user_id}/threads"
    params = {
        "media_type": "TEXT",
        "text": text,
        "access_token": token,
    }
    r = requests.post(url, params=params, timeout=15)
    if r.ok:
        cid = r.json().get("id")
        print(f"   ✅ Threads container created: {cid}")
        return cid
    print(f"   ❌ Threads container error {r.status_code}: {r.text[:300]}")
    return None


def _create_image_container(user_id: str, token: str, image_url: str, text: str) -> str | None:
    """Create a Threads media container for an IMAGE post (image must be a public URL)."""
    url = f"{GRAPH_BASE}/{user_id}/threads"
    params = {
        "media_type": "IMAGE",
        "image_url": image_url,
        "text": text,
        "access_token": token,
    }
    r = requests.post(url, params=params, timeout=15)
    if r.ok:
        cid = r.json().get("id")
        print(f"   ✅ Threads image container created: {cid}")
        return cid
    print(f"   ❌ Threads image container error {r.status_code}: {r.text[:300]}")
    return None


def _publish_container(user_id: str, token: str, container_id: str) -> bool:
    """Publish a Threads container."""
    url = f"{GRAPH_BASE}/{user_id}/threads_publish"
    params = {
        "creation_id": container_id,
        "access_token": token,
    }
    r = requests.post(url, params=params, timeout=15)
    if r.ok:
        post_id = r.json().get("id")
        print(f"   ✅ Threads post published! ID: {post_id}")
        return True
    print(f"   ❌ Threads publish error {r.status_code}: {r.text[:300]}")
    return False


def send_threads_post(text: str, image_url: str = None) -> bool:
    """
    Send a post to Threads.

    Args:
        text: Post text (max 500 chars)
        image_url: Optional public URL of an image to attach

    Returns:
        bool: True if successful
    """
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    user_id = os.environ.get("THREADS_USER_ID")

    print("=" * 50)
    print("📱 Posting to Threads...")
    print(f"   Token present: {bool(token)}")
    print(f"   User ID present: {bool(user_id)}")

    if not token or not user_id:
        print("   ⚠️  THREADS_ACCESS_TOKEN or THREADS_USER_ID not set — skipping.")
        return False

    # Threads limit: 500 chars
    post_text = text[:497] + "..." if len(text) > 500 else text

    if image_url:
        container_id = _create_image_container(user_id, token, image_url, post_text)
    else:
        container_id = _create_text_container(user_id, token, post_text)

    if not container_id:
        return False

    return _publish_container(user_id, token, container_id)
