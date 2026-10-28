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
import json
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


# ─────────────────────────────────────────────────────────────────────────────
# 4. Deterministic Next Trading Session & Upcoming Earnings Calendar
# ─────────────────────────────────────────────────────────────────────────────

WEEKDAY_IT = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MONTH_IT = [
    "", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
]

PORTFOLIO_EARNINGS_TICKERS = [
    # Core US holdings and Mega-cap Tech Titans
    "NVDA", "MSFT", "AMZN", "GOOG", "PLTR", "AVGO", "TSM", "MRVL",
    "LLY", "ABBV", "ABT", "HUM", "CCJ", "WMT", "AAPL", "META",
    # European corporate holdings
    "NOVO-B.CO", "AZN.L", "ENEL.MI", "ENI.MI", "PRY.MI", "BESI.NV", "RACE", "GLEN.L", "ULVR.L"
]


def get_equity_holdings_for_earnings() -> List[Tuple[str, str]]:
    """
    Dynamically returns a list of (portfolio_symbol, yahoo_ticker) tuples for all
    active equity holdings in the portfolio, excluding ETFs, commodities, and crypto.
    """
    excluded_non_equities = {
        "PPFB.DE", "IB01.L", "SX7PEX.DE", "IEUR", "IQQL.DE", "TRX", "SPCX.RTH",
        "WCLD.L", "INDO.PA", "WDEF.L", "XEON.DE", "MAU.PA", "MELI"
    }
    candidates: List[Tuple[str, str]] = []
    try:
        from portfolio_manager import PORTFOLIO_ASSETS_METADATA
        for sym, meta in PORTFOLIO_ASSETS_METADATA.items():
            if sym in excluded_non_equities:
                continue
            sector = meta.get("sector", "")
            if any(term in sector for term in ["ETF", "Safe Haven", "Titoli di Stato", "Blockchain"]):
                continue
            yf_sym = meta.get("yahoo_ticker", sym.replace(".US", "").replace(".NV", ".AS"))
            candidates.append((sym, yf_sym))
    except Exception:
        candidates = [(t, t.replace(".US", "").replace(".NV", ".AS")) for t in PORTFOLIO_EARNINGS_TICKERS]

    # Add mega-cap tech bellwethers if not present
    for titan in [("AAPL", "AAPL"), ("META", "META")]:
        if not any(c[0] == titan[0] for c in candidates):
            candidates.append(titan)

    return candidates


def get_next_trading_session_info(
    current_date: Optional[datetime.date] = None,
    market: str = "US",
) -> Dict[str, Any]:
    """
    Computes deterministic information about the NEXT trading session.
    Takes into account weekends (Saturday/Sunday) and official market holidays.
    """
    if current_date is None:
        current_date = datetime.datetime.now(datetime.timezone.utc).date()

    check_date = current_date + datetime.timedelta(days=1)
    skipped_holidays: List[str] = []

    while True:
        # Check weekends
        if check_date.weekday() >= 5:  # 5=Sat, 6=Sun
            check_date += datetime.timedelta(days=1)
            continue

        # Check market holidays
        if market.upper() == "US":
            is_hol, hol_name = is_us_market_holiday(check_date)
        else:
            is_hol, hol_name = is_all_eu_markets_closed(check_date)

        if is_hol:
            if hol_name and hol_name not in skipped_holidays:
                skipped_holidays.append(hol_name)
            check_date += datetime.timedelta(days=1)
            continue

        # Found active trading day
        break

    next_date = check_date
    days_ahead = (next_date - current_date).days
    is_tomorrow = (days_ahead == 1)

    next_weekday_it = WEEKDAY_IT[next_date.weekday()]
    month_name_it = MONTH_IT[next_date.month]
    formatted_date = f"{next_weekday_it} {next_date.day} {month_name_it}"
    full_formatted_date = f"{next_weekday_it} {next_date.day} {month_name_it} {next_date.year}"

    # Build natural timing phrasing for prompts and verification
    if is_tomorrow and not skipped_holidays:
        timing_phrase = f"nella seduta di domani ({formatted_date})"
        timing_short = f"Domani ({formatted_date})"
    elif current_date.weekday() == 4:  # Friday close looking to Monday
        timing_phrase = f"alla riapertura dei mercati di lunedì ({next_date.day} {month_name_it})"
        timing_short = f"Lunedì ({next_date.day} {month_name_it})"
    elif skipped_holidays:
        hol_str = ", ".join(skipped_holidays)
        timing_phrase = f"nella prossima seduta di {formatted_date} (mercati chiusi nel frattempo per {hol_str})"
        timing_short = f"{next_weekday_it.capitalize()} ({next_date.day} {month_name_it})"
    else:
        timing_phrase = f"nella prossima seduta di {formatted_date}"
        timing_short = f"{next_weekday_it.capitalize()} ({next_date.day} {month_name_it})"

    return {
        "current_date": current_date,
        "next_date": next_date,
        "days_ahead": days_ahead,
        "is_tomorrow": is_tomorrow,
        "is_friday_close": (current_date.weekday() == 4),
        "next_weekday_it": next_weekday_it,
        "formatted_date": formatted_date,
        "full_formatted_date": full_formatted_date,
        "timing_phrase": timing_phrase,
        "timing_short": timing_short,
        "skipped_holidays": skipped_holidays,
    }


