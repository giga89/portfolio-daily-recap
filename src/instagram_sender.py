#!/usr/bin/env python3
"""
Instagram Sender — Stories + Feed Posts
Posts to Instagram via Meta Graph API.

Supports:
  - STORY: beautiful generated vertical story image (1080x1920)
  - POST:  square image (1080x1080) or chart — with caption

Image must be publicly accessible. We upload via imgbb (free image hosting).

Required env vars:
  INSTAGRAM_ACCESS_TOKEN — long-lived user token
  INSTAGRAM_USER_ID      — numeric Instagram Business/Creator user ID
  IMGBB_API_KEY          — imgbb.com API key for image hosting
"""

import os
import time
import requests

GRAPH_BASE = "https://graph.instagram.com/v19.0"


def _upload_to_imgbb(image_path: str) -> str | None:
    """Upload a local image to imgbb and return the public URL."""
    api_key = os.environ.get("IMGBB_API_KEY")
    if not api_key:
        print("   ⚠️  IMGBB_API_KEY not set — cannot upload image for Instagram.")
        return None

    try:
        with open(image_path, "rb") as f:
            response = requests.post(
                "https://api.imgbb.com/1/upload",
                params={"key": api_key},
                files={"image": f},
                timeout=30,
            )
        if response.ok:
            url = response.json()["data"]["url"]
            print(f"   ✅ Image uploaded to imgbb: {url[:60]}...")
            return url
        else:
            print(f"   ❌ imgbb upload error: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"   ❌ imgbb exception: {e}")
        return None


def _create_container(
    user_id: str,
    token: str,
    image_url: str,
    caption: str,
    media_type: str = "IMAGE",
    is_carousel_item: bool = False,
) -> str | None:
    """Create an Instagram media container."""
    url = f"{GRAPH_BASE}/{user_id}/media"
    params = {
        "image_url": image_url,
        "access_token": token,
    }
    if is_carousel_item:
        params["is_carousel_item"] = "true"
        params["media_type"] = "IMAGE"
    else:
        params["media_type"] = media_type
        if caption:
            params["caption"] = caption

    r = requests.post(url, params=params, timeout=15)
    if r.ok:
        cid = r.json().get("id")
        print(f"   ✅ Container created ({media_type}): {cid}")
        return cid
    print(f"   ❌ Container error {r.status_code}: {r.text[:300]}")
    return None


def _create_carousel_container(
    user_id: str,
    token: str,
    children_ids: list,
    caption: str,
) -> str | None:
    """Create a carousel (multi-image) container."""
    url = f"{GRAPH_BASE}/{user_id}/media"
    params = {
        "media_type": "CAROUSEL",
        "children": ",".join(children_ids),
        "caption": caption,
        "access_token": token,
    }
    r = requests.post(url, params=params, timeout=15)
    if r.ok:
        cid = r.json().get("id")
        print(f"   ✅ Carousel container created: {cid}")
        return cid
    print(f"   ❌ Carousel error {r.status_code}: {r.text[:300]}")
    return None


def _create_story_container(user_id: str, token: str, image_url: str) -> str | None:
    """Create a Story media container."""
    url = f"{GRAPH_BASE}/{user_id}/media"
    params = {
        "image_url": image_url,
        "media_type": "STORIES",
        "access_token": token,
    }
    r = requests.post(url, params=params, timeout=15)
    if r.ok:
        cid = r.json().get("id")
        print(f"   ✅ Story container created: {cid}")
        return cid
    print(f"   ❌ Story container error {r.status_code}: {r.text[:300]}")
    return None


def _publish_container(user_id: str, token: str, container_id: str) -> bool:
    """Publish any type of Instagram container."""
    url = f"{GRAPH_BASE}/{user_id}/media_publish"
    params = {
        "creation_id": container_id,
        "access_token": token,
    }
    # Wait for media processing
    time.sleep(4)
    r = requests.post(url, params=params, timeout=15)
    if r.ok:
        post_id = r.json().get("id")
        print(f"   ✅ Published! Post ID: {post_id}")
        return True
    print(f"   ❌ Publish error {r.status_code}: {r.text[:300]}")
    return False


def send_instagram_story(story_image_path: str) -> bool:
    """
    Publish an Instagram Story from a local image file.

    Args:
        story_image_path: Path to the story image (1080x1920 recommended)

    Returns:
        bool: True if successful
    """
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID")

    print("   📖 Publishing Instagram Story...")

    if not token or not user_id:
        print("   ⚠️  Instagram credentials not set — skipping story.")
        return False

    if not os.path.exists(story_image_path):
        print(f"   ⚠️  Story image not found: {story_image_path}")
        return False

    public_url = _upload_to_imgbb(story_image_path)
    if not public_url:
        return False

    container_id = _create_story_container(user_id, token, public_url)
    if not container_id:
        return False

    return _publish_container(user_id, token, container_id)


def send_instagram_post(
    caption: str,
    image_path: str = None,
    image_url: str = None,
) -> bool:
    """
    Post a single image to Instagram feed.

    Args:
        caption: Post caption (max 2200 chars)
        image_path: Local image path (uploaded to imgbb)
        image_url: Public image URL (takes precedence)

    Returns:
        bool: True if successful
    """
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID")

    print("   🖼️  Publishing Instagram feed post...")

    if not token or not user_id:
        print("   ⚠️  Instagram credentials not set — skipping post.")
        return False

    public_url = image_url
    if not public_url and image_path and os.path.exists(image_path):
        public_url = _upload_to_imgbb(image_path)

    if not public_url:
        print("   ⚠️  No image available for Instagram post — skipping.")
        return False

    cap = caption[:2197] + "..." if len(caption) > 2200 else caption
    container_id = _create_container(user_id, token, public_url, cap, "IMAGE")
    if not container_id:
        return False

    return _publish_container(user_id, token, container_id)


def send_instagram_carousel(
    image_paths: list,
    caption: str,
) -> bool:
    """
    Post a carousel (multiple images) to Instagram feed.

    Args:
        image_paths: List of local image paths (max 10)
        caption: Caption for the carousel post

    Returns:
        bool: True if successful
    """
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID")

    print(f"   🎠 Publishing Instagram carousel ({len(image_paths)} slides)...")

    if not token or not user_id:
        print("   ⚠️  Instagram credentials not set — skipping carousel.")
        return False

    if not image_paths:
        print("   ⚠️  No images provided for carousel — skipping.")
        return False

    # Upload all images and create carousel item containers
    children_ids = []
    for i, img_path in enumerate(image_paths[:10]):
        if not os.path.exists(img_path):
            print(f"   ⚠️  Image not found, skipping: {img_path}")
            continue
        print(f"   📤 Uploading slide {i+1}/{len(image_paths)}...")
        public_url = _upload_to_imgbb(img_path)
        if not public_url:
            print(f"   ❌ Failed to upload slide {i+1}, skipping carousel.")
            return False
        cid = _create_container(user_id, token, public_url, "", is_carousel_item=True)
        if cid:
            children_ids.append(cid)
        else:
            print(f"   ❌ Failed to create container for slide {i+1}.")
            return False

    if len(children_ids) < 2:
        print("   ⚠️  Need at least 2 valid images for carousel — falling back to single post.")
        if children_ids:
            cap = caption[:2197] + "..." if len(caption) > 2200 else caption
            # Re-upload the first image as a normal post
            return send_instagram_post(caption=caption, image_path=image_paths[0])
        return False

    cap = caption[:2197] + "..." if len(caption) > 2200 else caption
    carousel_id = _create_carousel_container(user_id, token, children_ids, cap)
    if not carousel_id:
        return False

    return _publish_container(user_id, token, carousel_id)
