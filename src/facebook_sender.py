#!/usr/bin/env python3
"""
Facebook Page Sender
Posts portfolio recap to a Facebook Page via Meta Graph API.

Required env vars:
  FACEBOOK_PAGE_ACCESS_TOKEN — Page access token (manage_pages + publish_pages)
  FACEBOOK_PAGE_ID           — numeric Page ID (e.g. "1234567890")
"""

import os
import requests

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def send_facebook_post(text: str, image_path: str = None) -> bool:
    """
    Post a message (optionally with a photo) to a Facebook Page.

    Args:
        text: Post content
        image_path: Optional local path to an image file

    Returns:
        bool: True if successful
    """
    token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
    page_id = os.environ.get("FACEBOOK_PAGE_ID")

    print("=" * 50)
    print("📘 Posting to Facebook...")
    print(f"   Token present: {bool(token)}")
    print(f"   Page ID present: {bool(page_id)}")

    if not token or not page_id:
        print("   ⚠️  FACEBOOK_PAGE_ACCESS_TOKEN or FACEBOOK_PAGE_ID not set — skipping.")
        return False

    try:
        if image_path and os.path.exists(image_path):
            # Post with photo
            url = f"{GRAPH_BASE}/{page_id}/photos"
            with open(image_path, "rb") as img:
                files = {"source": img}
                data = {
                    "caption": text,
                    "access_token": token,
                }
                response = requests.post(url, data=data, files=files, timeout=30)
        else:
            # Text-only post
            url = f"{GRAPH_BASE}/{page_id}/feed"
            payload = {
                "message": text,
                "access_token": token,
            }
            response = requests.post(url, data=payload, timeout=15)

        print(f"   Response status: {response.status_code}")

        if response.ok:
            post_id = response.json().get("id")
            print(f"   ✅ Facebook post published! ID: {post_id}")
            return True
        else:
            print(f"   ❌ Facebook error: {response.text[:300]}")
            return False

    except Exception as e:
        print(f"   ❌ Facebook exception: {e}")
        return False
