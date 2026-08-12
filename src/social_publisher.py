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
from datetime import datetime

import telegram_sender
import twitter_sender
import bluesky_sender
import linkedin_sender
import threads_sender
import facebook_sender
import instagram_sender
import etoro_sender
import stock_focus_card
import stock_focus_infographic
import analytics_tracker
import story_generator
import ai_news_generator
import etoro_history


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
SESSION_US_CLOSE                 = "U.S. market close"
SESSION_WEEKLY_SAT               = "Weekly recap (Sat)"
SESSION_WEEKLY_SUN               = "Weekly recap (Sun)"
SESSION_MONTHLY                  = "Monthly recap"
SESSION_MONDAY                   = "Monday decision post"
SESSION_STOCK_FOCUS              = "Stock focus"
SESSION_WEEKLY_PORTFOLIO_OUTLOOK = "Weekly portfolio outlook"
SESSION_WEEKLY_MACRO_OUTLOOK     = "Weekly macro outlook"


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
    pie_chart_path: str = None,
    ai_cover_path: str = None,
    engagement_card_path: str = None,
    data: dict = None,
) -> dict:
    """
    Read the recap and publish to all enabled platforms.

    Args:
        recap_file_path:      Path to recap.txt
        image_path:           Optional path to the performance chart PNG
        pie_chart_path:       Optional path to a pie chart PNG (alternates each session)
        ai_cover_path:        Optional path to the AI/PIL cover image
        engagement_card_path: Optional path to the square engagement question card
        data: {"portfolio_daily": float, "stock_data": dict, "portfolio_weights": dict,
               "portfolio_perf": float, "portfolio_weekly": float}

    Returns:
        dict: {platform: True/False}
    """
    results = {}
    data = data or {}
    portfolio_daily   = data.get("portfolio_daily", 0.0)
    stock_data        = data.get("stock_data", {})
    portfolio_weights = data.get("portfolio_weights", {})
    portfolio_perf    = data.get("portfolio_perf", 0.0)
    portfolio_weekly  = data.get("portfolio_weekly", None)

    market_session = os.environ.get("MARKET_SESSION", "Daily recap")
    is_us_close          = SESSION_US_CLOSE.lower() in market_session.lower()
    is_weekly            = any(s.lower() in market_session.lower()
                               for s in [SESSION_WEEKLY_SAT, SESSION_WEEKLY_SUN, "weekly"])
    is_monthly           = SESSION_MONTHLY.lower() in market_session.lower()
    is_monday            = SESSION_MONDAY.lower() in market_session.lower()
    is_stock_focus       = SESSION_STOCK_FOCUS.lower() in market_session.lower()
    is_portfolio_outlook = SESSION_WEEKLY_PORTFOLIO_OUTLOOK.lower() in market_session.lower()
    is_macro_outlook     = SESSION_WEEKLY_MACRO_OUTLOOK.lower() in market_session.lower()

    # ── Special Sessions ──────────────────────────────────────────────────
    if is_monday:
        print("\n" + "=" * 60)
        print(f"📅 MONDAY SESSION — Decision & Empathy Post")
        print("=" * 60)
        results.update(_publish_monday_posts(
            portfolio_perf=portfolio_perf,
            portfolio_weekly=portfolio_weekly,
            portfolio_weights=portfolio_weights,
            pie_chart_path=pie_chart_path,
        ))
        return results

    if is_stock_focus:
        specified_ticker = None
        if ":" in market_session:
            specified_ticker = market_session.split(":", 1)[1].strip()
        print("\n" + "=" * 60)
        print(f"🔍 DAILY SESSION — Single Stock Focus Deep-Dive (Ticker: {specified_ticker or 'Auto-Rotate'})")
        print("=" * 60)
        results.update(_publish_stock_focus_post(specified_ticker))
        return results

    if is_portfolio_outlook:
        print("\n" + "=" * 60)
        print(f"📅 SATURDAY SESSION — Weekly Portfolio Outlook")
        print("=" * 60)
        results.update(_publish_weekly_portfolio_outlook())
        return results

    if is_macro_outlook:
        print("\n" + "=" * 60)
        print(f"🌍 SATURDAY SESSION — Weekly Global Macro Outlook")
        print("=" * 60)
        results.update(_publish_weekly_macro_outlook())
        return results

    print("\n" + "=" * 60)
    print(f"🌐 SOCIAL PUBLISHER — Session: '{market_session}'")
    print(f"   → Telegram:          always")
    print(f"   → Twitter / Bluesky: {'✅ YES' if is_us_close else '⏭️  only at US close'}")
    print(f"   → LinkedIn:          {'✅ YES' if is_weekly else '⏭️  only on weekly recap'}")
    print(f"   → Threads/FB/IG:     {'✅ YES' if is_us_close else '⏭️  only at US close'}")
    print(f"   → Pie chart:         {'✅ ' + pie_chart_path if pie_chart_path else '⏭️  not generated'}")
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

    # ── 1. Telegram (every session) — sends AI cover + recap + charts ──
    print("\n📨 Telegram:")
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        # Send AI cover as primary visual (if available)
        if ai_cover_path and os.path.exists(ai_cover_path):
            try:
                telegram_sender.send_telegram_photo(ai_cover_path, caption="")
                print("   🎨 AI cover image sent to Telegram")
            except Exception as exc:
                print(f"   ⚠️ AI cover send failed: {exc}")

        # Send text recap + performance chart
        ok = telegram_sender.send_recap_to_telegram(recap_file_path, image_path=image_path)
        results["telegram"] = ok
        # Also send pie chart as a separate photo when available
        if pie_chart_path and os.path.exists(pie_chart_path):
            try:
                caption = "📊 Portfolio breakdown — alternating views each session"
                telegram_sender.send_telegram_photo(pie_chart_path, caption=caption)
                print("   🥧 Pie chart sent to Telegram")
            except Exception as exc:
                print(f"   ⚠️ Pie chart send failed: {exc}")
        # Send engagement card to boost interaction
        if ok and engagement_card_path and os.path.exists(engagement_card_path):
            try:
                telegram_sender.send_telegram_photo(
                    engagement_card_path,
                    caption="💬 Lascia un commento qui sotto! ⬇️",
                )
                print("   💬 Engagement card sent to Telegram")
            except Exception as exc:
                print(f"   ⚠️ Engagement card send failed: {exc}")
    else:
        print("   ⏭️  Not configured.")
        results["telegram"] = False

    # ── 2. Twitter/X (US close — 2-tweet thread) ─────────────────────
    print("\n🐦 Twitter/X:")
    if not is_us_close:
        print(f"   ⏭️  Only at US close.")
        results["twitter"] = False
    elif os.environ.get("TWITTER_API_KEY") and os.environ.get("TWITTER_ACCESS_TOKEN"):
        tweets = twitter_sender.build_twitter_thread(
            portfolio_daily=portfolio_daily,
            top_performers=top_performers,
            session_name=market_session,
            plain_recap=plain_recap,
        )
        ok = twitter_sender.send_twitter_thread(tweets)
        results["twitter"] = ok
    else:
        print("   ⏭️  Not configured.")
        results["twitter"] = False

    # ── 3. Bluesky (US close — 2-post thread with engagement image) ────────────
    print("\n🦋 Bluesky:")
    if not is_us_close:
        print(f"   ⏭️  Only at US close.")
        results["bluesky"] = False
    elif os.environ.get("BLUESKY_HANDLE") and os.environ.get("BLUESKY_APP_PASS"):
        bsky_posts = bluesky_sender.build_bluesky_thread(
            portfolio_daily=portfolio_daily,
            top_performers=top_performers,
            session_name=market_session,
        )
        if engagement_card_path and os.path.exists(engagement_card_path):
            ok = bluesky_sender.send_bluesky_thread_with_image(
                bsky_posts,
                image_path=engagement_card_path,
                image_alt="Portfolio daily performance — lascia un commento!",
            )
        else:
            ok = bluesky_sender.send_bluesky_thread(bsky_posts)
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

    # ── 8. eToro Social Feed (Every session — with Winners & Losers card) ────
    print("\n🐂 eToro Social Feed:")
    if etoro_sender.etoro_client.is_configured():
        # Always prefer the Winners & Losers (Top & Flop) card as requested
        card_to_upload = engagement_card_path if (engagement_card_path and os.path.exists(engagement_card_path)) else image_path
        etoro_text = etoro_sender.build_etoro_post_text(
            plain_recap=plain_recap,
            portfolio_daily=portfolio_daily,
            top_performers=top_performers,
            session_name=market_session,
        )
        ok = etoro_sender.send_etoro_post(
            text=etoro_text,
            image_path=card_to_upload,
        )
        results["etoro"] = ok
        if ok:
            analytics_tracker.record_post(
                platform="etoro",
                post_id=f"recap_{market_session.replace(' ', '_').lower()}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
                session_name=market_session,
                text=etoro_text,
                image_type="winners_losers_card" if card_to_upload == engagement_card_path else "chart",
            )
            # Execute 3-comment cross-linking sequence in immediate succession (5s interval) to save runner minutes
            if etoro_sender.LAST_PUBLISHED_POST_ID and market_session in ["U.S. market open", "European market open", "U.S. market close"]:
                try:
                    import cross_link_scheduler
                    target_pid = etoro_sender.LAST_PUBLISHED_POST_ID
                    print(f"🚀 Publishing 3 cross-linking comments on eToro post {target_pid} in immediate sequence (5s interval)...")
                    cross_link_scheduler.run_comments_sequence(
                        post_id=target_pid,
                        interval_seconds=5,
                        session_name=market_session,
                        market_data=portfolio_data
                    )
                except Exception as c_err:
                    print(f"⚠️ Failed to execute cross_link_scheduler: {c_err}")
    else:
        print("   ⏭️  Not configured (ETORO_USER_KEY missing).")
        results["etoro"] = False

    # Update and regenerate analytics dashboard HTML for GitHub Pages
    try:
        analytics_tracker.update_and_build_dashboard()
    except Exception as exc:
        print(f"⚠️ Analytics dashboard update warning: {exc}")

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("📊 SOCIAL PUBLISH SUMMARY:")
    for platform, success in results.items():
        icon = "✅" if success else "❌"
        print(f"   {icon} {platform.replace('_', ' ').capitalize()}")
    print("=" * 60 + "\n")

    return results


