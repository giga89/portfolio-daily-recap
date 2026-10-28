"""
Corporate Earnings Timing & Verification Utilities.

Enforces:
1. Strict market timing awareness (BMO, AMC, European pre/post, HKEX).
2. Elimination of premature publications before market close / scheduled release time.
3. Elimination of hardcoded / fabricated placeholder figures.
4. Correct reporting quarter computation (e.g. Q3 vs Q4, and fiscal year offsets).
5. Safe quarterly revenue & YoY extraction (never annual TTM).
"""

import datetime
from datetime import timezone, timedelta
from typing import Optional, Dict, Any, Tuple
import pandas as pd

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    YFINANCE_AVAILABLE = False


def get_currency_symbol(ticker: str, yf_info: Optional[dict] = None) -> str:
    """Return the correct currency symbol for a given ticker."""
    curr = (yf_info or {}).get("currency")
    if curr == "EUR":
        return "€"
    if curr in ("GBP", "GBp"):
        return "£"
    if curr == "HKD":
        return "HK$"
    if curr == "DKK":
        return "DKK "
    if any(ticker.endswith(sfx) for sfx in [".MI", ".DE", ".NV", ".PA", ".AS"]):
        return "€"
    if ticker.endswith(".L"):
        return "£"
    if ticker.endswith(".HK"):
        return "HK$"
    return "$"


def get_reporting_quarter(ticker: str, report_date: datetime.date) -> str:
    """
    Calculate the precise corporate reporting quarter based on report date and fiscal year.
    Companies report the preceding completed quarter, not the current one.
    """
    month = report_date.month
    year = report_date.year
    clean = ticker.upper().replace("$", "").strip()

    # Special fiscal year exceptions in monitored portfolio
    if clean == "MSFT":
        # Microsoft FY ends June 30.
        # Oct/Nov/Dec -> Q1 FY(year+1)
        # Jan/Feb/Mar -> Q2 FY(year)
        # Apr/May/Jun -> Q3 FY(year)
        # Jul/Aug/Sep -> Q4 FY(year)
        fy_map = {
            10: f"Q1 FY{year+1}", 11: f"Q1 FY{year+1}", 12: f"Q1 FY{year+1}",
            1: f"Q2 FY{year}", 2: f"Q2 FY{year}", 3: f"Q2 FY{year}",
            4: f"Q3 FY{year}", 5: f"Q3 FY{year}", 6: f"Q3 FY{year}",
            7: f"Q4 FY{year}", 8: f"Q4 FY{year}", 9: f"Q4 FY{year}",
        }
        return fy_map.get(month, f"Q3 {year}")

    elif clean == "NVDA":
        # NVIDIA FY ends January 31.
        # Nov/Dec -> Q3 FY(year+1)
        # Feb/Mar -> Q4 FY(year)
        # May/Jun -> Q1 FY(year+1)
        # Aug/Sep -> Q2 FY(year+1)
        fy_map = {
            11: f"Q3 FY{year+1}", 12: f"Q3 FY{year+1}",
            2: f"Q4 FY{year}", 3: f"Q4 FY{year}",
            5: f"Q1 FY{year+1}", 6: f"Q1 FY{year+1}",
            8: f"Q2 FY{year+1}", 9: f"Q2 FY{year+1}",
        }
        return fy_map.get(month, f"Q3 {year}")

    elif clean == "AAPL":
        # Apple FY ends September 30.
        # Oct/Nov -> Q4 FY(year)
        # Jan/Feb -> Q1 FY(year+1)
        # Apr/May -> Q2 FY(year+1)
        # Jul/Aug -> Q3 FY(year+1)
        fy_map = {
            10: f"Q4 FY{year}", 11: f"Q4 FY{year}",
            1: f"Q1 FY{year+1}", 2: f"Q1 FY{year+1}",
            4: f"Q2 FY{year}", 5: f"Q2 FY{year}",
            7: f"Q3 FY{year}", 8: f"Q3 FY{year}",
        }
        return fy_map.get(month, f"Q4 {year}")

    # Standard calendar year companies (Jan-Dec)
    # Months 1-3 report Q4 of prior year
    # Months 4-6 report Q1 of current year
    # Months 7-9 report Q2 of current year
    # Months 10-12 report Q3 of current year
    if month in (1, 2, 3):
        return f"Q4 {year - 1}"
    elif month in (4, 5, 6):
        return f"Q1 {year}"
    elif month in (7, 8, 9):
        return f"Q2 {year}"
    else:
        return f"Q3 {year}"


