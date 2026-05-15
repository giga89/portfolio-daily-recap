#!/usr/bin/env python3
"""
Import eToro History
Standalone script to parse an eToro account statement Excel file and store it in the Gist.
Run this whenever you download a fresh statement from eToro.

Usage:
    python scripts/import_etoro_history.py path/to/etoro-account-statement.xlsx
    python scripts/import_etoro_history.py  # uses default path in project root
"""

import os
import sys
import glob

# Add src to path so we can import our modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

import etoro_history


def find_latest_excel(search_dir: str) -> str:
    """Find the most recently modified eToro Excel file in a directory."""
    pattern = os.path.join(search_dir, 'etoro-account-statement*.xlsx')
    matches = glob.glob(pattern)
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


def print_summary(history: dict) -> None:
    """Print a human-readable summary of the imported history."""
    stats = history.get('stats', {})
    period = history.get('period', {})
    fin = history.get('financial_summary', {})

    print()
    print('=' * 55)
    print('  ETORO HISTORY IMPORT SUMMARY')
    print('=' * 55)
    print(f"  Period: {period.get('from','?')} → {period.get('to','?')}")
    print(f"  Imported on: {history.get('import_date','?')}")
    print()
    print('  TRADING STATS:')
    print(f"    Total trades : {stats.get('total_trades','?')}")
    print(f"    Win rate     : {stats.get('win_rate','?')}%")
    print(f"    Avg hold     : {stats.get('avg_hold_days','?')} days")
    print(f"    Median hold  : {stats.get('median_hold_days','?')} days")
    print()
    print('  P&L BREAKDOWN:')
    for asset_type, pnl in stats.get('pnl_by_type', {}).items():
        sign = '+' if pnl >= 0 else ''
        print(f"    {asset_type:<10}: {sign}${pnl:.2f}")
    print(f"    {'TOTAL':<10}: +${stats.get('total_pnl_usd', 0):.2f}")
    print()
    print('  P&L BY YEAR:')
    for year, pnl in sorted(stats.get('pnl_by_year', {}).items()):
        sign = '+' if pnl >= 0 else ''
        bar = '█' * min(int(abs(pnl) / 100), 20)
        print(f"    {year}: {sign}${pnl:.0f}  {bar}")
    print()
    print('  TOP 5 BEST TRADES:')
    for t in stats.get('best_trades', [])[:5]:
        print(f"    +${t['profit_usd']:.2f}  {t['name'][:35]} ({t['close_date']})")
    print()
    print('  TOP 5 WORST TRADES:')
    for t in stats.get('worst_trades', [])[:5]:
        print(f"    ${t['profit_usd']:.2f}  {t['name'][:35]} ({t['close_date']})")
    print()
    print(f"  Deposits:  ${stats.get('total_deposits_usd', 0):.2f}")
    print(f"  Dividends: ${stats.get('total_dividends_usd', 0):.2f}")
    print()
    print(f"  Recent positions stored: {len(history.get('recent_positions', []))}")
    print('=' * 55)
    print()


def main():
    # Determine Excel file path
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        # Auto-discover in project root
        filepath = find_latest_excel(PROJECT_ROOT)
        if filepath:
            print(f"Auto-discovered Excel file: {filepath}")
        else:
            print("No eToro Excel file found.")
            print("Usage: python scripts/import_etoro_history.py path/to/etoro-account-statement.xlsx")
            sys.exit(1)

    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)

    # Parse
    try:
        history = etoro_history.parse_excel(filepath)
    except Exception as exc:
        print(f"Failed to parse Excel: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Print summary
    print_summary(history)

    # Save to Gist
    print("Saving to Gist...")
    ok = etoro_history.import_to_gist(filepath)

    if ok:
        print("Import completed successfully.")
        print("The eToro history is now stored in your Gist and will be used for:")
        print("  - Decision posts (generated every Monday)")
        print("  - P&L history pie chart")
        print("  - Stats context for Gemini prompts")
    else:
        print("Gist save failed. Check your GIST_ACCESS_TOKEN / GIST_ID environment variables.")
        print("The parsed data is shown above but was NOT persisted.")
        sys.exit(1)


if __name__ == '__main__':
    main()
