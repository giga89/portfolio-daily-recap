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
    
    # Step 2b: Calculate and update manual Portfolio YTD (Annual Yield)
    print("📈 Calculating portfolio YTD (Annual Yield)...")
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
    
    # Step 5: Generate formatted recap
    recap = formatter.generate_recap(stock_data, portfolio_daily, sheets_data, benchmark_data)
    
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
    telegram_sender.send_recap_to_telegram(output_path)
    print("=" * 50)

if __name__ == '__main__':
    main()
