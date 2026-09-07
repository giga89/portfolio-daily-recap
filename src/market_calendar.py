#!/usr/bin/env python3
"""
Market Calendar & Holiday Detection Module
==========================================
Detects market holidays for US exchanges (NYSE, NASDAQ) and European exchanges
(XETRA, LSE, Euronext, Borsa Italiana) using deterministic calendar algorithms.

Rules:
  1. US Market Closed:
     - US Market Open (us_open) -> Publish themed Holiday Meme card + post
     - US Market Close (us_close) -> DO NOT publish (skip session completely)
  2. European Market Closed:
     - If ALL European markets are closed -> Publish themed Holiday Meme card + post
     - If at least one EU market is open -> Normal session
"""

import os
import sys
import re
import random
import datetime
from typing import Tuple, Optional, Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────────────────────────────────────
# 1. Deterministic Easter & Holiday Computation (Pure Python)
# ─────────────────────────────────────────────────────────────────────────────
def get_easter_date(year: int) -> datetime.date:
    """Anonymous Gregorian algorithm (Meeus/Jones/Butcher algorithm) to compute Easter Sunday."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> datetime.date:
    """Return the nth occurrence of weekday (0=Mon, 6=Sun) in the given month."""
    first = datetime.date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + datetime.timedelta(days=offset + (n - 1) * 7)


def _last_weekday_of_month(year: int, month: int, weekday: int) -> datetime.date:
    """Return the last occurrence of weekday (0=Mon, 6=Sun) in the given month."""
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    last_day = next_month - datetime.timedelta(days=1)
    offset = (last_day.weekday() - weekday) % 7
    return last_day - datetime.timedelta(days=offset)


def _observe_us_holiday(dt: datetime.date) -> datetime.date:
    """If holiday falls on Sunday, observed on Monday. If Saturday, observed on Friday."""
    if dt.weekday() == 6:  # Sunday -> Monday
        return dt + datetime.timedelta(days=1)
    elif dt.weekday() == 5:  # Saturday -> Friday
        return dt - datetime.timedelta(days=1)
    return dt


def get_us_market_holidays(year: int) -> Dict[datetime.date, str]:
    """
    Return all official NYSE / NASDAQ stock market holidays for a given year.
    Matches standard SIFMA / NYSE holiday schedule.
    """
    easter = get_easter_date(year)
    good_friday = easter - datetime.timedelta(days=2)

    holidays = {
        _observe_us_holiday(datetime.date(year, 1, 1)): "New Year's Day",
        _nth_weekday_of_month(year, 1, 0, 3): "Martin Luther King Jr. Day",
        _nth_weekday_of_month(year, 2, 0, 3): "Washington's Birthday / Presidents' Day",
        good_friday: "Good Friday",
        _last_weekday_of_month(year, 5, 0): "Memorial Day",
        _observe_us_holiday(datetime.date(year, 6, 19)): "Juneteenth National Independence Day",
        _observe_us_holiday(datetime.date(year, 7, 4)): "Independence Day",
        _nth_weekday_of_month(year, 9, 0, 1): "Labor Day",
        _nth_weekday_of_month(year, 11, 3, 4): "Thanksgiving Day",
        _observe_us_holiday(datetime.date(year, 12, 25)): "Christmas Day",
    }
    return holidays


def is_us_market_holiday(d: Optional[datetime.date] = None) -> Tuple[bool, Optional[str]]:
    """Check if the given date (default today UTC) is an official US market holiday."""
    if d is None:
        d = datetime.datetime.now(datetime.timezone.utc).date()
    holidays = get_us_market_holidays(d.year)
    if d in holidays:
        return True, holidays[d]
    return False, None


def get_eu_universal_holidays(year: int) -> Dict[datetime.date, str]:
    """
    Holidays when ALL major European exchanges (XETRA, LSE, Euronext, Borsa Italiana)
    are universally closed.
    """
    easter = get_easter_date(year)
    good_friday = easter - datetime.timedelta(days=2)
    easter_monday = easter + datetime.timedelta(days=1)

    return {
        datetime.date(year, 1, 1): "Capodanno (New Year's Day)",
        good_friday: "Venerdì Santo (Good Friday)",
        easter_monday: "Lunedì dell'Angelo (Easter Monday)",
        datetime.date(year, 12, 25): "Natale (Christmas Day)",
        datetime.date(year, 12, 26): "Santo Stefano / Boxing Day",
    }


def is_all_eu_markets_closed(d: Optional[datetime.date] = None) -> Tuple[bool, Optional[str]]:
    """Check if ALL European markets are closed on the given date."""
    if d is None:
        d = datetime.datetime.now(datetime.timezone.utc).date()
    holidays = get_eu_universal_holidays(d.year)
    if d in holidays:
        return True, holidays[d]
    return False, None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Session Routing Logic
# ─────────────────────────────────────────────────────────────────────────────
def should_skip_or_meme_session(
    session_name: str,
    d: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    """
    Determine whether a market session should run normally, be skipped entirely,
    or switch to a themed holiday meme card.

    Returns dict:
      - {"action": "NORMAL"}
      - {"action": "SKIP", "reason": str, "holiday_name": str, "market": str}
      - {"action": "HOLIDAY_MEME", "reason": str, "holiday_name": str, "market": str}
    """
    if d is None:
        d = datetime.datetime.now(datetime.timezone.utc).date()

    s_lower = session_name.strip().lower()

    # 1. US Market Close -> SKIP COMPLETELY if US closed
    if any(k in s_lower for k in ("u.s. market close", "us_close", "us market close")):
        is_holiday, h_name = is_us_market_holiday(d)
        if is_holiday:
            return {
                "action": "SKIP",
                "reason": f"Wall Street is closed today for {h_name}. US Market Close recap skipped.",
                "holiday_name": h_name,
                "market": "US",
            }

    # 2. US Market Open -> HOLIDAY MEME if US closed
    if any(k in s_lower for k in ("u.s. market open", "us_open", "us market open")):
        is_holiday, h_name = is_us_market_holiday(d)
        if is_holiday:
            return {
                "action": "HOLIDAY_MEME",
                "reason": f"Wall Street is closed today for {h_name}. Publishing Holiday Theme Meme.",
                "holiday_name": h_name,
                "market": "US",
            }

    # 3. European Market Open -> HOLIDAY MEME if ALL EU markets closed
    if any(k in s_lower for k in ("european market open", "eu_open", "european open")):
        is_holiday, h_name = is_all_eu_markets_closed(d)
        if is_holiday:
            return {
                "action": "HOLIDAY_MEME",
                "reason": f"All European exchanges are closed today for {h_name}. Publishing Holiday Theme Meme.",
                "holiday_name": h_name,
                "market": "EU",
            }

    return {"action": "NORMAL"}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Holiday Post Text Generator & Publisher
# ─────────────────────────────────────────────────────────────────────────────
def generate_holiday_post_text(holiday_name: str, market: str = "US") -> str:
    """Generate high-engagement Italian post text for market holiday."""
    if market == "US":
        post_text = (
            f"🛋️ WALL STREET CHIUSA PER FESTIVITÀ: {holiday_name.upper()} 🇺🇸\n\n"
            f"Oggi i mercati finanziari statunitensi (NYSE e NASDAQ) rimangono chiusi per la festività nazionale del {holiday_name}. "
            "Nessuna sessione di contrattazione sui listini azionari USA.\n\n"
            "I mercati europei ($SX7PEX.DE, $ENI.MI, $WDEF.L) e il comparto crypto proseguono invece regolarmente le negoziazioni.\n\n"
            "Il nostro portafoglio mantiene la consueta strategia di lungo periodo: Risk Score 3/10 su eToro, zero leva finanziaria "
            "e 100% titoli reali. Nessuna ansia da trading e modalità relax attiva! ☕🌿\n\n"
            "Le regolari sessioni di Wall Street riprenderanno domani alle 15:30 italiane con la riapertura dei mercati.\n\n"
            "Buona festa a tutta la community! 👇\n\n"
            "📌 $SPX500 $NSDQ100 $PLTR $NVDA $SX7PEX.DE"
        )
    else:
        post_text = (
            f"🏖️ BORSE EUROPEE CHIUSE PER FESTIVITÀ: {holiday_name.upper()} 🇪🇺\n\n"
            f"Oggi i principali listini europei (XETRA, London Stock Exchange, Euronext e Borsa Italiana) rimangono chiusi "
            f"in occasione di {holiday_name}.\n\n"
            "Le negoziazioni sulle borse del continente sono sospese, mentre il nostro portafoglio continua a lavorare a lungo termine "
            "con compounding solido e zero stress.\n\n"
            "Auguriamo a tutta la community una splendida giornata di relax! ☕🌿\n\n"
            "📌 $SX7PEX.DE $ENI.MI $WDEF.L $SPX500"
        )

    return post_text.strip()


def publish_holiday_meme_session(
    session_name: str,
    holiday_name: str,
    market: str = "US",
    output_dir: str = "output",
) -> Dict[str, Any]:
    """
    Publish the Holiday Theme Meme card and post to eToro and Telegram.
    Saves outputs to output/recap.txt and output/holiday_meme.png.
    """
    print("=" * 65)
    print(f"🏖️ PUBLISHING HOLIDAY MEME CARD FOR: {holiday_name} ({market})")
    print(f"🕒 Timestamp: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 65)

    os.makedirs(output_dir, exist_ok=True)
    post_text = generate_holiday_post_text(holiday_name, market)

    # 1. Generate Holiday Meme Card
    card_path = None
    try:
        import meme_generator
        card_path = meme_generator.generate_meme_card(
            portfolio_daily=0.0,
            lang="it",
            is_holiday=True,
            holiday_name=holiday_name,
        )
        if card_path and os.path.exists(card_path):
            import shutil
            target_card = os.path.join(output_dir, "holiday_meme.png")
            shutil.copy2(card_path, target_card)
            card_path = target_card
            print(f"✅ Generated Holiday Meme Card: {card_path}")
    except Exception as exc:
        print(f"⚠️ Error generating holiday meme card: {exc}")

    # 2. Format footer and save recap.txt artifact
    profile_footer = "\n\n👤 Segui il mio portafoglio su eToro: https://www.etoro.com/people/andrearavalli"
    full_text = post_text + profile_footer
    recap_file = os.path.join(output_dir, "recap.txt")
    with open(recap_file, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"💾 Saved holiday recap text to {recap_file}")

    results: Dict[str, Any] = {"success": True, "holiday": holiday_name, "market": market}

    # 3. Publish to eToro Social Feed
    try:
        import etoro_sender
        if etoro_sender.etoro_client.is_configured():
            ok_etoro = etoro_sender.send_etoro_post(
                text=post_text,
                image_path=card_path if (card_path and os.path.exists(card_path)) else None,
            )
            results["etoro"] = ok_etoro
            if ok_etoro:
                print("✅ Holiday Meme post published successfully to eToro!")
                try:
                    import analytics_tracker
                    analytics_tracker.record_post(
                        platform="etoro",
                        post_id=etoro_sender.LAST_PUBLISHED_POST_ID or f"holiday_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')}",
                        session_name=f"Holiday Meme ({holiday_name})",
                        text=post_text,
                        image_type="meme_card",
                        tickers=["SPX500", "NSDQ100", "PLTR", "NVDA"],
                    )
                    analytics_tracker.update_and_build_dashboard()
                except Exception as a_err:
                    print(f"⚠️ Analytics tracking warning: {a_err}")
        else:
            print("ℹ️ eToro credentials not configured, skipping eToro send.")
            results["etoro"] = False
    except Exception as e:
        print(f"❌ Failed to publish holiday post to eToro: {e}")
        results["etoro"] = False

    # 4. Publish to Telegram
    try:
        import telegram_sender
        if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
            if card_path and os.path.exists(card_path):
                telegram_sender.send_telegram_photo(card_path, caption=full_text[:1024])
            else:
                telegram_sender.send_telegram_message(full_text[:4096])
            print("✅ Holiday Meme post published to Telegram!")
            results["telegram"] = True
        else:
            results["telegram"] = False
    except Exception as e:
        print(f"⚠️ Telegram send warning: {e}")
        results["telegram"] = False

    return results


if __name__ == "__main__":
    today = datetime.datetime.now(datetime.timezone.utc).date()
    is_us_h, us_name = is_us_market_holiday(today)
    is_eu_h, eu_name = is_all_eu_markets_closed(today)
    print(f"Date: {today} ({today.strftime('%A')})")
    print(f"US Market Holiday: {is_us_h} ({us_name})")
    print(f"EU All Closed Holiday: {is_eu_h} ({eu_name})")
    print("\nAction for 'U.S. market open':", should_skip_or_meme_session("U.S. market open", today))
    print("Action for 'U.S. market close':", should_skip_or_meme_session("U.S. market close", today))
    print("Action for 'European market open':", should_skip_or_meme_session("European market open", today))
