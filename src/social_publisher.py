#!/usr/bin/env python3
"""
Social Publisher — Orchestrator
Sends the portfolio recap to all configured social platforms.

Session routing rules:
  - Telegram  → every session (unchanged)
  - Threads   → only "U.S. market close"
  - Facebook  → only "U.S. market close"
  - Instagram → only "U.S. market close" (Story + carousel post)
  - Twitter/X → only "Monthly recap"

eToro links are appended to every social post.
"""

import os

import telegram_sender
import threads_sender
import twitter_sender
import facebook_sender
import instagram_sender
import story_generator


# ── eToro constants ──────────────────────────────────────────────────────────
ETORO_PROFILE  = "https://www.etoro.com/people/andrearavalli"
ETORO_REFERRAL = "https://etoro.tw/46qgHLr"

ETORO_FOOTER_LONG = (
    "\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    f"👤 Segui il mio portfolio su eToro:\n{ETORO_PROFILE}\n\n"
    f"🎁 Non sei ancora su eToro? Iscriviti gratis:\n{ETORO_REFERRAL}"
)

ETORO_FOOTER_SHORT = (
    f"\n\n👤 {ETORO_PROFILE}\n"
    f"🎁 Iscriviti: {ETORO_REFERRAL}"
)

# Session constants
SESSION_US_CLOSE = "U.S. market close"
SESSION_MONTHLY  = "Monthly recap"


