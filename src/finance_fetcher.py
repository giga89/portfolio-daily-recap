"""
Fetch stock data from Yahoo Finance using yfinance
"""

import yfinance as yf
from config import PORTFOLIO_TICKERS
import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime
import json
import pytz

# Fuso orario USA (New York)
NY_TZ = pytz.timezone('America/New_York')

# Orario di apertura e chiusura della borsa USA (9:30 AM a 4:00 PM ET)
US_OPEN_HOUR = 9
US_OPEN_MINUTE = 30
US_CLOSE_HOUR = 16
US_CLOSE_MINUTE = 00

def fetch_portfolio_ytd_from_bullaware():
    """
    Fetch portfolio aggregate YTD from BullAware (simple requests, no Selenium)
    Returns the overall portfolio YTD percentage for Google Sheets
    """
    try:
        url = "https://bullaware.com/etoro/AndreaRavalli"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the YTD percentage in the page
        page_text = soup.get_text()
        
        # Look for "Year to Date" or "YTD" followed by percentage
        ytd_pattern = r'Year to Date[:\s]+([+-]?\d+\.?\d*)\s*%'
        match = re.search(ytd_pattern, page_text, re.IGNORECASE)
        
        if match:
            ytd_value = float(match.group(1))
            print(f"✓ Found BullAware portfolio YTD: {ytd_value}%")
            return ytd_value
            
        print("Could not find portfolio YTD in BullAware page")
        return None
        
    except Exception as e:
        print(f"BullAware portfolio YTD fetch error: {e}")
        return None


def fetch_portfolio_weights_from_bullaware():
    """
    Fetch individual stock/ETF portfolio weights from BullAware using direct HTML parsing
    Extracts the "Portfolio Value" percentage for each instrument from the embedded JSON data
    Returns dict with {ticker: weight_percentage}
    """
    print("📊 Fetching portfolio weights from BullAware (via HTML parsing)...")
    
    try:
        url = "https://bullaware.com/etoro/AndreaRavalli"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        content = response.text
        
        # Regex to find the JSON-like objects containing symbol and value
        # Pattern covers: \"symbol\":\"PLTR\",\"value\":4.711386
        # The content in the HTML is inside a JSON string, so quotes are escaped like \"
        pattern = r'\\"symbol\\":\\"([^"]+)\\",\\"value\\":([\d.]+)'
        
        matches = re.findall(pattern, content)
        
        weights = {}
        for symbol, value in matches:
            try:
                weight = float(value)
                if weight > 0:  # Only positive weights
                    weights[symbol] = weight
            except ValueError:
                continue
                
        if weights:
            print(f"✓ Successfully fetched weights for {len(weights)} instruments")
            # Sort by weight descending for logging
            sorted_weights = dict(sorted(weights.items(), key=lambda x: x[1], reverse=True))
            for ticker, weight in list(sorted_weights.items())[:5]:
                print(f"   {ticker}: {weight}%")
            if len(sorted_weights) > 5:
                print(f"   ... and {len(sorted_weights) - 5} more")
            return weights
        else:
            print("⚠️  Could not extract weights from BullAware (no matches found)")
            return {}
            
    except Exception as e:
        print(f"⚠️  Could not fetch portfolio weights from BullAware: {e}")
        return {}


