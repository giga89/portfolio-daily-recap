"""
Fetch stock data from Yahoo Finance using yfinance
"""

import yfinance as yf
from config import PORTFOLIO_TICKERS


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
