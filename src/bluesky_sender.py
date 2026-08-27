#!/usr/bin/env python3
"""
Bluesky Sender — Thread support via AT Protocol
Posts a 2-post thread: performance hook + CTA reply.

Post 1: Daily result + top performers + hashtags (≤300 chars)
Post 2 (reply): eToro profile + referral link

Bluesky finance tags that get visibility:
  #Investing #Stocks #ETF #Finance #Portfolio
  #eToro #CopyTrading #Mercati #Finanza

Required env vars:
  BLUESKY_HANDLE   — e.g. "andrearavalli.bsky.social"
  BLUESKY_APP_PASS — app password from bsky.app → Settings → App Passwords
"""

import os
import requests
from datetime import datetime, timezone


BSKY_API = "https://bsky.social/xrpc"

ETORO_PROFILE  = "https://www.etoro.com/people/andrearavalli"
ETORO_REFERRAL = "https://etoro.tw/46qgHLr"


def _create_session(handle: str, app_pass: str) -> tuple[str, str] | tuple[None, None]:
    """Authenticate and return (did, access_jwt)."""
    r = requests.post(
        f"{BSKY_API}/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_pass},
        timeout=15,
    )
    if r.ok:
        d = r.json()
        print(f"   ✅ Bluesky session: {handle}")
        return d["did"], d["accessJwt"]
    print(f"   ❌ Bluesky auth failed {r.status_code}: {r.text[:150]}")
    return None, None


def _detect_facets(text: str) -> list:
    """
    Detect URLs, #hashtags and @mentions → AT Protocol rich-text facets.
    Required for links and tags to be clickable/searchable on Bluesky.
    """
    import re
    facets = []

    patterns = [
        (re.compile(r"https?://[^\s]+"),
         lambda m: {"$type": "app.bsky.richtext.facet#link", "uri": m.group()}),
        (re.compile(r"#(\w+)"),
         lambda m: {"$type": "app.bsky.richtext.facet#tag", "tag": m.group(1)}),
        (re.compile(r"@([\w.]+)"),
         lambda m: {"$type": "app.bsky.richtext.facet#mention",
                    "did": f"did:placeholder:{m.group(1)}"}),
    ]

    for pattern, feature_fn in patterns:
        for m in pattern.finditer(text):
            start = len(text[:m.start()].encode("utf-8"))
            end = len(text[:m.end()].encode("utf-8"))
            facets.append({
                "index": {"byteStart": start, "byteEnd": end},
                "features": [feature_fn(m)],
            })
    return facets


def _create_record(
    did: str,
    jwt: str,
    text: str,
    reply_ref: dict = None,
    embed: dict = None,
) -> tuple[str, str] | tuple[None, None]:
    """
    Create a Bluesky post record. Returns (uri, cid) or (None, None).
    reply_ref format: {"root": {"uri":..,"cid":..}, "parent": {"uri":..,"cid":..}}
    embed format: app.bsky.embed.images or app.bsky.embed.external object
    """
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = {
        "$type": "app.bsky.feed.post",
        "text": text[:300],
        "createdAt": now,
    }
    facets = _detect_facets(text)
    if facets:
        record["facets"] = facets
    if reply_ref:
        record["reply"] = reply_ref
    if embed:
        record["embed"] = embed

    r = requests.post(
        f"{BSKY_API}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
        timeout=15,
    )
    if r.ok:
        data = r.json()
        uri = data.get("uri", "")
        cid = data.get("cid", "")
        print(f"   ✅ Bluesky post created: {uri[:60]}")
        return uri, cid
    print(f"   ❌ Bluesky post error {r.status_code}: {r.text[:250]}")
    return None, None


