#!/usr/bin/env python3
"""
Schedule window guard and trading-date helpers for GitHub Actions fallback crons
and Gist session deduplication.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

try:
    import pytz
except ImportError:  # pragma: no cover
    pytz = None

US_TIMEZONE_SESSIONS = {
    "U.S. market open",
    "U.S. market close",
    "Monthly recap",
}

# Mapping of normalized session name -> tuple of (allowed_weekdays, start_hhmm, end_hhmm, label)
_SESSION_WINDOWS = {
    "European market open": (((1, 2, 3, 4, 5), 845, 1130),),
    "U.S. market open": (((1, 2, 3, 4, 5), 900, 1130),),
    "U.S. market close": (((1, 2, 3, 4, 5), 1530, 1830),),
    "Daily crypto recap": (((1, 2, 3, 4, 5, 6, 7), 1500, 2130),),
    "Stock focus": (((1, 2, 3, 4, 5), 1230, 1700),),
    "Copy trading post": (
        ((1, 2, 3, 4, 5), 1130, 1630),
        ((6,), 1030, 1500),
    ),
    "Community Poll": (((1, 3, 5), 1100, 1630),),
    "Weekly recap (Sat)": (((6,), 930, 1500),),
    "Weekly recap (Sun)": (((7,), 1630, 2345),),
}


def _get_tz(tz_name: str):
    """Return a tzinfo object for tz_name using zoneinfo with pytz fallback."""
    if ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    if pytz is not None:
        return pytz.timezone(tz_name)
    raise RuntimeError(f"No timezone provider available for '{tz_name}'")


def _normalize_session(session_name: str) -> str:
    """Normalize parameterized session names (e.g. 'Stock focus:NVDA' -> 'Stock focus')."""
    s = (session_name or "").strip()
    if s.startswith("Stock focus"):
        return "Stock focus"
    return s


def _ensure_utc(now_utc: Optional[datetime]) -> datetime:
    """Return a timezone-aware UTC datetime."""
    if now_utc is None:
        return datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        return now_utc.replace(tzinfo=timezone.utc)
    return now_utc.astimezone(timezone.utc)


def get_session_timezone(session_name: str) -> str:
    """Return canonical market/community IANA timezone for a session."""
    norm = _normalize_session(session_name)
    if norm in US_TIMEZONE_SESSIONS:
        return "America/New_York"
    return "Europe/Rome"


def get_session_trading_date(
    session_name: str,
    now_utc: Optional[datetime] = None,
) -> str:
    """Return canonical trading/session calendar date (YYYY-MM-DD) in the session's timezone."""
    utc_dt = _ensure_utc(now_utc)
    tz = _get_tz(get_session_timezone(session_name))
    return utc_dt.astimezone(tz).strftime("%Y-%m-%d")


def _format_window_desc(rules: tuple) -> str:
    """Format allowed weekday/HHMM rules into a readable summary."""
    parts = []
    for dows, start_hhmm, end_hhmm in rules:
        parts.append(
            f"dow in {list(dows)} {start_hhmm // 100:02d}:{start_hhmm % 100:02d}-"
            f"{end_hhmm // 100:02d}:{end_hhmm % 100:02d}"
        )
    return " or ".join(parts)


def is_schedule_within_window(
    session_name: str,
    trigger: str,
    now_utc: Optional[datetime] = None,
    force_run: bool = False,
) -> Tuple[bool, str]:
    """
    Validate whether a GitHub Actions fallback `schedule` trigger is running inside
    its intended market/community time window.
    """
    if force_run:
        return True, "Force run bypassed schedule window check"

    trig = (trigger or "").strip()
    if trig != "schedule":
        return True, f"Trigger '{trig}' does not require fallback cron window guard"

    norm = _normalize_session(session_name)
    tz_name = get_session_timezone(norm)
    now_local = _ensure_utc(now_utc).astimezone(_get_tz(tz_name))
    hhmm = now_local.hour * 100 + now_local.minute
    dow = now_local.isoweekday()
    local_str = now_local.strftime("%Y-%m-%d %H:%M %Z")

    if norm == "Monthly recap":
        is_last_day = (now_local + timedelta(days=1)).day == 1
        in_hours = 1500 <= hhmm <= 1900
        if is_last_day and in_hours:
            return True, f"Within Monthly recap window ({local_str}, dow={dow})"
        return (
            False,
            f"Outside Monthly recap window: local={local_str}, dow={dow}, "
            f"is_last_day={is_last_day}; allowed last calendar day of month 15:00-19:00 {tz_name}",
        )

    rules = _SESSION_WINDOWS.get(norm)
    if not rules:
        return True, f"No window restriction for session '{session_name}'"

    for allowed_dows, start_hhmm, end_hhmm in rules:
        if dow in allowed_dows and start_hhmm <= hhmm <= end_hhmm:
            return True, f"Within {norm} window ({local_str}, dow={dow})"

    allowed_desc = _format_window_desc(rules)
    return (
        False,
        f"Outside {norm} window: local={local_str}, dow={dow}; "
        f"allowed {allowed_desc} ({tz_name})",
    )
