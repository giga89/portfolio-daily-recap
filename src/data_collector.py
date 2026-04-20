#!/usr/bin/env python3
"""
Daily Portfolio Recap Generator - Main Orchestrator
Collects data from yfinance and Google Sheets to generate daily performance recap
"""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.dirname(__file__))

import finance_fetcher
from sheets_fetcher import update_google_sheets_cell, fetch_google_sheets_data, fetch_historical_from_sheets, append_historical_data, update_historical_data, seed_historical_data
import sheets_fetcher
import formatter
import telegram_sender
import chart_generator

def main():
    """
    Main function to orchestrate data collection and recap generation
    """
    
    print("Starting daily portfolio recap generation...~")
    print("=" * 50)
    
    # Step 1: Get yfinance data for all symbols
    stock_data = finance_fetcher.fetch_stock_data()
    print(f"Successfully fetched data for {len(stock_data)} symbols")
    print("=" * 50)
    
    # Step 2: Calculate portfolio daily performance (will auto-fetch weights from BullAware)
    # We fetch weights once to reuse them for both Daily and YTD calculations
    print("📊 Fetching portfolio weights...")
    portfolio_weights = finance_fetcher.fetch_portfolio_weights_from_bullaware()
    
    portfolio_daily = finance_fetcher.calculate_portfolio_daily_change(stock_data, portfolio_weights)
    print(f"Portfolio daily performance: {portfolio_daily:.2f}%")
    print("=" * 50)
    
    # Step 2b: Get reliable Portfolio YTD (Annual Yield) from eToro public API
    # Data comes directly from eToro's stats page - no auth required
    print("📈 Fetching Portfolio YTD from eToro...")
    portfolio_ytd = finance_fetcher.fetch_portfolio_ytd_from_etoro()
    
    # Fallback to calculated YTD if BullAware fails
    if portfolio_ytd is None:
        print("⚠️ Falling back to calculated YTD from market data...")
        portfolio_ytd = finance_fetcher.calculate_portfolio_ytd(stock_data, portfolio_weights)
    
    # Step 2c: Update Google Sheets with the new YTD value
    from config import YEARLY_PERFORMANCE_CELL
    sheets_fetcher.update_google_sheets_cell(YEARLY_PERFORMANCE_CELL, portfolio_ytd)
    print("=" * 50)
    
    # Step 3: Get data from Google Sheets
    sheets_data = sheets_fetcher.fetch_google_sheets_data()
    print("=" * 50)
    
    # Step 4: Get benchmark comparison data
    benchmark_data = finance_fetcher.fetch_benchmarks_performance(start_date='2020-01-01')
    print("=" * 50)
    
    # Step 4b: Calculate weekly/monthly performance if needed
    market_session = os.getenv('MARKET_SESSION', 'Daily recap')
    is_weekly = "WEEKLY" in market_session.upper()
    is_monthly = "MONTHLY" in market_session.upper()
    
    portfolio_weekly = None
    portfolio_monthly = None
    
    if is_weekly:
        print("📊 Calculating WEEKLY portfolio performance...")
        portfolio_weekly = finance_fetcher.calculate_portfolio_weighted_change(stock_data, portfolio_weights, metric='weekly_change')
        print("=" * 50)
    
    if is_monthly:
        print("📊 Calculating MONTHLY portfolio performance...")
        portfolio_monthly = finance_fetcher.calculate_portfolio_weighted_change(stock_data, portfolio_weights, metric='monthly_change')
        print("=" * 50)
    
    
    # Step 5: Generate Performance Chart (New Feature)
    print("📈 Generating performance comparison chart...")
    chart_path = None
    ath_distance = 0.0
    try:
        # Fetch history from Google Sheets
        import pandas as pd
        port_hist = fetch_historical_from_sheets()
        current_perf = sheets_data.get('five_year_return', 156.0)
        
        # If not present or too little, populate it from eToro first
        if port_hist is None or len(port_hist) < 2:
            print("   ⚠️ No rich history found in Sheets, pulling 2020+ from eToro to seed...")
            port_hist_etoro = finance_fetcher.fetch_portfolio_history_from_etoro(start_year=2020)
            
            # Populate the newly created sheet with the eToro historical monthly data
            if port_hist_etoro is not None and not port_hist_etoro.empty:
                max_so_far = -999.0
                rows_to_seed = []
                for index, current_cum in port_hist_etoro.items():
                    if current_cum > max_so_far:
                        max_so_far = current_cum
                    rows_to_seed.append([index.strftime('%Y-%m-%d'), current_cum, max_so_far])
                
                seed_historical_data(rows_to_seed)
                # Re-fetch from sheets to format properly
                port_hist = fetch_historical_from_sheets()
        
        ath_value = current_perf
        if port_hist is not None and not port_hist.empty:
            max_hist_perf = port_hist['Performance'].max()
            ath_value = float(max(max_hist_perf, current_perf))
            current_perf_float = float(current_perf)

            # Upsert today's snapshot: update if already present, append if not.
            today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
            today_mask = port_hist['Date'].dt.strftime('%Y-%m-%d') == today_str
            if today_mask.any():
                # Use the last occurrence (handles pre-existing duplicates)
                row_idx = int(port_hist.index[today_mask][-1])
                sheet_row = row_idx + 2  # +1 for 1-based, +1 for header row
                update_historical_data(sheet_row, today_str, current_perf_float, ath_value)
            else:
                append_historical_data(today_str, current_perf_float, ath_value)
            
            # Reprepare for charts — deduplicate dates (keep last) then index by Date
            port_hist = port_hist.drop_duplicates(subset='Date', keep='last')
            port_hist.set_index('Date', inplace=True)
            port_series = port_hist['Performance']
            
            # Note: Do not divide by 100 since formatting expects percentages!
            
            bench_hist = finance_fetcher.fetch_benchmarks_history(start_date='2020-01-01')
            if not bench_hist.empty:
                chart_path = chart_generator.generate_performance_chart(port_series, bench_hist)
                
            ath_distance = current_perf_float - ath_value
            if ath_distance >= 0: ath_distance = 0.0 # Safety check / New ATH
            print(f"📊 Calculated ATH Distance: {ath_distance:.2f}% (ATH: {ath_value:.2f}%, Current: {current_perf_float:.2f}%)")
        else:
            print("⚠️ Skipping chart generation due to missing data")
            
    except Exception as e:
        print(f"❌ Error generating chart: {e}")
        import traceback
        traceback.print_exc()

    # Step 6: Generate formatted recap
    recap = formatter.generate_recap(
        stock_data, 
        portfolio_daily, 
        sheets_data, 
        benchmark_data, 
        portfolio_weekly=portfolio_weekly,
        portfolio_monthly=portfolio_monthly,
        ath_distance=ath_distance
    )
    
    # Step 7: Save to file
    os.makedirs('output', exist_ok=True)
    output_path = 'output/recap.txt'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(recap)
    
    print(f"Recap saved to {output_path}")
    print("=" * 50)
    print("RECAP OUTPUT:")
    print("=" * 50)
    print(recap)
    print("=" * 50)
    print("Daily portfolio recap generation completed successfully!")

    # Step 7: Send to Telegram
    print("=" * 50)
    print("Sending recap to Telegram...")
    telegram_sender.send_recap_to_telegram(output_path, image_path=chart_path)
    print("=" * 50)

if __name__ == '__main__':
    main()
