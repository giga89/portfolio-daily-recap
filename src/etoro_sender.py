#!/usr/bin/env python3
"""
eToro Social Feed Sender
========================
Formats and publishes portfolio recaps directly to the eToro Social Feed.
Supports:
  • Uploading image attachments (Top & Flop / Winners & Losers card)
  • Converting recap text with cashtags (e.g. $NVDA, $PLTR)
  • Returning direct post links
"""

import os
import re
from typing import Optional, List, Tuple
import etoro_client


def _strip_html(text: str) -> str:
    """Remove HTML tags used by Telegram/HTML formatters."""
    text = re.sub(r"<b>(.*?)</b>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<i>(.*?)</i>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _add_cashtags(text: str) -> str:
    """Ensure standard ticker mentions have cashtags for eToro feed (e.g. NVDA -> $NVDA)."""
    # Replace ticker mentions in lines like "• NVDA +4.5%" or "NVDA:" with "$NVDA"
    # Avoid replacing already prefixed $TICKER
    pattern = r'(?<![\$\w])([A-Z]{2,6}(?:\.[A-Z]{2})?)(?=\s*[:\+\-\(]|\s+[\+\-]\d)'
    return re.sub(pattern, r'$\1', text)


def build_etoro_post_text(
    plain_recap: str,
    portfolio_daily: Optional[float] = None,
    top_performers: Optional[List[Tuple[str, float]]] = None,
    session_name: str = "Daily recap",
) -> str:
    """
    Format a clean post suitable for the eToro Social Feed.
    Max 4000 chars.
    """
    clean_text = _strip_html(plain_recap)
    tagged_text = _add_cashtags(clean_text)

    # Add header if not already present
    perf_str = f" ({portfolio_daily:+.2f}%)" if portfolio_daily is not None else ""
    header = f"📊 Recap Portafoglio — {session_name}{perf_str}\n\n"

    # Limit to 3800 characters to leave room for tags/footer
    if len(tagged_text) > 3600:
        tagged_text = tagged_text[:3600] + "\n\n... (recap completo su canale)"

    footer = "\n\n💬 Cosa ne pensate della sessione di oggi? Lasciate un commento qui sotto! 👇"
    
    post_content = f"{tagged_text}{footer}".strip()
    return post_content[:3950]


def send_etoro_post(
    text: str,
    image_path: Optional[str] = None,
    language: str = "it",
) -> bool:
    """
    Send a post to the eToro Social Feed with an optional image attachment.

    Args:
        text: Post content (plain text, max 4000 characters)
        image_path: Path to image file (e.g. output/winners_losers.png)
        language: ISO 639-1 language code (default: 'it')

    Returns:
        bool: True if published successfully, False otherwise
    """
    if not etoro_client.is_configured():
        print("   ⏭️  eToro API not configured (ETORO_USER_KEY missing).")
        return False

    print("📢 Publishing post to eToro Social Feed...")
    attachment_objects = []

    # Upload attachment if provided
    if image_path and os.path.exists(image_path):
        print(f"   🖼️ Uploading media attachment: {os.path.basename(image_path)}")
        att = etoro_client.upload_attachment(image_path)
        if att and att.get("url"):
            attachment_objects.append(att)
            print(f"   ✓ Media attached: {att.get('url', '')[:80]}...")
        else:
            print("   ⚠️ Media upload failed, continuing with text-only post.")

    # Automatically resolve all mentioned cashtags to eToro market IDs
    found_tickers = re.findall(r"\$([A-Za-z0-9\.\-]+)", text)
    market_ids = etoro_client.get_market_ids_for_tickers(found_tickers)
    if market_ids:
        print(f"   🏷️ Tagged eToro markets: {found_tickers} -> IDs {market_ids}")

    clean_content = _strip_html(text)

    res = etoro_client.create_post(
        content=clean_content,
        language=language,
        attachment_objects=attachment_objects if attachment_objects else None,
        market_ids=market_ids if market_ids else None,
    )

    if res.get("success"):
        post_id = res.get("id")
        _, _, username = etoro_client.get_credentials()
        print(f"   ✅ Published on eToro! Profile: https://www.etoro.com/people/{username}")
        if post_id:
            print(f"   🔗 Post ID: {post_id}")
        return True
    else:
        print(f"   ❌ Failed to publish on eToro: {res.get('error')}")
        return False


def build_stock_focus_cross_link_comment(recent_count: int = 3) -> str:
    """
    Build a cross-linking comment referencing the last 3 Stock Focus posts.
    """
    import time
    from stock_focus_card import TICKER_THEMES

    # Retrieve last used tickers from gist / local analytics
    try:
        from gist_storage import get_used_stock_focus_tickers
        used = get_used_stock_focus_tickers()
    except Exception:
        used = []

    if not used or len(used) < recent_count:
        default_top = ["PLTR", "NVDA", "CCJ", "SX7PEX.DE", "LLY"]
        used = (used + [t for t in default_top if t not in used])

    recent = used[-recent_count:]
    recent.reverse()  # most recent first

    lines = [
        "💡 <b>APPROFONDIMENTI TITOLI IN PORTAFOGLIO</b>",
        "Se vuoi approfondire le singole posizioni e la tesi di lungo termine, ecco gli ultimi focus dedicati:\n"
    ]

    for idx, ticker in enumerate(recent, 1):
        info = TICKER_THEMES.get(ticker, {})
        sector = info.get("sector", "Azienda")
        thesis = info.get("thesis", "Tesi fondamentale di crescita.")
        lines.append(f"{idx}️⃣ <b>${ticker}</b> · {sector}\n   ↳ <i>{thesis}</i>\n")

    lines.append("👉 Trovi tutti i dettagli e le analisi sul mio profilo @AndreaRavalli! 🎯")
    return "\n".join(lines)


def send_delayed_cross_link_comment(
    post_id: str,
    delay_seconds: int = 600,
    language: str = "it",
) -> bool:
    """
    Wait `delay_seconds` (default 10 minutes) then post the cross-linking comment under `post_id`.
    """
    import time
    if not post_id or not etoro_client.is_configured():
        return False

    if delay_seconds > 0:
        print(f"⏳ Waiting {delay_seconds // 60} minutes ({delay_seconds}s) before posting cross-link comment...")
        time.sleep(delay_seconds)

    comment_msg = build_stock_focus_cross_link_comment(recent_count=3)
    clean_msg = _strip_html(comment_msg)

    print(f"💬 Posting cross-link comment to eToro post {post_id}...")
    res = etoro_client.add_post_comment(
        post_id=post_id,
        message=clean_msg,
        language=language,
    )
    return res.get("success", False)

