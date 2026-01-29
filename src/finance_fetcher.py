"""
Fetch stock data from Yahoo Finance using yfinance
"""

import yfinance as yf
from config import PORTFOLIO_TICKERS, BENCHMARKS
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
    Fetch portfolio aggregate YTD from BullAware by compounding monthly returns
    found in the highly reliable JSON data embedded in the page.
    """
    try:
        url = "https://bullaware.com/etoro/AndreaRavalli"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Simple retry loop
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"   Values fetch attempt {attempt+1}/{max_retries}...")
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                break # Success
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e # Re-raise on last attempt
                print(f"   ⚠️ Timeout or error, retrying: {e}")
                import time
                time.sleep(2) # Wait a bit before retry

        content = response.text
        
        # 1. Try to find the monthly returns block
        # The block usually contains contiguous months like "2025-1":3.59,"2025-2":-2.47...
        current_year = datetime.now().year
        # Search for the block starting with January of the current year
        block_pattern = rf'\\?["\']{current_year}-1\\?["\']:\s*[+-]?\d+\.?\d*.*?[}}]'
        match_block = re.search(block_pattern, content)
        
        if match_block:
            block_content = match_block.group(0)
            # Now extract all months from this specific block
            monthly_pattern = rf'\\?["\']{current_year}-(\d+)\\?["\']:\s*([+-]?\d+\.?\d*)'
            matches = re.findall(monthly_pattern, block_content)
            
            if matches:
                # Sort by month index (1 to 12)
                monthly_data = sorted([(int(m), float(v)) for m, v in matches], key=lambda x: x[0])
                print(f"   Found {len(monthly_data)} months of data for {current_year}")
                
                # Compound the monthly returns
                compounded_return = 1.0
                for month, return_val in monthly_data:
                    compounded_return *= (1 + (return_val / 100.0))
                
                ytd_value = (compounded_return - 1.0) * 100.0
                print(f"✓ Calculated BullAware portfolio YTD (compounded): {ytd_value:.2f}%")
                return ytd_value
            
        # 2. Fallback to direct "Year to Date" string
        ytd_pattern = r'Year to Date.*?([+-]?\d+\.?\d*)<!-- -->%'
        match = re.search(ytd_pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            ytd_value = float(match.group(1))
            print(f"✓ Found BullAware portfolio YTD (regex): {ytd_value}%")
            return ytd_value
            
        print("Could not find portfolio YTD in BullAware page")
        return None
        
    except Exception as e:
        print(f"BullAware portfolio YTD fetch error: {e}")
        return None


def calculate_portfolio_ytd(stock_data, portfolio_weights=None):
    """
    Calculate overall portfolio YTD performance as WEIGHTED average
    
    Args:
        stock_data: dict with stock data including 'yearly_change' for each ticker
        portfolio_weights: dict with {ticker: weight_percentage}
    
    Returns:
        float: weighted portfolio YTD performance as percentage
    """
    if not stock_data:
        return 0.0
        
    # Fetch fresh weights from BullAware if not provided
    if portfolio_weights is None:
        portfolio_weights = fetch_portfolio_weights_from_bullaware()
        
    if not portfolio_weights:
        print("⚠️ No portfolio weights available for YTD calculation. Using equal weight fallback.")
        total = sum(data['yearly_change'] for data in stock_data.values())
        return total / len(stock_data)
        
    weighted_sum = 0.0
    total_weight = 0.0
    
    for ticker, data in stock_data.items():
        if ticker in portfolio_weights:
            weight = portfolio_weights[ticker] / 100.0
            weighted_sum += data['yearly_change'] * weight
            total_weight += weight
            
    if total_weight == 0:
        return 0.0
        
    print(f"📊 Calculated Portfolio YTD: {weighted_sum:.2f}%")
    return weighted_sum


def fetch_portfolio_weights_from_bullaware():
    """
    Fetch individual stock/ETF portfolio weights from BullAware using direct HTTP and Regex.
    Extracts the 'positions' JSON data embedded in the Next.js page.
    Returns dict with {ticker: weight_percentage}
    """
    print("📊 Fetching portfolio weights from BullAware...")
    
    try:
        url = "https://bullaware.com/etoro/AndreaRavalli"
        # Mimic a browser to avoid potential blocking (though usually not needed for public pages)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Simple retry loop for weights
        max_retries = 3
        response = None
        
        for attempt in range(max_retries):
            try:
                print(f"   Weights fetch attempt {attempt+1}/{max_retries}...")
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                break # Success
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    print(f"❌ Failed to fetch after {max_retries} attempts: {e}")
                    return {}
                print(f"   ⚠️ Timeout or error, retrying: {e}")
                import time
                time.sleep(2)

        content = response.text
        
        # Regex to find the "positions" array in the JSON structure
        # The JSON is often inside a JS string, so quotes might be escaped as \"
        # We handle both "positions" and \"positions\"
        # We also handle the following comma and "copies" or \"copies\"
        pattern = r'\\?"positions\\?":\s*(\[.*?\]),\s*\\?"copies'
        
        match = re.search(pattern, content)
        if not match:
             # Fallback: maybe copies is not after?
             pattern = r'\\?"positions\\?":\s*(\[\{.*?\}\])'
             match = re.search(pattern, content)
        
        if match:
            positions_json = match.group(1)
            # If the extracted string contains escaped quotes like \", we need to unescape them
            # because json.loads expects standard quotes "".
            # However, usually json.loads can't handle \" unless it's a string value.
            # But here we extracted the *list* string: [{\"symbol\":\"TRX\"...}]
            # If we just pass this to json.loads, it will fail if it has \" keys.
            # We can try to replace \" with " globally in the string if it looks escaped.
            if '\\"' in positions_json:
                positions_json = positions_json.replace('\\"', '"')
                
            try:
                positions = json.loads(positions_json)
                
                weights = {}
                for pos in positions:
                    symbol = pos.get('symbol')
                    value = pos.get('value') # This represents the portfolio allocation percentage (0-100)
                    
                    if symbol and value is not None:
                        # Ensure value is treated as a float
                        try:
                            weight = float(value)
                            # Sanity check: weight should be between 0 and 100
                            if 0 < weight <= 100:
                                weights[symbol] = weight
                        except ValueError:
                            continue
                            
                if weights:
                    print(f"✓ Successfully extracted {len(weights)} portfolio weights")
                    
                    # Sort by weight descending for logging
                    sorted_weights = dict(sorted(weights.items(), key=lambda x: x[1], reverse=True))
                    for ticker, weight in list(sorted_weights.items())[:5]:
                        print(f"   {ticker}: {weight:.2f}%")
                    if len(sorted_weights) > 5:
                        print(f"   ... and {len(sorted_weights) - 5} more")
                        
                    return weights
                else:
                     print("⚠️ Valid positions JSON found but no valid weights extracted")
            
            except json.JSONDecodeError as e:
                print(f"❌ Error extracting JSON from regex match: {e}")
        else:
            print("❌ Could not find 'positions' JSON block in BullAware page source")
            # Debug: save content to file if needed
            # with open("bullaware_debug.html", "w") as f: f.write(content)

        return {}

    except Exception as e:
        print(f"⚠️ Could not fetch portfolio weights from BullAware: {e}")
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
                'weekly_change': 0.0,
                'monthly_change': monthly_change,
                'yearly_change': yearly_change
            }

            # Calculate weekly change (last 5 trading days)
            if len(hist) >= 5:
                current = hist['Close'].iloc[-1]
                week_ago = hist['Close'].iloc[-5]
                weekly_change = ((current - week_ago) / week_ago) * 100
                stock_data[etoro_symbol]['weekly_change'] = weekly_change
            else:
                 stock_data[etoro_symbol]['weekly_change'] = 0.0
            
            print(f"{etoro_symbol} ({yahoo_ticker}): Daily {daily_change:.2f}%, Monthly {monthly_change:.2f}%, Yearly {yearly_change:.2f}%")
            
        except Exception as e:
            print(f"Error fetching data for {etoro_symbol} ({yahoo_ticker}): {e}")
            continue
    
    return stock_data



def calculate_portfolio_daily_change(stock_data, portfolio_weights=None):
    """
    Wrapper for backward compatibility. Calculates weighted daily change.
    """
    return calculate_portfolio_weighted_change(stock_data, portfolio_weights, metric='daily_change')


def calculate_portfolio_weighted_change(stock_data, portfolio_weights=None, metric='daily_change'):
    """
    Calculate overall portfolio performance for a specific metric as WEIGHTED average
    
    Args:
        stock_data: dict with stock data
        portfolio_weights: dict with {ticker: weight_percentage}
        metric: string key to use from stock_data (e.g. 'daily_change', 'weekly_change')
    
    Returns:
        float: weighted portfolio performance as percentage
    """
    if not stock_data:
        return 0.0
    # Fetch fresh weights from BullAware if not provided
    if portfolio_weights is None:
        portfolio_weights = fetch_portfolio_weights_from_bullaware()
    
    # If still no weights, fallback to equal weights with warning
    if not portfolio_weights:
        print("⚠️  No portfolio weights available. Using equal weight fallback.")
        total = sum(data[metric] for data in stock_data.values())
        return total / len(stock_data)

    # AUTO-SYNC: Update local config based on fetched weights
    try:
        from portfolio_manager import sync_portfolio
        # Update JSON config (add new, remove old)
        port_tickers = sync_portfolio(portfolio_weights)
        
        # RELOAD CONFIG: Update the global variable in config module so subsequent calls use it
        import config
        config.PORTFOLIO_TICKERS = port_tickers
        
    except Exception as e:
        print(f"Error during portfolio sync: {e}")
    
    # Calculate weighted average
    weighted_sum = 0.0
    total_weight = 0.0
    missing_weights = []
    
    for ticker, data in stock_data.items():
        if ticker in portfolio_weights:
            weight = portfolio_weights[ticker] / 100.0  # Convert percentage to decimal
            weighted_sum += data[metric] * weight
            total_weight += weight
        else:
            missing_weights.append(ticker)
    
    if missing_weights:
        print(f"⚠️  No weights found for: {', '.join(missing_weights)}")
        print("   These positions are excluded from the weighted calculation")
    
    if total_weight == 0:
        print("⚠️  Total weight is zero. Using equal weight fallback.")
        total = sum(data[metric] for data in stock_data.values())
        return total / len(stock_data)
    
    # Calculate weighted performance
    weighted_performance = weighted_sum
    
    print(f"📊 Weighted Portfolio {metric} Change: {weighted_performance:.2f}%")
    
    return weighted_performance



def fetch_benchmarks_performance(start_date='2020-01-01'):
    """
    Fetch historical performance for benchmarks starting from a specific date.
    Returns a dictionary of cumulative returns for each benchmark.
    """
    print(f"📈 Fetching benchmark performance since {start_date}...")
    bench_data = {}
    
    for etoro_ticker, yahoo_ticker in BENCHMARKS.items():
        try:
            stock = yf.Ticker(yahoo_ticker)
            # Fetch historical data
            hist = stock.history(start=start_date)
            
            if not hist.empty:
                start_price = hist['Close'].iloc[0]
                current_price = hist['Close'].iloc[-1]
                total_return = ((current_price - start_price) / start_price) * 100
                bench_data[etoro_ticker] = total_return
                print(f"   {etoro_ticker}: {total_return:+.2f}%")
            else:
                print(f"   ⚠️ No data for {etoro_ticker} ({yahoo_ticker})")
                
        except Exception as e:
            print(f"   ❌ Error fetching benchmark {etoro_ticker}: {e}")
            
    return bench_data