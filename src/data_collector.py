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
    
    # Step 2b: Get reliable Portfolio YTD (Annual Yield) from BullAware
    # The user manual check at eToro stats confirms BullAware is highly accurate
    print("📈 Fetching reliable Portfolio YTD from BullAware...")
    portfolio_ytd = finance_fetcher.fetch_portfolio_ytd_from_bullaware()
    
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
    try:
        # Fetch history
        port_hist = finance_fetcher.fetch_portfolio_history_from_bullaware(start_year=2020)
        bench_hist = finance_fetcher.fetch_benchmarks_history(start_date='2020-01-01')
        
        if port_hist is not None and not bench_hist.empty:
            chart_path = chart_generator.generate_performance_chart(port_hist, bench_hist)
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
        portfolio_monthly=portfolio_monthly
    )
    
    # Step 5: Save to file
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

    # Step 6: Send to Telegram
    print("=" * 50)
    print("Sending recap to Telegram...")
    print("Sending recap to Telegram...")
    telegram_sender.send_recap_to_telegram(output_path, image_path=chart_path)
    print("=" * 50)

if __name__ == '__main__':
    main()
