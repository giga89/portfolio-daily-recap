"""
Fetch stock data from Yahoo Finance using yfinance
"""

import yfinance as yf
from config import PORTFOLIO_TICKERS
import requests


def fetch_bullaware_data(etoro_symbol):
    """
    Fetch MTD and YTD data from BullAware API as fallback
    Returns dict with 'monthly_change' and 'yearly_change' or None if failed
    """
    try:
        # BullAware API endpoint - adjust based on actual API
        url = f"https://api.bullaware.com/v1/stocks/{etoro_symbol}/performance"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'monthly_change': data.get('mtd_change', 0.0),
                'yearly_change': data.get('ytd_change', 0.0)
            }
    except Exception as e:
        print(f"BullAware API error for {etoro_symbol}: {e}")
    
    return None


def fetch_stock_data():
    """
    Get stock data from yfinance for all symbols
    Returns daily, monthly, and yearly performance
    """
    print(f"Fetching yfinance data for {len(PORTFOLIO_TICKERS)} symbols...")
    
    stock_data = {}
    
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
            
            # Daily change (today vs yesterday)
            if len(hist) >= 2:
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
            
            # Yearly change (last 252 trading days)
            if len(hist) >= 252:
                year_ago_price = hist['Close'].iloc[-252]
                yearly_change = ((current_price - year_ago_price) / year_ago_price) * 100
            else:
                yearly_change = 0.0

                        # Fallback to BullAware if monthly or yearly change is zero
            if monthly_change == 0.0 or yearly_change == 0.0:
                bullaware_data = fetch_bullaware_data(etoro_symbol)
                if bullaware_data:
                    if monthly_change == 0.0 and bullaware_data['monthly_change'] != 0.0:
                        monthly_change = bullaware_data['monthly_change']
                        print(f"Using BullAware MTD for {etoro_symbol}: {monthly_change:.2f}%")
                    if yearly_change == 0.0 and bullaware_data['yearly_change'] != 0.0:
                        yearly_change = bullaware_data['yearly_change']
                        print(f"Using BullAware YTD for {etoro_symbol}: {yearly_change:.2f}%")
            
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