def extract_quarterly_financials(
    ticker: str,
    yf_ticker_obj: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Safely extract most recent quarterly revenue and YoY revenue growth from quarterly_income_stmt.
    Never uses annual / TTM totalRevenue.
    """
    res: Dict[str, Any] = {
        "rev_actual": None,
        "rev_growth": None,
        "currency_sym": "$",
    }
    if not YFINANCE_AVAILABLE:
        return res

    try:
        t = yf_ticker_obj or yf.Ticker(ticker)
        y_info = getattr(t, "info", {}) or {}
        curr_sym = get_currency_symbol(ticker, y_info)
        res["currency_sym"] = curr_sym

        q_stmt = t.quarterly_income_stmt
        if q_stmt is not None and not q_stmt.empty and "Total Revenue" in q_stmt.index:
            col_curr = q_stmt.columns[0]
            val_curr = float(q_stmt.loc["Total Revenue", col_curr])
            if val_curr > 0:
                if val_curr >= 1e9:
                    res["rev_actual"] = f"{curr_sym}{val_curr / 1e9:.1f}B"
                else:
                    res["rev_actual"] = f"{curr_sym}{val_curr / 1e6:.1f}M"

                # Check YoY (4 quarters back)
                if len(q_stmt.columns) >= 5:
                    col_yoy = q_stmt.columns[4]
                    val_yoy = float(q_stmt.loc["Total Revenue", col_yoy])
                    if val_yoy > 0:
                        growth = ((val_curr - val_yoy) / val_yoy) * 100
                        res["rev_growth"] = f"{growth:+.1f}% YoY"
    except Exception as e:
        print(f"⚠️ Financials extraction note for {ticker}: {e}")

    return res


def verify_earnings_release_status(
    ticker: str,
    yf_sym: str,
    lookback_days: int = 3,
    check_time: Optional[datetime.datetime] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Strictly verifies whether a corporate earnings report for `ticker` has ALREADY
    been officially released to the market and has verified reported figures.

    Returns:
        (is_released: bool, data_dict: Optional[dict], reason: str)
    """
    if not YFINANCE_AVAILABLE:
        return False, None, "yfinance not available"

    now_utc = check_time or datetime.datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    try:
        t = yf.Ticker(yf_sym)
        ed = t.earnings_dates
        if ed is None or ed.empty:
            return False, None, f"No earnings dates available in data provider for {yf_sym}"

        # Search the most recent entries within the lookback window
        for dt, row in ed.head(5).iterrows():
            dt_utc = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            days_ago = (now_utc.date() - dt_utc.date()).days

            # Must fall strictly in [0, lookback_days]
            if days_ago < 0:
                continue
            if days_ago > lookback_days:
                break

            # ── GUARD 1: Release hour must have passed ──
            # Add a 15-minute buffer after scheduled release time
            earliest_release_allowed = dt_utc + timedelta(minutes=15)
            if now_utc < earliest_release_allowed:
                hours_remaining = (earliest_release_allowed - now_utc).total_seconds() / 3600.0
                return (
                    False,
                    None,
                    f"Earnings release scheduled for {dt_utc.strftime('%Y-%m-%d %H:%M UTC')} "
                    f"(in {hours_remaining:.1f}h). Market release time not reached yet.",
                )

            # ── GUARD 2: Reported EPS must be published and non-NaN ──
            rep_eps = row.get("Reported EPS")
            if pd.isna(rep_eps) or rep_eps is None:
                return (
                    False,
                    None,
                    f"Scheduled release date was {dt_utc.strftime('%Y-%m-%d %H:%M UTC')}, "
                    f"but Reported EPS is still NaN/pending in financial data.",
                )

            # ── Data is VERIFIED released! ──
            est_eps = row.get("EPS Estimate")
            surp_val = row.get("Surprise(%)")
            y_info = getattr(t, "info", {}) or {}
            curr_sym = get_currency_symbol(ticker, y_info)
            quarter_str = get_reporting_quarter(ticker, dt_utc.date())

            rep_float = float(rep_eps)
            est_float = float(est_eps) if (est_eps is not None and not pd.isna(est_eps)) else None

            eps_actual_str = f"{curr_sym}{rep_float:.2f}"
            eps_est_str = f"{curr_sym}{est_float:.2f}" if est_float is not None else None
            eps_beat = (rep_float >= est_float) if est_float is not None else True

            diff_str = None
            if surp_val is not None and not pd.isna(surp_val):
                diff_str = f"{float(surp_val):+.1f}% Surprise"

            # Fetch safe quarterly financials
            fin = extract_quarterly_financials(ticker, yf_ticker_obj=t)

            data = {
                "ticker": ticker,
                "yf_sym": yf_sym,
                "scheduled_dt": dt_utc,
                "days_ago": days_ago,
                "quarter": quarter_str,
                "currency_sym": curr_sym,
                "eps_actual": eps_actual_str,
                "eps_est": eps_est_str,
                "eps_beat": eps_beat,
                "eps_diff_pct": diff_str,
                "rev_actual": fin.get("rev_actual"),
                "rev_growth": fin.get("rev_growth"),
                "y_info": y_info,
            }
            return True, data, "Verified earnings report published"

        return False, None, f"No earnings release found within last {lookback_days} days for {ticker}"

    except Exception as e:
        return False, None, f"Error verifying earnings for {ticker}: {e}"