def _upload_image_blob(jwt: str, image_path: str) -> dict | None:
    """
    Upload an image file to Bluesky and return the blob object for embedding.

    Args:
        jwt:        Access JWT from _create_session().
        image_path: Local path to the PNG or JPEG image.

    Returns:
        Blob dict (from the API response) or None on failure.
    """
    import mimetypes
    mime, _ = mimetypes.guess_type(image_path)
    mime = mime or "image/png"

    try:
        with open(image_path, "rb") as f:
            data = f.read()
        r = requests.post(
            f"{BSKY_API}/com.atproto.repo.uploadBlob",
            headers={
                "Authorization": f"Bearer {jwt}",
                "Content-Type": mime,
            },
            data=data,
            timeout=30,
        )
        if r.ok:
            blob = r.json().get("blob")
            print(f"   ✅ Bluesky image blob uploaded ({len(data)//1024} KB)")
            return blob
        print(f"   ❌ Bluesky blob upload failed {r.status_code}: {r.text[:200]}")
        return None
    except Exception as exc:
        print(f"   ❌ Bluesky blob upload error: {exc}")
        return None




def build_bluesky_thread(
    portfolio_daily: float,
    top_performers: list,
    session_name: str = "U.S. market close",
) -> list[str]:
    """
    Build a 2-post Bluesky thread in English optimised for discoverability.

    Post 1 — Performance hook + top 3 + finance hashtags (≤300 chars)
    Post 2 — eToro CTA with profile + referral links
    """
    # Performance label
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

    date_str = datetime.now().strftime("%d %b %Y")

    # ── Post 1: hook ─────────────────────────────────────────────────
    lines = [
        f"🌆 US Market Close — {date_str}",
        "",
        f"{p_emoji} Daily Result: {portfolio_daily:+.2f}%",
        "",
    ]
    if top_performers:
        lines.append("📈 Top movers today:")
        for sym, pct in top_performers[:3]:
            arrow = "▲" if pct >= 0 else "▼"
            clean_sym = sym.replace(".", "_")
            lines.append(f"  {arrow} #{clean_sym} {pct:+.2f}%")
        lines.append("")
    lines.append("#Investing #Stocks #ETF #Finance #Portfolio #Markets")
    post1 = "\n".join(lines)[:300]

    # ── Post 2: CTA ──────────────────────────────────────────────────
    post2 = (
        "👤 Follow & copy my portfolio on eToro:\n"
        f"{ETORO_PROFILE}\n"
        "\n"
        "🎁 Join eToro with my official Partner Link:\n"
        f"{ETORO_REFERRAL}\n"
        "\n"
        "#eToro #CopyTrading #Investing #Finance"
    )

    return [post1, post2[:300]]


def build_bluesky_copy_trading_thread(
    gain_pct: str = "+200%",
) -> list[str]:
    """
    Build a dedicated 2-post Bluesky promotional thread in English explaining
    Andrea Ravalli's Popular Investor strategy and Copy Trading.
    """
    post1 = (
        "👋 Hello! I'm Andrea Ravalli, Popular Investor on eToro.\n\n"
        "📊 Transparent long-term investing strategy:\n"
        f"• {gain_pct} cumulative since 2020\n"
        "• Risk Score 3/10 (conservative)\n"
        "• Zero leverage (1x real assets)\n"
        "• Diversified: AI, Healthcare, Nuclear & ETFs\n\n"
        "#eToro #CopyTrading #Investing"
    )

    post2 = (
        "📈 You can follow or automatically copy my strategy:\n"
        f"{ETORO_PROFILE}\n\n"
        "🎁 Join eToro with my official Partner Link:\n"
        f"{ETORO_REFERRAL}\n\n"
        "#Finance #Portfolio #Stocks #Investing"
    )

    return [post1[:300], post2[:300]]