def _strip_html(text: str) -> str:
    """Remove HTML tags used by Telegram (other platforms expect plain text)."""
    import re
    text = re.sub(r"<b>(.*?)</b>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<i>(.*?)</i>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _make_twitter_teaser(plain_text: str, max_len: int = 270) -> str:
    """Build a short teaser for Twitter (270 chars + referral link)."""
    lines = [l for l in plain_text.splitlines() if l.strip()]
    teaser = ""
    for line in lines:
        candidate = teaser + line + "\n"
        if len(candidate) > max_len:
            break
        teaser = candidate
    teaser = teaser.strip()
    # Add short eToro link
    teaser += f"\n🎁 {ETORO_REFERRAL}"
    return teaser[:280]


def _extract_top_performers(plain_text: str) -> list:
    """
    Extract top performers from the recap text for use in story/post images.
    Returns list of (symbol, pct) tuples.
    Parses lines like: "🤖 NVDA +2.34%"
    """
    import re
    performers = []
    # Match lines with a ticker and percentage
    pattern = re.compile(r"[^\s]+\s+(\$?\w[\w.]+)\s+([+-]?\d+\.\d+)%")
    for line in plain_text.splitlines():
        m = pattern.search(line)
        if m:
            symbol = m.group(1).replace("$", "")
            pct = float(m.group(2))
            performers.append((symbol, pct))
    return performers[:5]


def publish_all(
    recap_file_path: str,
    image_path: str = None,
    data: dict = None,
) -> dict:
    """
    Read the recap file and publish to all enabled social platforms.

    Args:
        recap_file_path: Path to the recap.txt file
        image_path: Optional path to the performance chart PNG
        data: Optional dict with runtime data:
              {"portfolio_daily": float, "stock_data": dict, ...}

    Returns:
        dict: {platform: True/False} for each platform attempted
    """
    results = {}
    data = data or {}
    portfolio_daily = data.get("portfolio_daily", 0.0)
    stock_data = data.get("stock_data", {})

    # Detect current session
    market_session = os.environ.get("MARKET_SESSION", "Daily recap")
    is_us_close = SESSION_US_CLOSE.lower() in market_session.lower()
    is_monthly  = SESSION_MONTHLY.lower() in market_session.lower()

    print("\n" + "=" * 60)
    print(f"🌐 SOCIAL PUBLISHER — Session: '{market_session}'")
    print(f"   → Threads/FB/IG: {'✅ YES' if is_us_close else '⏭️  NO (only at US close)'}")
    print(f"   → Twitter:       {'✅ YES' if is_monthly else '⏭️  NO (only on Monthly recap)'}")
    print("=" * 60)

    # Read recap file
    try:
        with open(recap_file_path, "r", encoding="utf-8") as f:
            full_recap = f.read()
    except Exception as e:
        print(f"❌ social_publisher: could not read recap file: {e}")
        return results

    plain_recap = _strip_html(full_recap)

    # Build text with eToro footer for each platform
    plain_with_footer = plain_recap + ETORO_FOOTER_LONG

    # Extract top performers for image generation
    top_performers = _extract_top_performers(plain_recap)

    # If no stock data provided but we have top performers from text, use those
    # (stock_data can be used for more precise top-5 extraction)
    if stock_data:
        try:
            sorted_stocks = sorted(
                stock_data.items(),
                key=lambda x: x[1].get("daily_change", 0),
                reverse=True
            )
            top_performers = [
                (sym, d.get("daily_change", 0.0))
                for sym, d in sorted_stocks[:5]
                if d.get("has_traded_today", True)
            ]
        except Exception:
            pass  # fallback to text-parsed performers

    # ── 1. Telegram (every session, HTML + image) ────────────────────
    print("\n📨 Telegram:")
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        ok = telegram_sender.send_recap_to_telegram(recap_file_path, image_path=image_path)
        results["telegram"] = ok
    else:
        print("   ⏭️  Not configured, skipping.")
        results["telegram"] = False

    # ── 2. Threads (only at US market close) ────────────────────────
    print("\n📱 Threads:")
    if not is_us_close:
        print(f"   ⏭️  Session '{market_session}' — Threads only posts at US close.")
        results["threads"] = False
    elif os.environ.get("THREADS_ACCESS_TOKEN") and os.environ.get("THREADS_USER_ID"):
        post_text = plain_with_footer
        ok = threads_sender.send_threads_post(post_text)
        results["threads"] = ok
    else:
        print("   ⏭️  Not configured, skipping.")
        results["threads"] = False

    # ── 3. Twitter/X (only on Monthly recap) ────────────────────────
    print("\n🐦 Twitter/X:")
    if not is_monthly:
        print(f"   ⏭️  Session '{market_session}' — Twitter only posts on Monthly recap.")
        results["twitter"] = False
    elif os.environ.get("TWITTER_API_KEY") and os.environ.get("TWITTER_ACCESS_TOKEN"):
        teaser = _make_twitter_teaser(plain_recap)
        ok = twitter_sender.send_twitter_post(teaser)
        results["twitter"] = ok
    else:
        print("   ⏭️  Not configured, skipping.")
        results["twitter"] = False

    # ── 4. Facebook (only at US market close, text + chart image) ───
    print("\n📘 Facebook:")
    if not is_us_close:
        print(f"   ⏭️  Session '{market_session}' — Facebook only posts at US close.")
        results["facebook"] = False
    elif os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") and os.environ.get("FACEBOOK_PAGE_ID"):
        ok = facebook_sender.send_facebook_post(plain_with_footer, image_path=image_path)
        results["facebook"] = ok
    else:
        print("   ⏭️  Not configured, skipping.")
        results["facebook"] = False

    # ── 5. Instagram (only at US market close — Story + Carousel) ───
    print("\n📸 Instagram:")
    if not is_us_close:
        print(f"   ⏭️  Session '{market_session}' — Instagram only posts at US close.")
        results["instagram_story"] = False
        results["instagram_post"] = False
    elif os.environ.get("INSTAGRAM_ACCESS_TOKEN") and os.environ.get("INSTAGRAM_USER_ID"):
        ig_results = _publish_instagram(
            plain_recap=plain_recap,
            plain_with_footer=plain_with_footer,
            portfolio_daily=portfolio_daily,
            top_performers=top_performers,
            chart_path=image_path,
            market_session=market_session,
        )
        results.update(ig_results)
    else:
        print("   ⏭️  Not configured, skipping.")
        results["instagram_story"] = False
        results["instagram_post"] = False

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("📊 SOCIAL PUBLISH SUMMARY:")
    for platform, success in results.items():
        icon = "✅" if success else ("❌" if success is False else "⏭️ ")
        print(f"   {icon} {platform.replace('_', ' ').capitalize()}")
    print("=" * 60 + "\n")

    return results


def _publish_instagram(
    plain_recap: str,
    plain_with_footer: str,
    portfolio_daily: float,
    top_performers: list,
    chart_path: str,
    market_session: str,
) -> dict:
    """Handle all Instagram publishing: Story + Carousel post."""
    results = {}

    # ── Generate Story image ─────────────────────────────────────────
    print("   📖 Generating story image...")
    story_path = None
    try:
        story_path = story_generator.generate_story_image(
            portfolio_daily=portfolio_daily,
            top_performers=top_performers,
            output_path="output/ig_story.png",
        )
    except Exception as e:
        print(f"   ❌ Story generation error: {e}")

    # ── Generate Post image ──────────────────────────────────────────
    print("   🖼️  Generating post image...")
    post_image_path = None
    try:
        post_image_path = story_generator.generate_post_image(
            portfolio_daily=portfolio_daily,
            top_performers=top_performers,
            session_name=market_session,
            output_path="output/ig_post.png",
        )
    except Exception as e:
        print(f"   ❌ Post image generation error: {e}")

    # ── Publish Story ────────────────────────────────────────────────
    if story_path:
        results["instagram_story"] = instagram_sender.send_instagram_story(story_path)
    else:
        results["instagram_story"] = False

    # ── Publish Carousel: post image + chart (if available) ──────────
    carousel_images = []
    if post_image_path and os.path.exists(post_image_path):
        carousel_images.append(post_image_path)
    if chart_path and os.path.exists(chart_path):
        carousel_images.append(chart_path)

    ig_caption = plain_with_footer[:2197] + "..." if len(plain_with_footer) > 2200 else plain_with_footer

    if len(carousel_images) >= 2:
        print(f"   🎠 Publishing carousel with {len(carousel_images)} slides...")
        results["instagram_post"] = instagram_sender.send_instagram_carousel(
            image_paths=carousel_images,
            caption=ig_caption,
        )
    elif len(carousel_images) == 1:
        print("   🖼️  Only 1 image available, publishing as single post...")
        results["instagram_post"] = instagram_sender.send_instagram_post(
            caption=ig_caption,
            image_path=carousel_images[0],
        )
    else:
        print("   ⚠️  No images available for Instagram post — skipping.")
        results["instagram_post"] = False

    return results
