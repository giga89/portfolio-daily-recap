"""
Fetch stock data from Yahoo Finance using yfinance
"""
import yfinance as yf
from config import PORTFOLIO_TICKERS
import requests
from bs4 import BeautifulSoup
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


def fetch_bullaware_data_selenium(etoro_symbol):
    """
    Fetch YTD data from BullAware using Selenium
    Clicks on Time Period dropdown and selects Year to Date for treemap
    Returns dict with 'yearly_change' or None if failed
    """
    driver = None
    try:
        # Setup headless Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to BullAware portfolio page
        url = "https://bullaware.com/etoro/AndreaRavalli"
        print(f"Loading BullAware for {etoro_symbol}...")
        driver.get(url)
        
        # Wait for page to load completely
        time.sleep(6)
        
        # Click on "Time Period" dropdown to open the menu
        try:
            # Find the dropdown button by text content
            dropdown_btn = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Time Period')]"))
            )
            dropdown_btn.click()
            print("Clicked on Time Period dropdown")
            time.sleep(1)
            
            # Click on "Year to Date" option in the menu
            ytd_option = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Year to Date')]"))
            )
            ytd_option.click()
            print("Selected Year to Date from dropdown")
            time.sleep(3)  # Wait for treemap to update with YTD data
            
        except Exception as e:
            print(f"Could not switch to YTD view: {e}")
            # Continue anyway - might already be on YTD or we'll try to scrape current view
        
        # Get page source after interaction
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Strategy 1: Find symbol in text and get percentage from next lines
        page_text = soup.get_text()
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        
        for i, line in enumerate(lines):
            # Exact match for symbol (case-insensitive)
            if line.upper() == etoro_symbol.upper():
                # Look for percentage in next 5 lines
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j]
                    # Match standalone percentage (YTD value)
                    if re.match(r'^-?\d+\.?\d*%$', next_line):
                        ytd_str = next_line.rstrip('%')
                        ytd_value = float(ytd_str)
                        print(f"✓ Found BullAware YTD for {etoro_symbol}: {ytd_value}%")
                        return {'yearly_change': ytd_value}
        
        # Strategy 2: Search for symbol in elements and find nearby percentage
        all_elements = soup.find_all(text=re.compile(etoro_symbol, re.IGNORECASE))
        for elem in all_elements:
            parent = elem.parent
            if parent:
                # Get all text from parent and siblings
                parent_text = parent.get_text(strip=True)
                # Look for percentage right after symbol
                pattern = rf'{re.escape(etoro_symbol)}[^\d\-]*(-?\d+\.?\d*)%'
                match = re.search(pattern, parent_text, re.IGNORECASE)
                if match:
                    ytd_value = float(match.group(1))
                    print(f"✓ Found BullAware YTD for {etoro_symbol}: {ytd_value}% (from parent)")
                    return {'yearly_change': ytd_value}
        
        print(f"Could not find YTD for {etoro_symbol} in BullAware treemap")
        
    except Exception as e:
        print(f"BullAware Selenium error for {etoro_symbol}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
    
    return None

def fetch_stock_data():
    """
    Get stock data from yfinance for all symbols
    Returns daily, monthly, and yearly performance
    
    Logic:
    - Daily: For US stocks, only use during 16:00 and 22:00 sessions
    - Monthly: Always use for all stocks
    - Yearly (YTD): Always use for all stocks, with BullAware Selenium fallback if ~0
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
            
            # Fallback to BullAware Selenium if yearly change is zero or very close to zero
            # This applies to ALL stocks (US and non-US)
            # IMPORTANT: Get individual stock YTD, not portfolio YTD
            if abs(yearly_change) < 0.01:
                print(f"YTD for {etoro_symbol} is ~0, trying BullAware Selenium fallback...")
                bullaware_data = fetch_bullaware_data_selenium(etoro_symbol)
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