def get_upcoming_earnings_calendar(
    target_date: Optional[datetime.date] = None,
    max_cache_age_hours: float = 12.0,
    force_refresh: bool = False,
) -> Dict[str, str]:
    """
    Returns a dict mapping ticker -> 'YYYY-MM-DD' of known upcoming corporate earnings dates.
    Caches results in data/earnings_calendar_cache.json to guarantee sub-millisecond execution.
    """
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    cache_path = os.path.join(cache_dir, "earnings_calendar_cache.json")

    # Attempt cache load
    if not force_refresh and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            updated_str = cached_data.get("updated_at", "")
            if updated_str:
                updated_dt = datetime.datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                age = (datetime.datetime.now(datetime.timezone.utc) - updated_dt).total_seconds() / 3600.0
                if age < max_cache_age_hours and isinstance(cached_data.get("earnings"), dict):
                    return cached_data["earnings"]
        except Exception as c_err:
            print(f"ℹ️ Earnings cache read note: {c_err}")

    # Refresh via yfinance
    earnings_map: Dict[str, str] = {}
    try:
        import yfinance as yf
        symbols_to_query = get_equity_holdings_for_earnings()
        for sym, yf_sym in symbols_to_query:
            try:
                t = yf.Ticker(yf_sym)
                c = t.calendar
                if c and "Earnings Date" in c:
                    ed = c["Earnings Date"]
                    d = ed[0] if isinstance(ed, list) else ed
                    if isinstance(d, (datetime.date, datetime.datetime)):
                        earnings_map[sym] = d.strftime("%Y-%m-%d")
                    elif isinstance(d, str):
                        earnings_map[sym] = d[:10]
            except Exception:
                continue
    except Exception as yf_err:
        print(f"ℹ️ yfinance earnings lookup note: {yf_err}")

    # Fallback to existing cache if refresh produced few results
    if not earnings_map and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f).get("earnings", {})
        except Exception:
            pass

    # Save to cache
    if earnings_map:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({
                    "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "earnings": earnings_map,
                }, f, indent=2)
        except Exception as save_err:
            print(f"⚠️ Failed to save earnings cache: {save_err}")

    return earnings_map


def get_earnings_for_session(target_date: datetime.date) -> List[Dict[str, Any]]:
    """
    Returns corporate earnings scheduled precisely on target_date for monitored portfolio assets.
    """
    calendar_map = get_upcoming_earnings_calendar(target_date)
    target_str = target_date.strftime("%Y-%m-%d")
    matches = []

    try:
        from portfolio_manager import PORTFOLIO_ASSETS_METADATA
    except ImportError:
        PORTFOLIO_ASSETS_METADATA = {}

    for sym, date_str in calendar_map.items():
        if date_str == target_str:
            meta = PORTFOLIO_ASSETS_METADATA.get(sym, {})
            name = meta.get("name", sym)
            matches.append({
                "ticker": sym,
                "name": name,
                "tag": f"${sym}",
                "date_str": date_str,
            })

    return matches


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