def _publish_monday_posts(
    portfolio_perf: float,
    portfolio_weekly: float = None,
    portfolio_weights: dict = None,
    pie_chart_path: str = None,
) -> dict:
    """
    Generate and send Monday decision + empathy posts to Telegram.
    Also sends the current pie chart.

    Returns:
        dict: {platform: True/False}
    """
    results = {}

    if not (os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")):
        print("   ⏭️  Telegram not configured.")
        results["telegram_decision"] = False
        results["telegram_empathy"] = False
        return results

    # Load eToro history for context
    history = etoro_history.get_history_from_gist()
    history_stats_text  = etoro_history.get_stats_summary_text(history)
    recent_closes_text  = etoro_history.get_recent_closes_text(history, days=30)

    # 1. Decision post
    print("\n📋 Generating decision post...")
    decision_text = ai_news_generator.generate_decision_post(
        recent_closes_text=recent_closes_text,
        current_weights=portfolio_weights,
        history_stats_text=history_stats_text,
    )
    if decision_text:
        header = "<b>📋 DECISIONE DELLA SETTIMANA</b>\n\n"
        footer = ETORO_FOOTER_LONG
        full_msg = header + decision_text + footer
        ok = telegram_sender.send_telegram_message(full_msg[:4096])
        results["telegram_decision"] = ok
        print(f"   {'✅' if ok else '❌'} Decision post sent")
    else:
        print("   ⚠️  Decision post generation failed")
        results["telegram_decision"] = False

    # 2. Empathy post
    print("\n💬 Generating empathy post...")
    empathy_text = ai_news_generator.generate_empathy_post(
        portfolio_perf=portfolio_perf,
        weekly_perf=portfolio_weekly,
        history_stats_text=history_stats_text,
    )
    if empathy_text:
        header = "<b>💬 UN PENSIERO PER VOI</b>\n\n"
        footer = ETORO_FOOTER_LONG
        full_msg = header + empathy_text + footer
        ok = telegram_sender.send_telegram_message(full_msg[:4096])
        results["telegram_empathy"] = ok
        print(f"   {'✅' if ok else '❌'} Empathy post sent")
    else:
        print("   ⚠️  Empathy post generation failed")
        results["telegram_empathy"] = False

    # 3. eToro Social Feed for Empathy Post
    print("\n🐂 eToro Social Feed (Empathy Post):")
    if etoro_sender.etoro_client.is_configured() and empathy_text:
        top_flop_img = "output/winners_losers.png"
        ok_etoro = etoro_sender.send_etoro_post(
            text=empathy_text,
            image_path=top_flop_img if os.path.exists(top_flop_img) else None,
        )
        results["etoro_empathy"] = ok_etoro
        if ok_etoro:
            analytics_tracker.record_post(
                platform="etoro",
                post_id=f"empathy_{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
                session_name="Monday decision / Empathy",
                text=empathy_text,
                image_type="winners_losers_card",
            )
    else:
        results["etoro_empathy"] = False

    # 4. Pie chart (if available)
    if pie_chart_path and os.path.exists(pie_chart_path):
        try:
            caption = "📊 Come è composto il portfolio questa settimana — aggiornato in tempo reale da eToro."
            telegram_sender.send_telegram_photo(pie_chart_path, caption=caption)
            results["telegram_pie_chart"] = True
            print("   ✅ Pie chart sent to Telegram")
        except Exception as exc:
            print(f"   ⚠️  Pie chart send failed: {exc}")
            results["telegram_pie_chart"] = False

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


# ── Artifact Saving & Special Session Publishers ──────────────────────────────

def _save_post_to_artifacts(filename: str, title: str, content: str):
    """
    Save generated post content into output/ and the AGY conversation artifacts folder.
    """
    os.makedirs("output", exist_ok=True)
    out_path = os.path.join("output", filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"💾 Saved post to {out_path}")

    # Also attempt to copy to conversation artifacts directory if it exists
    brain_dir = os.environ.get("CONVERSATION_ARTIFACTS_DIR", r"C:\Users\andre\.gemini\antigravity\brain\0f2f1dd3-ac81-49cc-b9be-1d45e0dd1585")
    if os.path.exists(brain_dir):
        art_dir = os.path.join(brain_dir, "generated_posts")
        os.makedirs(art_dir, exist_ok=True)
        art_path = os.path.join(art_dir, filename)
        with open(art_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📦 Saved post artifact to {art_path}")


def _publish_stock_focus_post(ticker: str = None) -> dict:
    """Publish Daily Stock Focus post to Telegram & eToro with 16:9 Stock Focus Card."""
    results = {}
    stock_focus_res = ai_news_generator.generate_stock_focus_post(ticker)
    if not stock_focus_res or not isinstance(stock_focus_res, (tuple, list)) or len(stock_focus_res) < 2:
        print("⚠️ Stock focus generation returned invalid result, skipping publish.")
        return {"telegram_stock_focus": False, "etoro_stock_focus": False}

    ticker_sym, post_text = stock_focus_res
    if not post_text:
        print("⚠️ Stock focus post text empty, skipping publish.")
        return {"telegram_stock_focus": False, "etoro_stock_focus": False}

    full_text = post_text + ETORO_FOOTER_LONG
    _save_post_to_artifacts(f"stock_focus_{ticker_sym}.txt", f"Stock Focus - {ticker_sym}", full_text)

    # 1. Generate High-End Investor Infographic (Hitachi Style)
    card_path = f"output/infographic_{ticker_sym}.png"
    try:
        card_path = stock_focus_infographic.generate_stock_infographic(
            ticker=ticker_sym,
            output_path=card_path,
        )
    except Exception as exc:
        print(f"⚠️ Infographic generation warning: {exc}")
        # Fallback to stock_focus_card if needed
        try:
            from portfolio_manager import load_config
            config = load_config()
            comp_name = config.get("tickers", {}).get(ticker_sym, [None, ticker_sym])[1]
            card_path = stock_focus_card.generate_stock_focus_card(
                ticker=ticker_sym,
                company_name=comp_name,
                output_path=f"output/stock_focus_{ticker_sym}.png",
            )
        except Exception:
            card_path = None

    # 2. eToro Social Feed
    print("\n🐂 eToro Social Feed (Stock Focus):")
    if etoro_sender.etoro_client.is_configured():
        ok_etoro = etoro_sender.send_etoro_post(
            text=post_text,
            image_path=card_path if (card_path and os.path.exists(card_path)) else None,
        )
        results["etoro_stock_focus"] = ok_etoro
        if ok_etoro:
            analytics_tracker.record_post(
                platform="etoro",
                post_id=f"focus_{ticker_sym}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
                session_name="Stock focus",
                text=post_text,
                image_type="stock_focus_card",
                tickers=[ticker_sym],
            )
    else:
        print("   ⏭️  eToro not configured.")
        results["etoro_stock_focus"] = False

    # 3. Telegram send
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        try:
            telegram_sender.send_telegram_message(full_text)
            if card_path and os.path.exists(card_path):
                telegram_sender.send_telegram_photo(card_path, caption=f"🔍 Focus Titolo: ${ticker_sym}")
            print(f"✅ Stock Focus post for {ticker_sym} published to Telegram")
            results["telegram_stock_focus"] = True
        except Exception as e:
            print(f"❌ Telegram send failed for Stock Focus: {e}")
            results["telegram_stock_focus"] = False
    else:
        print("   ⏭️  Telegram not configured.")
        results["telegram_stock_focus"] = False

    try:
        analytics_tracker.update_and_build_dashboard()
    except Exception:
        pass

    return results


def _publish_weekly_portfolio_outlook() -> dict:
    """Publish Saturday Portfolio Outlook post to Telegram and eToro."""
    results = {}
    post_text = ai_news_generator.generate_weekly_portfolio_outlook()
    if not post_text:
        print("⚠️ Weekly portfolio outlook post text empty, skipping publish.")
        return {"telegram_portfolio_outlook": False, "etoro_portfolio_outlook": False}

    full_text = post_text + ETORO_FOOTER_LONG
    _save_post_to_artifacts("weekly_portfolio_outlook.txt", "Weekly Portfolio Outlook", full_text)

    # eToro send with Winners & Losers card if available
    if etoro_sender.etoro_client.is_configured():
        top_flop_img = "output/winners_losers.png"
        ok_etoro = etoro_sender.send_etoro_post(
            text=post_text,
            image_path=top_flop_img if os.path.exists(top_flop_img) else None,
        )
        results["etoro_portfolio_outlook"] = ok_etoro
        if ok_etoro:
            analytics_tracker.record_post(
                platform="etoro",
                post_id=f"outlook_{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
                session_name="Weekly portfolio outlook",
                text=post_text,
                image_type="winners_losers_card",
            )
    else:
        results["etoro_portfolio_outlook"] = False

    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        try:
            telegram_sender.send_telegram_message(full_text)
            print("✅ Weekly Portfolio Outlook published to Telegram")
            results["telegram_portfolio_outlook"] = True
        except Exception as e:
            print(f"❌ Telegram send failed for Portfolio Outlook: {e}")
            results["telegram_portfolio_outlook"] = False
    else:
        print("   ⏭️  Telegram not configured.")
        results["telegram_portfolio_outlook"] = False

    return results


def _publish_weekly_macro_outlook() -> dict:
    """Publish Saturday Global Macro Outlook post to Telegram and eToro."""
    results = {}
    post_text = ai_news_generator.generate_weekly_macro_outlook()
    if not post_text:
        print("⚠️ Weekly macro outlook post text empty, skipping publish.")
        return {"telegram_macro_outlook": False, "etoro_macro_outlook": False}

    full_text = post_text + ETORO_FOOTER_LONG
    _save_post_to_artifacts("weekly_macro_outlook.txt", "Weekly Macro Outlook", full_text)

    # eToro send
    if etoro_sender.etoro_client.is_configured():
        top_flop_img = "output/winners_losers.png"
        ok_etoro = etoro_sender.send_etoro_post(
            text=post_text,
            image_path=top_flop_img if os.path.exists(top_flop_img) else None,
        )
        results["etoro_macro_outlook"] = ok_etoro
    else:
        results["etoro_macro_outlook"] = False

    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        try:
            telegram_sender.send_telegram_message(full_text)
            print("✅ Weekly Global Macro Outlook published to Telegram")
            results["telegram_macro_outlook"] = True
        except Exception as e:
            print(f"❌ Telegram send failed for Macro Outlook: {e}")
            results["telegram_macro_outlook"] = False
    else:
        print("   ⏭️  Telegram not configured.")
        results["telegram_macro_outlook"] = False

    return results