def send_bluesky_thread(posts: list[str]) -> bool:
    """
    Post a thread on Bluesky. Post 2 is a reply to post 1.

    Args:
        posts: List of post texts (2 recommended)

    Returns:
        bool: True if at least the first post succeeded
    """
    handle   = os.environ.get("BLUESKY_HANDLE")
    app_pass = os.environ.get("BLUESKY_APP_PASS")

    print("=" * 50)
    print(f"🦋 Posting Bluesky thread ({len(posts)} posts)...")

    if not handle or not app_pass:
        print("   ⚠️  BLUESKY_HANDLE or BLUESKY_APP_PASS not set — skipping.")
        return False

    did, jwt = _create_session(handle, app_pass)
    if not did:
        return False

    root_uri = root_cid = None
    prev_uri = prev_cid = None
    success = False

    for i, text in enumerate(posts):
        print(f"   📝 Post {i+1}/{len(posts)}...")
        reply_ref = None
        if root_uri and prev_uri:
            reply_ref = {
                "root":   {"uri": root_uri,  "cid": root_cid},
                "parent": {"uri": prev_uri,  "cid": prev_cid},
            }

        uri, cid = _create_record(did, jwt, text, reply_ref)
        if uri:
            if i == 0:
                root_uri, root_cid = uri, cid
                success = True
            prev_uri, prev_cid = uri, cid
        else:
            print(f"   ⚠️  Post {i+1} failed, stopping thread.")
            break

    return success


def send_bluesky_thread_with_image(
    posts: list[str],
    image_path: str,
    image_alt: str = "Portfolio engagement card",
) -> bool:
    """
    Post a Bluesky thread where the first post carries an embedded image.
    Falls back to a text-only thread if the image upload fails.

    Args:
        posts:      List of post texts (2 recommended).
        image_path: Local path to the image file to embed in post 1.
        image_alt:  Alt-text for accessibility.

    Returns:
        bool: True if at least the first post succeeded.
    """
    handle   = os.environ.get("BLUESKY_HANDLE")
    app_pass = os.environ.get("BLUESKY_APP_PASS")

    print("=" * 50)
    print(f"🦋 Posting Bluesky thread with image ({len(posts)} posts)...")

    if not handle or not app_pass:
        print("   ⚠️  BLUESKY_HANDLE or BLUESKY_APP_PASS not set — skipping.")
        return False

    did, jwt = _create_session(handle, app_pass)
    if not did:
        return False

    # Upload image blob for post 1
    embed = None
    import os as _os
    if image_path and _os.path.exists(image_path):
        blob = _upload_image_blob(jwt, image_path)
        if blob:
            embed = {
                "$type": "app.bsky.embed.images",
                "images": [
                    {
                        "image": blob,
                        "alt": image_alt,
                    }
                ],
            }
        else:
            print("   ⚠️  Image upload failed — continuing without image.")
    else:
        print(f"   ⚠️  Image not found: {image_path} — continuing without image.")

    root_uri = root_cid = None
    prev_uri = prev_cid = None
    success = False

    for i, text in enumerate(posts):
        print(f"   📝 Post {i+1}/{len(posts)}...")
        reply_ref = None
        if root_uri and prev_uri:
            reply_ref = {
                "root":   {"uri": root_uri,  "cid": root_cid},
                "parent": {"uri": prev_uri,  "cid": prev_cid},
            }

        # Embed image only in the first post
        post_embed = embed if i == 0 else None
        uri, cid = _create_record(did, jwt, text, reply_ref, embed=post_embed)
        if uri:
            if i == 0:
                root_uri, root_cid = uri, cid
                success = True
            prev_uri, prev_cid = uri, cid
        else:
            print(f"   ⚠️  Post {i+1} failed, stopping thread.")
            break

    return success


def send_bluesky_post(text: str) -> bool:
    """Simple single-post interface (legacy)."""
    handle   = os.environ.get("BLUESKY_HANDLE")
    app_pass = os.environ.get("BLUESKY_APP_PASS")
    if not handle or not app_pass:
        print("   ⚠️  Bluesky credentials not set — skipping.")
        return False
    did, jwt = _create_session(handle, app_pass)
    if not did:
        return False
    uri, _ = _create_record(did, jwt, text[:300])
    return uri is not None
