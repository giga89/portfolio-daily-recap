"""
Corporate Earnings Timing & Verification Utilities.

Enforces:
1. Strict market timing awareness (BMO, AMC, European pre/post, HKEX).
2. Elimination of premature publications before market close / scheduled release time.
3. Elimination of hardcoded / fabricated placeholder figures.
4. Correct reporting quarter computation (e.g. Q3 vs Q4, and fiscal year offsets).
5. Safe quarterly revenue & YoY extraction (never annual TTM).
"""

import os
import re
import json
import datetime
from datetime import timezone, timedelta
import zoneinfo
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


def _get_verified_earnings_override(
    ticker: str,
    lookback_days: int = 4,
    now_utc: Optional[datetime.datetime] = None,
) -> Optional[Dict[str, Any]]:
    """
    Check data/verified_earnings_overrides.json for certified earnings releases
    that Yahoo Finance's earnings_dates table misses or lags on.
    """
    try:
        overrides_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "verified_earnings_overrides.json")
        if not os.path.exists(overrides_path):
            return None

        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides = json.load(f)

        clean = ticker.strip().upper()
        entry = (
            overrides.get(clean)
            or overrides.get(clean.replace(".US", ""))
            or overrides.get(clean.replace(".MI", ""))
        )
        if not entry:
            return None

        sched_str = entry.get("scheduled_dt", "")
        sched_dt = datetime.datetime.fromisoformat(sched_str.replace("Z", "+00:00"))
        if sched_dt.tzinfo is None:
            sched_dt = sched_dt.replace(tzinfo=timezone.utc)

        now = now_utc or datetime.datetime.now(timezone.utc)
        days_ago = (now.date() - sched_dt.date()).days
        if days_ago < 0 or days_ago > lookback_days:
            return None

        data = {
            "ticker": clean,
            "yf_sym": entry.get("yf_sym", clean),
            "scheduled_dt": sched_dt,
            "days_ago": days_ago,
            "quarter": entry["quarter"],
            "currency_sym": entry.get("currency_sym", "$"),
            "eps_actual": entry["eps_actual"],
            "eps_est": entry.get("eps_est"),
            "eps_beat": entry.get("eps_beat", True),
            "eps_diff_pct": entry.get("eps_diff_pct"),
            "rev_actual": entry.get("rev_actual"),
            "rev_growth": entry.get("rev_growth"),
            "y_info": entry.get("y_info", {}),
        }
        return data
    except Exception as e:
        print(f"ℹ️ Earnings override lookup note: {e}")
        return None


