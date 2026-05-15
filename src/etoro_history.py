#!/usr/bin/env python3
"""
eToro History Parser
Parses eToro account statement Excel files and stores the history in GitHub Gist.
Tracks closed positions, deposits, dividends, and portfolio stats over time.
"""

import os
import json
import pandas as pd
from datetime import datetime

try:
    import gist_storage
    GIST_AVAILABLE = True
except ImportError:
    GIST_AVAILABLE = False


# ── Excel sheet names ─────────────────────────────────────────────────────────
SHEET_CLOSED   = 'Closed Positions'
SHEET_ACTIVITY = 'Account Activity'
SHEET_DIVIDENDS = 'Dividends'
SHEET_SUMMARY  = 'Financial Summary'

# Number of recent closed positions to store in Gist for decision posts
RECENT_POSITIONS_LIMIT = 30


def parse_excel(filepath: str) -> dict:
    """
    Parse an eToro account statement Excel file and return structured history data.

    Args:
        filepath: Path to the .xlsx file downloaded from eToro

    Returns:
        dict with keys: import_date, period, financial_summary, stats, recent_positions
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Excel file not found: {filepath}")

    print(f"📂 Parsing eToro history from: {filepath}")
    xl = pd.ExcelFile(filepath)

    closed    = _parse_closed_positions(xl)
    activity  = _parse_account_activity(xl)
    dividends = _parse_dividends(xl)
    fin_sum   = _parse_financial_summary(xl)

    # Determine period
    period_from = closed['Open Date'].min().strftime('%Y-%m-%d') if not closed.empty else 'unknown'
    period_to   = closed['Close Date'].max().strftime('%Y-%m-%d') if not closed.empty else 'unknown'

    stats           = _compute_stats(closed, activity, dividends)
    recent_positions = _get_recent_positions(closed)

    history = {
        'import_date': datetime.now().strftime('%Y-%m-%d'),
        'period': {'from': period_from, 'to': period_to},
        'financial_summary': fin_sum,
        'stats': stats,
        'recent_positions': recent_positions,
    }

    print(f"✅ Parsed {stats['total_trades']} trades | Win rate: {stats['win_rate']}% | Total P&L: ${stats['total_pnl_usd']:.2f}")
    return history


# ── Sheet parsers ─────────────────────────────────────────────────────────────

def _parse_closed_positions(xl: pd.ExcelFile) -> pd.DataFrame:
    df = xl.parse(SHEET_CLOSED, header=0)

    df['Open Date']  = pd.to_datetime(df['Open Date'],  dayfirst=True, errors='coerce')
    df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')
    df['hold_days']  = (df['Close Date'] - df['Open Date']).dt.days
    df['year']       = df['Close Date'].dt.year

    # Normalize numeric columns
    for col in ['Amount', 'Profit(USD)', 'Profit(EUR)', 'Spread Fees (USD)']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    return df


def _parse_account_activity(xl: pd.ExcelFile) -> pd.DataFrame:
    df = xl.parse(SHEET_ACTIVITY, header=0)
    df['Date']   = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
    return df


def _parse_dividends(xl: pd.ExcelFile) -> pd.DataFrame:
    df = xl.parse(SHEET_DIVIDENDS, header=0)
    df['Date of Payment'] = pd.to_datetime(df['Date of Payment'], dayfirst=True, errors='coerce')
    df['Net Dividend Received (USD)'] = pd.to_numeric(
        df['Net Dividend Received (USD)'], errors='coerce'
    ).fillna(0.0)
    return df


def _parse_financial_summary(xl: pd.ExcelFile) -> dict:
    df = xl.parse(SHEET_SUMMARY, header=0)

    result = {}
    # Row format: Name | Amount in (USD) | Amount in (EUR) | Tax Rate
    for _, row in df.iterrows():
        name = str(row.iloc[0]).strip()
        try:
            usd_val = float(str(row.iloc[1]).replace(',', '.'))
        except (ValueError, TypeError):
            usd_val = 0.0
        if name and name != 'Name':
            # Normalize key
            key = (
                name.lower()
                .replace(' ', '_')
                .replace('(', '')
                .replace(')', '')
                .replace('/', '_')
            )
            result[key] = usd_val

    return result


# ── Stats computation ─────────────────────────────────────────────────────────

def _compute_stats(
    closed: pd.DataFrame,
    activity: pd.DataFrame,
    dividends: pd.DataFrame,
) -> dict:
    if closed.empty:
        return {}

    # P&L per year
    pnl_by_year = (
        closed.groupby('year')['Profit(USD)']
        .sum()
        .round(2)
        .to_dict()
    )
    pnl_by_year = {int(k): float(v) for k, v in pnl_by_year.items()}

    # P&L per asset type
    pnl_by_type = (
        closed.groupby('Type')['Profit(USD)']
        .sum()
        .round(2)
        .to_dict()
    )
    pnl_by_type = {str(k): float(v) for k, v in pnl_by_type.items()}

    # Win rate
    total_trades = len(closed)
    winning      = len(closed[closed['Profit(USD)'] > 0])
    win_rate     = round(winning / total_trades * 100, 1) if total_trades else 0.0

    # Hold times
    avg_hold    = round(float(closed['hold_days'].mean()), 1)
    median_hold = round(float(closed['hold_days'].median()), 1)

    # Total P&L
    total_pnl = round(float(closed['Profit(USD)'].sum()), 2)

    # Best/worst trades (top 5 each)
    def _trade_record(row):
        return {
            'name':        str(row['Action']),
            'type':        str(row['Type']),
            'amount_usd':  round(float(row['Amount']), 2),
            'profit_usd':  round(float(row['Profit(USD)']), 2),
            'open_date':   row['Open Date'].strftime('%Y-%m-%d') if pd.notna(row['Open Date']) else '',
            'close_date':  row['Close Date'].strftime('%Y-%m-%d') if pd.notna(row['Close Date']) else '',
            'hold_days':   int(row['hold_days']) if pd.notna(row['hold_days']) else 0,
        }

    best_trades  = [_trade_record(r) for _, r in closed.nlargest(5, 'Profit(USD)').iterrows()]
    worst_trades = [_trade_record(r) for _, r in closed.nsmallest(5, 'Profit(USD)').iterrows()]

    # Top assets by number of trades
    top_assets = (
        closed['Action']
        .value_counts()
        .head(15)
        .reset_index()
        .rename(columns={'Action': 'name', 'count': 'trades'})
        .to_dict(orient='records')
    )

    # Deposits/withdrawals
    deposit_types  = ['Deposit']
    withdraw_types = ['Withdraw Request']
    deposits = activity[activity['Type'].isin(deposit_types)]
    withdraws = activity[activity['Type'].isin(withdraw_types)]
    total_deposits  = round(float(deposits['Amount'].sum()), 2)
    total_withdraws = round(float(withdraws['Amount'].sum()), 2)

    # Dividends
    total_dividends = round(float(dividends['Net Dividend Received (USD)'].sum()), 2)

    # Count by type
    trades_by_type = (
        closed.groupby('Type')
        .size()
        .to_dict()
    )
    trades_by_type = {str(k): int(v) for k, v in trades_by_type.items()}

    return {
        'total_trades':       total_trades,
        'winning_trades':     winning,
        'win_rate':           win_rate,
        'avg_hold_days':      avg_hold,
        'median_hold_days':   median_hold,
        'total_pnl_usd':      total_pnl,
        'pnl_by_year':        pnl_by_year,
        'pnl_by_type':        pnl_by_type,
        'trades_by_type':     trades_by_type,
        'best_trades':        best_trades,
        'worst_trades':       worst_trades,
        'top_assets_by_count': top_assets,
        'total_deposits_usd': total_deposits,
        'total_withdraws_usd': total_withdraws,
        'total_dividends_usd': total_dividends,
    }


def _get_recent_positions(closed: pd.DataFrame, limit: int = RECENT_POSITIONS_LIMIT) -> list:
    """Return the most recent N closed positions, compact format."""
    if closed.empty:
        return []

    recent = closed.nlargest(limit, 'Close Date')
    records = []
    for _, row in recent.iterrows():
        records.append({
            'name':       str(row['Action']),
            'type':       str(row['Type']),
            'amount_usd': round(float(row['Amount']), 2),
            'profit_usd': round(float(row['Profit(USD)']), 2),
            'open_date':  row['Open Date'].strftime('%Y-%m-%d') if pd.notna(row['Open Date']) else '',
            'close_date': row['Close Date'].strftime('%Y-%m-%d') if pd.notna(row['Close Date']) else '',
            'hold_days':  int(row['hold_days']) if pd.notna(row['hold_days']) else 0,
        })
    return records


# ── Gist integration ──────────────────────────────────────────────────────────

def import_to_gist(filepath: str) -> bool:
    """
    Parse the Excel file and save the history to the Gist.

    Args:
        filepath: Path to the eToro Excel file

    Returns:
        True if saved successfully
    """
    if not GIST_AVAILABLE:
        print("❌ gist_storage not available, cannot save")
        return False

    history = parse_excel(filepath)

    data = gist_storage.load_data()
    data['etoro_history'] = history
    ok = gist_storage.save_data(data)

    if ok:
        print("✅ eToro history saved to Gist")
    else:
        print("❌ Failed to save eToro history to Gist")
    return ok


def get_history_from_gist() -> dict:
    """
    Load the stored eToro history from Gist.

    Returns:
        dict with history data, or empty dict if not present
    """
    if not GIST_AVAILABLE:
        return {}
    data = gist_storage.load_data()
    return data.get('etoro_history', {})


def get_stats_summary_text(history: dict) -> str:
    """
    Return a short human-readable summary of the eToro history stats.
    Used as context for Gemini prompts.

    Args:
        history: dict from get_history_from_gist()

    Returns:
        str: compact stats text
    """
    if not history:
        return ""

    stats = history.get('stats', {})
    period = history.get('period', {})
    fin = history.get('financial_summary', {})

    pnl_by_year = stats.get('pnl_by_year', {})
    year_lines = ', '.join(
        f"{y}: {'+'if v>=0 else ''}{v:.0f}$"
        for y, v in sorted(pnl_by_year.items())
    )

    best = stats.get('best_trades', [{}])[0]
    worst = stats.get('worst_trades', [{}])[0]

    lines = [
        f"Period: {period.get('from','?')} → {period.get('to','?')}",
        f"Total trades: {stats.get('total_trades','?')} | Win rate: {stats.get('win_rate','?')}%",
        f"Avg hold: {stats.get('avg_hold_days','?')} days | Median: {stats.get('median_hold_days','?')} days",
        f"Total P&L: ${stats.get('total_pnl_usd','?'):.2f}",
        f"P&L by year: {year_lines}",
        f"Deposits: ${stats.get('total_deposits_usd','?'):.2f} | Dividends: ${stats.get('total_dividends_usd','?'):.2f}",
        f"Best trade: {best.get('name','?')} +${best.get('profit_usd',0):.2f} ({best.get('close_date','?')})",
        f"Worst trade: {worst.get('name','?')} ${worst.get('profit_usd',0):.2f} ({worst.get('close_date','?')})",
    ]
    return '\n'.join(lines)


def get_recent_closes_text(history: dict, days: int = 30) -> str:
    """
    Return a text summary of positions closed in the last N days.
    Used to generate "decision posts".

    Args:
        history: dict from get_history_from_gist()
        days: look-back window in days

    Returns:
        str: summary of recent closures
    """
    recent = history.get('recent_positions', [])
    if not recent:
        return ""

    cutoff = (datetime.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    filtered = [p for p in recent if p.get('close_date', '') >= cutoff]

    if not filtered:
        # Fall back to last 5 regardless of date
        filtered = recent[:5]

    lines = []
    for pos in filtered:
        sign   = '+' if pos['profit_usd'] >= 0 else ''
        lines.append(
            f"- {pos['name']} ({pos['type']}): "
            f"${pos['amount_usd']:.0f} invested, "
            f"{sign}${pos['profit_usd']:.2f} P&L, "
            f"held {pos['hold_days']} days "
            f"(closed {pos['close_date']})"
        )
    return '\n'.join(lines)
