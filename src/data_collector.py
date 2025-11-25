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
    portfolio_daily = finance_fetcher.calculate_portfolio_daily_change(stock_data)
    print(f"Portfolio daily performance: {portfolio_daily:.2f}%")
    print("=" * 50)
    
    # Step 3: Get data from Google Sheets
    sheets_data = sheets_fetcher.fetch_google_sheets_data()
    print("=" * 50)
    
    # Step 4: Generate formatted recap
    recap = formatter.generate_recap(stock_data, portfolio_daily, sheets_data)
    
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
