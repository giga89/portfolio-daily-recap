#!/usr/bin/env python3
"""
Social Publisher — Orchestrator
Sends the portfolio recap to all configured social platforms.

Session routing:
  Telegram   → every session (unchanged)
  Twitter/X  → US market close (daily, no monthly limit)
  Bluesky    → US market close (daily)
  LinkedIn   → Weekly recap only (Sat/Sun) — professional format
  Threads    → US market close (daily) — pending Meta restriction fix
  Facebook   → US market close (daily) — pending Meta restriction fix
  Instagram  → US market close (daily) — pending Meta restriction fix

eToro profile + referral link appended to all posts.
"""

import os

import telegram_sender
import twitter_sender
import bluesky_sender
import linkedin_sender
import threads_sender
import facebook_sender
import instagram_sender
import story_generator


# ── eToro constants ───────────────────────────────────────────────────────────
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
    f"🎁 {ETORO_REFERRAL}"
)

# Session name constants
SESSION_US_CLOSE = "U.S. market close"
SESSION_WEEKLY_SAT = "Weekly recap (Sat)"
SESSION_WEEKLY_SUN = "Weekly recap (Sun)"
SESSION_MONTHLY = "Monthly recap"


def _strip_html(text: str) -> str:
    """Remove HTML tags used by Telegram (other platforms expect plain text)."""
    import re
    text = re.sub(r"<b>(.*?)</b>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<i>(.*?)</i>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _make_twitter_post(plain_text: str) -> str:
    """Build a Twitter post (max 280 chars) from the recap."""
    MAX = 270  # reserve 10 for the referral link
    lines = [l for l in plain_text.splitlines() if l.strip()]
    teaser = ""
    for line in lines:
        candidate = (teaser + "\n" + line).strip()
        if len(candidate) > MAX:
            break
        teaser = candidate
    teaser = teaser.strip() or plain_text[:MAX]
    return (teaser + f"\n\n{ETORO_REFERRAL}")[:280]


def _extract_top_performers(plain_text: str, stock_data: dict = None) -> list:
    """Extract top 5 performers from stock_data or fallback to text parsing."""
    if stock_data:
        try:
            sorted_stocks = sorted(
                stock_data.items(),
                key=lambda x: x[1].get("daily_change", 0),
                reverse=True,
            )
            return [
                (sym, d.get("daily_change", 0.0))
                for sym, d in sorted_stocks[:5]
                if d.get("has_traded_today", True)
            ]
        except Exception:
            pass

    # Fallback: parse text
    import re
    pattern = re.compile(r"[^\s]+\s+(\$?\w[\w.]+)\s+([+-]?\d+\.\d+)%")
    performers = []
    for line in plain_text.splitlines():
        m = pattern.search(line)
        if m:
            performers.append((m.group(1).replace("$", ""), float(m.group(2))))
    return performers[:5]


def publish_all(
    recap_file_path: str,
    image_path: str = None,
    data: dict = None,
) -> dict:
    """
    Read the recap and publish to all enabled platforms.

    Args:
        recap_file_path: Path to recap.txt
        image_path: Optional path to the performance chart PNG
        data: {"portfolio_daily": float, "stock_data": dict}

    Returns:
        dict: {platform: True/False}
    """
    results = {}
    data = data or {}
    portfolio_daily = data.get("portfolio_daily", 0.0)
    stock_data = data.get("stock_data", {})

    market_session = os.environ.get("MARKET_SESSION", "Daily recap")
    is_us_close = SESSION_US_CLOSE.lower() in market_session.lower()
    is_weekly   = any(s.lower() in market_session.lower()
                      for s in [SESSION_WEEKLY_SAT, SESSION_WEEKLY_SUN, "weekly"])
    is_monthly  = SESSION_MONTHLY.lower() in market_session.lower()

    print("\n" + "=" * 60)
    print(f"🌐 SOCIAL PUBLISHER — Session: '{market_session}'")
    print(f"   → Telegram:          always")
    print(f"   → Twitter / Bluesky: {'✅ YES' if is_us_close else '⏭️  only at US close'}")
    print(f"   → LinkedIn:          {'✅ YES' if is_weekly else '⏭️  only on weekly recap'}")
    print(f"   → Threads/FB/IG:     {'✅ YES' if is_us_close else '⏭️  only at US close'}")
    print("=" * 60)

    # ── Read recap ──────────────────────────────────────────────────
    try:
        with open(recap_file_path, "r", encoding="utf-8") as f:
            full_recap = f.read()
    except Exception as e:
        print(f"❌ Could not read recap file: {e}")
        return results

    plain_recap = _strip_html(full_recap)
    plain_with_footer = plain_recap + ETORO_FOOTER_LONG
    top_performers = _extract_top_performers(plain_recap, stock_data)

    # ── 1. Telegram (every session) ──────────────────────────────────
    print("\n📨 Telegram:")
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        ok = telegram_sender.send_recap_to_telegram(recap_file_path, image_path=image_path)
        results["telegram"] = ok
    else:
        print("   ⏭️  Not configured.")
        results["telegram"] = False

    # ── 2. Twitter/X (US close, daily — no monthly cap) ─────────────
    print("\n🐦 Twitter/X:")
    if not is_us_close:
        print(f"   ⏭️  Only at US close.")
        results["twitter"] = False
    elif os.environ.get("TWITTER_API_KEY") and os.environ.get("TWITTER_ACCESS_TOKEN"):
        tweet = _make_twitter_post(plain_recap)
        ok = twitter_sender.send_twitter_post(tweet)
        results["twitter"] = ok
    else:
        print("   ⏭️  Not configured.")
        results["twitter"] = False

    # ── 3. Bluesky (US close, daily) ─────────────────────────────────
    print("\n🦋 Bluesky:")
    if not is_us_close:
        print(f"   ⏭️  Only at US close.")
        results["bluesky"] = False
    elif os.environ.get("BLUESKY_HANDLE") and os.environ.get("BLUESKY_APP_PASS"):
        ok = bluesky_sender.send_bluesky_post(plain_with_footer)
        results["bluesky"] = ok
    else:
        print("   ⏭️  Not configured.")
        results["bluesky"] = False

    # ── 4. LinkedIn (weekly only — professional format) ───────────────
    print("\n💼 LinkedIn:")
    if not is_weekly:
        print(f"   ⏭️  Only on weekly recap.")
        results["linkedin"] = False
    elif os.environ.get("LINKEDIN_ACCESS_TOKEN"):
        ok = linkedin_sender.send_linkedin_post(plain_recap)
        results["linkedin"] = ok
    else:
        print("   ⏭️  Not configured.")
        results["linkedin"] = False

    # ── 5. Threads (US close — pending Meta restriction fix) ──────────
    print("\n📱 Threads:")
    if not is_us_close:
        print(f"   ⏭️  Only at US close.")
        results["threads"] = False
    elif os.environ.get("THREADS_ACCESS_TOKEN") and os.environ.get("THREADS_USER_ID"):
        ok = threads_sender.send_threads_post(plain_with_footer)
        results["threads"] = ok
    else:
        print("   ⏭️  Not configured (pending Meta restriction fix).")
        results["threads"] = False

    # ── 6. Facebook (US close — pending Meta restriction fix) ─────────
    print("\n📘 Facebook:")
    if not is_us_close:
        print(f"   ⏭️  Only at US close.")
        results["facebook"] = False
    elif os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") and os.environ.get("FACEBOOK_PAGE_ID"):
        ok = facebook_sender.send_facebook_post(plain_with_footer, image_path=image_path)
        results["facebook"] = ok
    else:
        print("   ⏭️  Not configured (pending Meta restriction fix).")
        results["facebook"] = False

    # ── 7. Instagram (US close — Story + carousel) ────────────────────
    print("\n📸 Instagram:")
    if not is_us_close:
        print(f"   ⏭️  Only at US close.")
        results["instagram_story"] = False
        results["instagram_post"] = False
    elif os.environ.get("INSTAGRAM_ACCESS_TOKEN") and os.environ.get("INSTAGRAM_USER_ID"):
        ig = _publish_instagram(
            plain_recap=plain_recap,
            plain_with_footer=plain_with_footer,
            portfolio_daily=portfolio_daily,
            top_performers=top_performers,
            chart_path=image_path,
            market_session=market_session,
        )
        results.update(ig)
    else:
        print("   ⏭️  Not configured (pending Meta restriction fix).")
        results["instagram_story"] = False
        results["instagram_post"] = False

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("📊 SOCIAL PUBLISH SUMMARY:")
    for platform, success in results.items():
        icon = "✅" if success else "❌"
        print(f"   {icon} {platform.replace('_', ' ').capitalize()}")
    print("=" * 60 + "\n")

    return results


def _publish_instagram(
    plain_recap, plain_with_footer, portfolio_daily,
    top_performers, chart_path, market_session
) -> dict:
    """Handle Instagram Story + carousel post."""
    results = {}

    story_path = None
    try:
        story_path = story_generator.generate_story_image(
            portfolio_daily=portfolio_daily,
            top_performers=top_performers,
            output_path="output/ig_story.png",
        )
    except Exception as e:
        print(f"   ❌ Story generation error: {e}")

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

    results["instagram_story"] = (
        instagram_sender.send_instagram_story(story_path)
        if story_path else False
    )

    carousel_images = [p for p in [post_image_path, chart_path]
                       if p and os.path.exists(p)]
    ig_caption = plain_with_footer[:2197] + "..." \
        if len(plain_with_footer) > 2200 else plain_with_footer

    if len(carousel_images) >= 2:
        results["instagram_post"] = instagram_sender.send_instagram_carousel(
            carousel_images, ig_caption)
    elif len(carousel_images) == 1:
        results["instagram_post"] = instagram_sender.send_instagram_post(
            ig_caption, image_path=carousel_images[0])
    else:
        print("   ⚠️  No images — Instagram post skipped.")
        results["instagram_post"] = False

    return results