def fetch_stock_data():
    """
    Fetch daily, monthly, and YTD data for all portfolio tickers using yfinance
    """
    stock_data = {}
    
    for ticker, (yahoo_ticker, descr) in PORTFOLIO_TICKERS.items():
        yahoo_ticker = yahoo_ticker  # Use
        company_name = descr  # Default to symbol
        etoro_symbol = ticker
        
        try:
            # Fetch stock info
            stock = yf.Ticker(yahoo_ticker)
            info = stock.info
            
            # 1. Ottieni l'orario corrente a New York
            now_ny = datetime.now(NY_TZ)
            
            # 2. Determina se siamo in orario PRE-MARKET (prima delle 9:30 AM ET)
            # L'orario di apertura è fissato alle 9:30 AM ET.
            is_pre_market_hours = now_ny.hour < US_OPEN_HOUR or \
                                (now_ny.hour == US_OPEN_HOUR and now_ny.minute < US_OPEN_MINUTE)

            # Get company name
            company_name = info.get('longName', info.get('shortName', yahoo_ticker))
            
            # Get current price
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            
            # Fetch historical data for daily and monthly calculations
            hist = stock.history(period='1y')
            
            if hist.empty:
                print(f"No historical data for {etoro_symbol}")
                continue
            
            # Calculate daily change
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                previous = hist['Close'].iloc[-2]
                daily_change = ((current - previous) / previous) * 100
            else:
                daily_change = 0.0
            
            # Calculate monthly change (last 30 days)
            if len(hist) >= 30:
                current = hist['Close'].iloc[-1]
                month_ago = hist['Close'].iloc[-30]
                monthly_change = ((current - month_ago) / month_ago) * 100
            else:
                monthly_change = 0.0
            
            # Calculate YTD change (from January 1st of current year)
            current_year = datetime.now().year
            try:
                ytd_hist = stock.history(start=f'{current_year}-01-01')
                if len(ytd_hist) >= 2:
                    ytd_start = ytd_hist['Close'].iloc[0]
                    ytd_current = ytd_hist['Close'].iloc[-1]
                    yearly_change = ((ytd_current - ytd_start) / ytd_start) * 100
                else:
                    yearly_change = 0.0
            except Exception as e:
                print(f"YTD calculation error for {etoro_symbol}: {e}")
                yearly_change = 0.0
            
            exchange = info.get('exchange', '')
            us_exchanges = ['NASDAQ', 'NYSE', 'AMEX', 'NMS', 'NYQ', 'NAS']
            is_us_stock = exchange in us_exchanges

            if is_us_stock and is_pre_market_hours:
                print(f"Day not yet started for {etoro_symbol}")
                daily_change = 0.0

            stock_data[etoro_symbol] = {
                'yahoo_ticker': yahoo_ticker,
                'company_name': company_name,
                'price': current_price,
                'daily_change': daily_change,
                'monthly_change': monthly_change,
                'yearly_change': yearly_change
            }
            
            print(f"{etoro_symbol} ({yahoo_ticker}): Daily {daily_change:.2f}%, Monthly {monthly_change:.2f}%, Yearly {yearly_change:.2f}%")
            
        except Exception as e:
            print(f"Error fetching data for {etoro_symbol} ({yahoo_ticker}): {e}")
            continue
    
    return stock_data


def calculate_portfolio_daily_change(stock_data, portfolio_weights=None):
    """
    Calculate overall portfolio daily performance as WEIGHTED average
    Uses portfolio weights to properly calculate performance based on position sizes
    
    Args:
        stock_data: dict with stock data including 'daily_change' for each ticker
        portfolio_weights: dict with {ticker: weight_percentage} (e.g., {'NVDA': 3.08, 'PLTR': 0.71})
                           If None, will fetch fresh weights from BullAware
    
    Returns:
        float: weighted portfolio daily performance as percentage
    """
    if not stock_data:
        return 0.0
    # Fetch fresh weights from BullAware if not provided
    if portfolio_weights is None:
        portfolio_weights = fetch_portfolio_weights_from_bullaware()
    
    # If still no weights, fallback to equal weights with warning
    if not portfolio_weights:
        print("⚠️  No portfolio weights available. Using equal weight fallback.")
        print("   This will give INACCURATE results! Portfolio performance should be weighted by position size.")
        total = sum(data['daily_change'] for data in stock_data.values())
        return total / len(stock_data)
    
    # Calculate weighted average
    weighted_sum = 0.0
    total_weight = 0.0
    missing_weights = []
    
    for ticker, data in stock_data.items():
        if ticker in portfolio_weights:
            weight = portfolio_weights[ticker] / 100.0  # Convert percentage to decimal
            weighted_sum += data['daily_change'] * weight
            total_weight += weight
        else:
            missing_weights.append(ticker)
    
    if missing_weights:
        print(f"⚠️  No weights found for: {', '.join(missing_weights)}")
        print("   These positions are excluded from the weighted calculation")
    
    if total_weight == 0:
        print("⚠️  Total weight is zero. Using equal weight fallback.")
        total = sum(data['daily_change'] for data in stock_data.values())
        return total / len(stock_data)
    
    # Calculate weighted performance
    # We don't normalize by total_weight here because weights are already in percentage terms
    # and we want the actual portfolio daily change
    weighted_performance = weighted_sum
    
    print(f"📊 Weighted Portfolio Daily Change: {weighted_performance:.2f}% (based on {len(stock_data)} positions)")
    
    return weighted_performance