def verify_earnings_release_status(
    ticker: str,
    yf_sym: str,
    lookback_days: int = 3,
    check_time: Optional[datetime.datetime] = None,
    enforce_market_session_window: bool = True,
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
            override = _get_verified_earnings_override(ticker, lookback_days, now_utc)
            if override:
                if not override.get("y_info"):
                    override["y_info"] = getattr(t, "info", {}) or {}
                return True, override, "Verified earnings report published (curated registry)"
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

            # ── GUARD 2: Session timing policy (POST -> European morning, PRE -> Shortly after US open) ──
            if enforce_market_session_window:
                import zoneinfo
                ny_tz = zoneinfo.ZoneInfo("America/New_York")
                dt_et = dt_utc.astimezone(ny_tz)
                now_et = now_utc.astimezone(ny_tz)
                is_european = any(ticker.endswith(sfx) for sfx in [".MI", ".DE", ".PA", ".AS", ".CO", ".L", ".NV"])

                # AMC (Post-market close): Release hour in ET >= 15 (e.g. 16:00 ET / 20:00 UTC)
                if dt_et.hour >= 15 or dt_utc.hour >= 19:
                    # User rule: Hold until European morning (>= 07:00 UTC next morning / CET)
                    # to ensure earnings call is finished, transcripts available, and numbers verified.
                    if now_utc.date() <= dt_utc.date() or now_utc.hour < 7:
                        return (
                            False,
                            None,
                            f"Earnings for ${ticker} released AMC (post-market close). "
                            f"Holding publication until European morning window (>= 08:00 UTC) "
                            f"for complete earnings call digestion and verified data.",
                        )

                # BMO (Pre-market open): Release hour in ET < 12 (e.g. 06:00-09:00 ET)
                elif (dt_et.hour < 12 or dt_utc.hour < 16) and not is_european:
                    # User rule: Hold until shortly after US market open (>= 10:00 ET / ~14:15 UTC summer, 15:15 UTC winter)
                    # to ensure consistent regular trading session data.
                    if now_et.hour < 10:
                        return (
                            False,
                            None,
                            f"Earnings for ${ticker} released BMO (pre-market). "
                            f"Holding publication until shortly after US market open (>= 10:00 ET) "
                            f"to ensure regular session data consistency.",
                        )

            # ── GUARD 3: Reported EPS must be published and non-NaN ──
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

        # Check verified overrides / curated fallback registry if yfinance table is missing or lagging
        override = _get_verified_earnings_override(ticker, lookback_days, now_utc)
        if override:
            if not override.get("y_info"):
                override["y_info"] = getattr(t, "info", {}) or {}
            return True, override, "Verified earnings report published (curated registry)"

        return False, None, f"No earnings release found within last {lookback_days} days for {ticker}"

    except Exception as e:
        return False, None, f"Error verifying earnings for {ticker}: {e}"


# ══════════════════════════════════════════════════════════════════════════
# BOX 3 RESOLUTION ENGINE: OPTION C + B + A FALLBACK WITH RIGID VERIFICATION
# ══════════════════════════════════════════════════════════════════════════

FORBIDDEN_BOX3_PHRASES = [
    "commenti del management", "outlook strategico", "solida traiettoria",
    "forte impegno", "domanda solida", "crescita sostenuta",
    "continua ad accelerare", "risultati eccezionali", "approfonditi durante",
    "earnings call", "prospettive future", "visione a lungo termine",
    "in corso di valutazione", "in linea con le aspettative", "sostenuta dalla domanda",
    "attesi in call", "conference call", "dettagli in call", "disclaimer",
]


def verify_option_c_highlights(ticker: str, lines: list) -> Tuple[bool, list, str]:
    """Rigidly verifies Option C operational highlights against strict quality rules."""
    if not lines or len(lines) < 2:
        return False, [], "Option C requires at least 2 distinct operational bullet points"

    clean_lines = []
    for l in lines[:2]:
        text = str(l).strip()
        if text.startswith("•") or text.startswith("-"):
            text = text[1:].strip()
        if not text:
            return False, [], "Empty bullet line"
        if len(text) > 75:
            return False, [], f"Bullet line exceeds maximum length ({len(text)} > 75 chars)"
        lower = text.lower()
        for f in FORBIDDEN_BOX3_PHRASES:
            if f in lower:
                return False, [], f"Contains forbidden generic boilerplate: '{f}'"

        # Must have at least one concrete anchor: numbers, symbols (%, $, €) or recognized business entities
        has_number = bool(re.search(r"\d", text)) or any(sym in text for sym in ["%", "$", "€", "£", "B", "M", "bps"])
        has_business_entity = any(kw in lower for kw in [
            "cloud", "azure", "aws", "gpu", "blackwell", "chip", "mounjaro", "zepbound",
            "glp-1", "data center", "ricavi", "margini", "cassa", "fcf", "ebitda", "ebit",
            "utile", "buyback", "dividendo", "contratti", "aip", "retail", "server", "nodi",
            "fonderia", "rame", "eolico", "solare", "spedizioni", "volumi", "pre-market"
        ])
        if not (has_number or has_business_entity):
            return False, [], f"Bullet lacks concrete quantitative or business entity: '{text}'"
        clean_lines.append(f"• {text}")

    return True, clean_lines, "Verified"


def extract_option_c_bullets(ticker: str, quarter: str, raw_news: Optional[str] = None) -> Optional[list]:
    """Attempt to generate 2 verified operational highlight bullets via AI cascade."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = f"""Sei un analista finanziario istituzionale. Estrai ESATTAMENTE 2 sintetici punti elenco operativi sui risultati trimestrali appena pubblicati per ${ticker} ({quarter}).
News / Contesto: {raw_news or 'Trimestrale appena pubblicata'}

REGOLE TASSATIVE:
- Massimo 60 caratteri per punto.
- Punto 1: Focus su prodotto/divisione chiave o crescita segmento principale.
- Punto 2: Focus su margini, efficienza industriale o generazione di cassa.
- ZERO opinioni, ZERO frasi vaghe, ZERO 'commenti del management'.
- DEVI citare o un numero/percentuale o il nome specifico di un prodotto/divisione.
- Rispondi SOLO con 2 righe, ciascuna che inizia con '• '."""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        if response and response.text:
            raw_lines = [l.strip() for l in response.text.strip().split("\n") if l.strip()]
            ok, verified, reason = verify_option_c_highlights(ticker, raw_lines)
            if ok:
                return verified
            else:
                print(f"⚠️ Option C candidate rejected by rigid gate: {reason}")
    except Exception as e:
        print(f"⚠️ Option C extraction note: {e}")
    return None


def resolve_box3_content(
    ticker: str,
    quarter: str,
    yf_ticker_obj: Optional[Any] = None,
    raw_news: Optional[str] = None,
    lang: str = "it",
) -> Dict[str, Any]:
    """
    Resolves Box 3 content following user-specified Option C + B + A fallback sequence:
      1. Option C (Operational Highlights with Rigid Verification)
      2. Option B (Profitability / Cash Quantitative KPI: Margin % or Net Income)
      3. Option A (Curated Strategic Driver from portfolio metadata)
    """
    clean_sym = ticker.replace("$", "").strip().upper()

    # ── 1. Attempt Option C (Verified Operational Highlights) ──
    c_bullets = extract_option_c_bullets(clean_sym, quarter, raw_news=raw_news)
    if c_bullets:
        print(f"✅ Box 3: Option C verified highlights accepted for ${clean_sym}")
        return {
            "mode": "bullets",
            "title": "HIGHLIGHT OPERATIVI TRIMESTRE" if lang == "it" else "OPERATIONAL HIGHLIGHTS",
            "lines": c_bullets,
            "source": "Option C (Verified Operational Highlights)",
        }
    else:
        print(f"ℹ️ Box 3: Option C not available or rejected. Evaluating Option B for ${clean_sym}...")

    # ── 2. Attempt Option B (Profitability / Cash Quantitative KPI) ──
    try:
        t = yf_ticker_obj or (yf.Ticker(clean_sym) if YFINANCE_AVAILABLE else None)
        if t is not None:
            q_stmt = getattr(t, "quarterly_income_stmt", None)
            if q_stmt is not None and not q_stmt.empty:
                col = q_stmt.columns[0]
                if "Operating Income" in q_stmt.index and "Total Revenue" in q_stmt.index:
                    op_inc = float(q_stmt.loc["Operating Income", col])
                    tot_rev = float(q_stmt.loc["Total Revenue", col])
                    if tot_rev > 0 and op_inc > 0:
                        margin_pct = (op_inc / tot_rev) * 100
                        print(f"✅ Box 3: Option B profitability KPI accepted for ${clean_sym}: Operating Margin {margin_pct:.1f}%")
                        return {
                            "mode": "metric",
                            "title": "REDDITIVITÀ OPERATIVA" if lang == "it" else "OPERATING PROFITABILITY",
                            "metric": f"{margin_pct:.1f}%",
                            "sub": "Margine Operativo EBIT" if lang == "it" else "Operating Margin",
                            "source": "Option B (Profitability KPI - Operating Margin)",
                        }
                if "Net Income" in q_stmt.index:
                    net_inc = float(q_stmt.loc["Net Income", col])
                    if net_inc > 0:
                        y_info = getattr(t, "info", {}) or {}
                        curr = get_currency_symbol(clean_sym, y_info)
                        val_str = f"{curr}{net_inc/1e9:.1f}B" if net_inc >= 1e9 else f"{curr}{net_inc/1e6:.1f}M"
                        print(f"✅ Box 3: Option B net income accepted for ${clean_sym}: {val_str}")
                        return {
                            "mode": "metric",
                            "title": "UTILE NETTO TRIMESTRE" if lang == "it" else "NET INCOME",
                            "metric": val_str,
                            "sub": "Utile Netto GAAP" if lang == "it" else "GAAP Net Income",
                            "source": "Option B (Profitability KPI - Net Income)",
                        }
    except Exception as e:
        print(f"⚠️ Box 3 Option B evaluation note: {e}")

    # ── 3. Option A Fallback (Curated Strategic Driver - Rock-Solid Bedrock) ──
    print(f"ℹ️ Box 3: Option B not available. Using Option A (Curated Strategic Driver) for ${clean_sym}")
    from stock_focus_card import TICKER_THEMES
    info = TICKER_THEMES.get(clean_sym, {})
    driver_text = info.get("driver")
    if not driver_text:
        from portfolio_manager import PORTFOLIO_ASSETS_METADATA
        meta = PORTFOLIO_ASSETS_METADATA.get(clean_sym, {})
        catalysts = meta.get("upside_catalysts", [])
        driver_text = catalysts[0] if catalysts else meta.get("thesis", "Leadership di mercato e solidità dei flussi di cassa.")

    return {
        "mode": "text",
        "title": "DRIVER STRATEGICO & CORE BUSINESS" if lang == "it" else "STRATEGIC DRIVER & CORE BUSINESS",
        "text": driver_text,
        "source": "Option A (Curated Strategic Driver)",
    }

