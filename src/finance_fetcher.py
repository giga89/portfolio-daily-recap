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
        ytd_pattern = r'Year to Date[:\s]+(-?\d+\.?\d*)%'
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

def fetch_stock_data():
    """
    Get stock data from yfinance for all symbols
    Returns daily, monthly, and yearly performance
    
    Logic:
    - Daily: For US stocks, only use during 16:00 and 22:00 sessions
    - Monthly: Always use for all stocks
    - Yearly (YTD): Calculate from January 1st of current year
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
                is_us_stock = False
                print(f"Could not determine exchange for {etoro_symbol}, assuming non-US")
            
            # Daily change (today vs yesterday)
            if is_us_stock and not is_us_session:
                daily_change = 0.0
                print(f"⏸ Skipping daily for US stock {etoro_symbol} ({exchange}) - market not yet closed")
            elif len(hist) >= 2:
                yesterday_price = hist['Close'].iloc[-2]
                daily_change = ((current_price - yesterday_price) / yesterday_price) * 100
            else:
                daily_change = 0.0
            
            # Monthly change (last 30 days)
            if len(hist) >= 30:
                month_ago_price = hist['Close'].iloc[-30]
                monthly_change = ((current_price - month_ago_price) / month_ago_price) * 100
            else:
                monthly_change = 0.0
            
            # Calculate true YTD (Year to Date) - from January 1st of current year
            current_year = datetime.now().year
            ytd_start = datetime(current_year, 1, 1)
            
            try:
                # Get historical data from YTD start to now
                ytd_hist = ticker.history(start=ytd_start)
                if len(ytd_hist) >= 2:
                    ytd_start_price = ytd_hist['Close'].iloc[0]
                    yearly_change = ((current_price - ytd_start_price) / ytd_start_price) * 100
                    print(f"✓ Calculated YTD for {etoro_symbol} from {ytd_start.date()}: {yearly_change:.2f}%")
                else:
                    # Fallback to 252 trading days if YTD data not available
                    if len(hist) >= 252:
                        year_ago_price = hist['Close'].iloc[-252]
                        yearly_change = ((current_price - year_ago_price) / year_ago_price) * 100
                        print(f"ℹ Using 252-day calculation for {etoro_symbol}: {yearly_change:.2f}%")
                    else:
                        yearly_change = 0.0
            except Exception as e:
                print(f"YTD calculation error for {etoro_symbol}: {e}")
                yearly_change = 0.0
            
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
