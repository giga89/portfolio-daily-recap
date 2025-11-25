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
    Fetch individual stock/ETF portfolio weights from BullAware using Selenium
    Extracts the "Portfolio Value" percentage for each instrument from the treemap/bubble view
    Returns dict with {ticker: weight_percentage}
    """
    print("📊 Fetching portfolio weights from BullAware...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        import time
        
        # Setup headless Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        # Initialize driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        weights = {}
        
        try:
            # Navigate to BullAware portfolio page
            driver.get("https://bullaware.com/etoro/AndreaRavalli")
            print("   Waiting for page to load...")
            time.sleep(5)  # Wait for dynamic content to load
            
            # The treemap/bubble elements contain the data
            # Look for elements with stock symbols and their weights
            # Based on the HTML structure we saw, find all instrument elements
            
            # Try to find elements in the treemap (they usually have specific attributes)
            page_source = driver.page_source
            
            # Extract using regex from page source (as treemap data is in JS)
            # Pattern to find ticker and portfolio value percentage
            pattern = r'"?([A-Z0-9]+\.?[A-Z]*)"?\s*:\s*"?(\d+\.?\d*)%?"?'
            
            # Also try to extract from visible text elements
            elements = driver.find_elements(By.CSS_SELECTOR, '[class*="treemap"], [class*="bubble"], [class*="portfolio"]')
            
            # Parse the visible treemap items
            treemap_items = driver.find_elements(By.XPATH, "//*[contains(text(), '%')]")
            
            for item in treemap_items:
                text = item.text.strip()
                # Look for pattern like "NVDA\n-3.08%\n" or "CCJ\n4.79%"
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                if len(lines) >= 2:
                    ticker = lines[0]
                    # Find line with percentage
                    for line in lines[1:]:
                        if '%' in line:
                            try:
                                # Extract the percentage value
                                weight_str = line.replace('%', '').strip()
                                # Remove any +/- signs (those are daily changes, not weights)
                                # Weight is always positive
                                if weight_str.replace('+', '').replace('-', '').replace('.', '').isdigit():
                                    weight = abs(float(weight_str.replace('+', '').replace('-', '')))
                                    if 0 < weight < 50:  # Sanity check (individual weights should be < 50%)
                                        weights[ticker] = weight
                                        break
                            except ValueError:
                                continue
            
            # Alternative: Extract from specific Portfolio Value elements if they exist
            try:
                portfolio_value_elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'portfolio-value') or contains(@aria-label, 'Portfolio Value')]")
                for elem in portfolio_value_elements:
                    # Extract ticker and value from attributes or text
                    pass
            except:
                pass
            
            # If we got very few weights, try parsing the page source directly
            if len(weights) < 5:
                print("   Trying alternative extraction method...")
                # Look for data in JavaScript objects in page source
                import re
                # Find patterns like {'symbol': 'NVDA', 'portfolioValue': 3.08}
                js_pattern = r"['\"]symbol['\"]:\s*['\"]([A-Z0-9.]+)['\"].*?['\"]portfolioValue['\"]:\s*(\d+\.?\d*)"
                matches = re.findall(js_pattern, page_source, re.DOTALL)
                for symbol, value in matches:
                    try:
                        weights[symbol] = float(value)
                    except ValueError:
                        pass
            
            driver.quit()
            
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
                print("⚠️  Could not extract weights from BullAware, using fallback")
                return {}
                
        except Exception as e:
            print(f"⚠️  Error during weight extraction: {e}")
            driver.quit()
            return {}
            
    except ImportError:
        print("⚠️  Selenium not installed. Install with: pip install selenium webdriver-manager")
        return {}
    except Exception as e:
        print(f"⚠️  Could not fetch portfolio weights from BullAware: {e}")
        return {}


def fetch_stock_data():
    """
    Fetch daily, monthly, and YTD data for all portfolio tickers using yfinance
    """
    stock_data = {}
    
    for etoro_symbol in PORTFOLIO_TICKERS:
        yahoo_ticker = etoro_symbol  # Use eToro symbol as-is for Yahoo Finance
        company_name = etoro_symbol  # Default to symbol
        
        try:
            # Fetch stock info
            stock = yf.Ticker(yahoo_ticker)
            info = stock.info
            
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
