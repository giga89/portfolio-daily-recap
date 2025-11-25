"""
Fetch stock data from Yahoo Finance using yfinance
"""
import yfinance as yf
from config import PORTFOLIO_TICKERS
import requests
from bs4 import BeautifulSoup
import os
import re

def fetch_bullaware_data(etoro_symbol):
    """
    Fetch YTD data from BullAware web page by scraping the treemap
    Returns dict with 'yearly_change' or None if failed
    """
    try:
        # BullAware portfolio page
        url = "https://bullaware.com/etoro/AndreaRavalli"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all text content in the page
            page_text = soup.get_text()
            
            # Look for the symbol followed by a percentage
            # Pattern: Symbol name followed by percentage (e.g., "PLTR 140.88%" or "PLTR\n140.88%")
            pattern = rf'{re.escape(etoro_symbol)}[\s\n]+(-?\d+\.?\d*)%'
            match = re.search(pattern, page_text, re.IGNORECASE)
            
            if match:
                ytd_value = float(match.group(1))
                print(f"Found BullAware YTD for {etoro_symbol}: {ytd_value}%")
                return {'yearly_change': ytd_value}
            
            # Alternative: try to find just the percentage near the symbol
            # Split text and look for symbol + percentage pattern
            lines = page_text.split('\n')
            for i, line in enumerate(lines):
                if etoro_symbol in line:
                    # Check current line and next few lines for percentage
                    for j in range(i, min(i + 5, len(lines))):
                        perc_match = re.search(r'(-?\d+\.?\d*)%', lines[j])
                        if perc_match:
                            ytd_value = float(perc_match.group(1))
                            print(f"Found BullAware YTD for {etoro_symbol}: {ytd_value}%")
                            return {'yearly_change': ytd_value}
    
    except Exception as e:
        print(f"BullAware scraping error for {etoro_symbol}: {e}")
    
    return None

def fetch_stock_data():
    """
    Get stock data from yfinance for all symbols
    Returns daily, monthly, and yearly performance
    
    Logic:
    - Daily: For US stocks, only use during 16:00 and 22:00 sessions
    - Monthly: Always use for all stocks
    - Yearly (YTD): Always use for all stocks, with BullAware fallback if ~0
    """
    print(f"Fetching yfinance data for {len(PORTFOLIO_TICKERS)} symbols...")
    
    stock_data = {}
    
    # Get market session from environment (16:00 or 22:00)
    market_session = os.getenv('MARKET_SESSION', 'Daily recap')
    is_us_session = market_session in ['16:00', '22:00']
    
    print(f"Market session: {market_session}, US session active: {is_us_session}")
    
    # US exchanges
    us_exchanges = ['NASDAQ', 'NYSE', 'AMEX', 'NMS', 'NYQ', 'NAS']
    
    for etoro_symbol, (yahoo_ticker, company_name) in PORTFOLIO_TICKERS.items():
        try:
            # Download historical data
            ticker = yf.Ticker(yahoo_ticker)
            
            # Get 1 year of data to calculate all periods
            hist = ticker.history(period='1y')
            
            if len(hist) < 2:
                print(f"Insufficient data for {etoro_symbol} ({yahoo_ticker})")
                continue
            
            # Current price
            current_price = hist['Close'].iloc[-1]
            
            # Determine if this is a US stock
            try:
                info = ticker.info
                exchange = info.get('exchange', '')
                is_us_stock = exchange in us_exchanges
            except:
                # If we can't get info, assume non-US for safety
                is_us_stock = False
                print(f"Could not determine exchange for {etoro_symbol}, assuming non-US")
            
            # Daily change (today vs yesterday)
            # ONLY skip for US stocks outside 16:00/22:00 sessions
            if is_us_stock and not is_us_session:
                daily_change = 0.0
                print(f"⏸ Skipping daily for US stock {etoro_symbol} ({exchange}) - market not yet closed")
            elif len(hist) >= 2:
                yesterday_price = hist['Close'].iloc[-2]
                daily_change = ((current_price - yesterday_price) / yesterday_price) * 100
            else:
                daily_change = 0.0
            
            # Monthly change (last 30 days) - ALWAYS calculate
            if len(hist) >= 30:
                month_ago_price = hist['Close'].iloc[-30]
                monthly_change = ((current_price - month_ago_price) / month_ago_price) * 100
            else:
                monthly_change = 0.0
            
            # Yearly change (last 252 trading days) - ALWAYS calculate
            # YTD applies to ALL stocks regardless of session time
            if len(hist) >= 252:
                year_ago_price = hist['Close'].iloc[-252]
                yearly_change = ((current_price - year_ago_price) / year_ago_price) * 100
            else:
                yearly_change = 0.0
            
            # Fallback to BullAware if yearly change is zero or very close to zero
            # This applies to ALL stocks (US and non-US)
            if abs(yearly_change) < 0.01:
                print(f"YTD for {etoro_symbol} is ~0, trying BullAware fallback...")
                bullaware_data = fetch_bullaware_data(etoro_symbol)
                if bullaware_data and abs(bullaware_data['yearly_change']) > 0.01:
                    yearly_change = bullaware_data['yearly_change']
                    print(f"✓ Using BullAware YTD for {etoro_symbol}: {yearly_change:.2f}%")
            
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

def calculate_portfolio_daily_change(stock_data):
    """
    Calculate overall portfolio daily performance as simple average
    """
    if not stock_data:
        return 0.0
    
    total = sum(data['daily_change'] for data in stock_data.values())
    return total / len(stock_data)
