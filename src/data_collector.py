#!/usr/bin/env python3
"""
Daily Portfolio Recap Generator - Main Orchestrator
Collects data from yfinance and Google Sheets to generate daily performance recap
"""

import os
from yfinance_fetcher import fetch_stock_data, calculate_portfolio_daily_change
from sheets_fetcher import fetch_google_sheets_data
from formatter import generate_recap


def main():
    """
    Main function to orchestrate data collection and recap generation
    """
    print("Starting daily portfolio recap generation...")
    print("=" * 50)
    
    # Step 1: Get yfinance data for all symbols
    stock_data = fetch_stock_data()
    print(f"Successfully fetched data for {len(stock_data)} symbols")
    print("=" * 50)
    
    # Step 2: Calculate portfolio daily performance
    portfolio_daily = calculate_portfolio_daily_change(stock_data)
    print(f"Portfolio daily performance: {portfolio_daily:+.2f}%")
    print("=" * 50)
    
    # Step 3: Get data from Google Sheets
    sheets_data = fetch_google_sheets_data()
    print("=" * 50)
    
    # Step 4: Generate formatted recap
    recap = generate_recap(stock_data, portfolio_daily, sheets_data)
    
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


if __name__ == "__main__":
    main()
