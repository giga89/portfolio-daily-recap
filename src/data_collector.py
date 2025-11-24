#!/usr/bin/env python3
"""
Daily Portfolio Recap Generator
Collects data from yfinance and Google Sheets to generate daily performance recap
"""

import os
import json
import yfinance as yf
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Portfolio symbols mapping: eToro symbol -> Yahoo Finance ticker
PORTFOLIO_TICKERS = {
    # ETFs
    'SX7PEX.DE': 'SX7PEX.DE',      # iShares S&P 500 UCITS ETF
    'VWCE.L': 'VWCE.L',            # Vanguard FTSE All-World UCITS ETF
    'IEUR': 'IEUR.L',              # iShares Core MSCI Europe UCITS ETF
    'IQQL.DE': 'IQQL.DE',          # iShares MSCI World Quality Factor UCITS ETF
    'IEMG': 'IEMG',                # iShares Core MSCI Emerging Markets ETF
    'WDEF.L': 'WDEF.L',            # WisdomTree Europe Equity Income UCITS ETF
    
    # Healthcare & Pharmaceuticals
    'AZN.L': 'AZN.L',              # AstraZeneca (London)
    'ABT': 'ABT',                  # Abbott Laboratories
    'ABBV': 'ABBV',                # AbbVie
    'LLY': 'LLY',                  # Eli Lilly
    'NOVO-B': 'NVO',               # Novo Nordisk (US ADR)
    'HUM': 'HUM',                  # Humana
    
    # Technology & Semiconductors
    'AVGO': 'AVGO',                # Broadcom
    'NVDA': 'NVDA',                # NVIDIA
    'TSM': 'TSM',                  # Taiwan Semiconductor
    'MSFT': 'MSFT',                # Microsoft
    'SNPS': 'SNPS',                # Synopsys
    'AMZN': 'AMZN',                # Amazon
    'GOOG': 'GOOGL',               # Google/Alphabet
    'PLTR': 'PLTR',                # Palantir
    'NET': 'NET',                  # Cloudflare
    
    # Energy & Nuclear
    'CCJ': 'CCJ',                  # Cameco
    'ENEL.MI': 'ENEL.MI',          # Enel (Milan)
    
    # Crypto
    'TRX': 'TRX-USD',              # TRON
    'ETOR': 'BTC-USD',             # Bitcoin (assuming ETOR is Bitcoin ETN)
    
    # Financial Services & Others
    'DB1.DE': 'DB1.DE',            # Xtrackers MSCI World Momentum UCITS ETF
    'TRIG.L': 'TRIG.L',            # Trig PLC
    'BHPL': 'BHP',                 # BHP Group (US ADR)
    'PRY.MI': 'PRY.MI',            # Prysmian (Milan)
    'RACE': 'RACE',                # Ferrari
    'VOW3': 'VOW3.DE',             # Volkswagen
    'MELI': 'MELI',                # MercadoLibre
    'PYPL': 'PYPL',                # PayPal
    'GLEN': 'GLEN.L',              # Glencore (London)
    '1919.HK': '1919.HK',          # COSCO SHIPPING Holdings (Hong Kong)
    '2318.HK': '2318.HK',          # Ping An Insurance (Hong Kong)
}

# Emoji mapping for each eToro symbol
EMOJI_MAP = {
    # ETFs
    'SX7PEX.DE': '🪙',
    'VWCE.L': '🌐',
    'IEUR': '🏦',
    'IQQL.DE': '🔥',
    'IEMB': '🌍',
    'WDEF.L': '💼',
    
    # Healthcare & Pharmaceuticals
    'AZN.L': '💊',
    'ABT': '🏥',
    'ABBV': '💉',
    'LLY': '🧬',
    'NOVO-B': '💉',
    'HUM': '🏥',
    
    # Technology & Semiconductors
    'AVGO': '🔧',
    'NVDA': '🤖',
    'TSM': '🏭',
    'MSFT': '💻',
    'SNPS': '🖥️',
    'AMZN': '📦',
    'GOOG': '🔍',
    'PLTR': '🔮',
    'NET': '☁️',
    
    # Energy & Nuclear
    'CCJ': '⚡',
    'ENEL.MI': '🔋',
    
    # Crypto
    'TRX': '🪙',
    'ETOR': '₿',
    
    # Financial Services & Others
    'DB1.DE': '📊',
    'TRIG.L': '🔺',
    'BHPL': '⛏️',
    'PRY.MI': '🔌',
    'RACE': '🏎️',
    'VOW3': '🚗',
    'MELI': '🛒',
    'PYPL': '💳',
    'GLEN': '⛏️',
    '1919.HK': '🚢',
    '2318.HK': '🏦',
}

def get_emoji(etoro_symbol):
    """Get emoji for a given eToro symbol"""
    return EMOJI_MAP.get(etoro_symbol, '📊')

def get_yfinance_data(portfolio_tickers):
    """
    Get stock data from yfinance for all symbols
    Returns daily, monthly, and yearly performance
    """
    print(f"Fetching yfinance data for {len(portfolio_tickers)} symbols...")
    
    stock_data = {}
    
    for etoro_symbol, yahoo_ticker in portfolio_tickers.items():
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

def get_google_sheets_data():
    """
    Get 5-year performance from Google Sheets cell G6
    """
    print("Fetching Google Sheets data...")
    
    try:
        # Get credentials from environment variable
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if not creds_json:
            print("No Google Sheets credentials found")
            return 156.0  # Fallback value
        
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # Spreadsheet ID from the URL
        spreadsheet_id = '1jK6MlFxO6Im0eBfUP1eOjzW0Nii87jABEHiBnsjP52U'
        range_name = 'G6'
        
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if values and len(values[0]) > 0:
            # Extract percentage value (e.g., "156%" -> 156.0)
            value_str = str(values[0][0]).replace('%', '').strip()
            five_year_return = float(value_str)
            print(f"5-year return from Google Sheets: {five_year_return}%")
            return five_year_return
        else:
            print("No data in cell G6")
            return 156.0  # Fallback
            
    except Exception as e:
        print(f"Error fetching Google Sheets data: {e}")
        return 156.0  # Fallback

def calculate_portfolio_daily_change(stock_data):
    """
    Calculate overall portfolio daily performance as simple average
    """
    if not stock_data:
        return 0.0
    
    total = sum(data['daily_change'] for data in stock_data.values())
    return total / len(stock_data)

def generate_recap(stock_data, five_year_return):
    """
    Generate the formatted daily recap
    """
    print("Generating recap...")
    
    # Get today's date
    today = datetime.now().strftime('%d/%m/%Y')
    
    # Calculate portfolio daily change
    portfolio_daily = calculate_portfolio_daily_change(stock_data)
    
    # Calculate top performers
    # Top 5 daily
    daily_sorted = sorted(stock_data.items(), key=lambda x: x[1]['daily_change'], reverse=True)[:5]
    # Top 3 monthly
    monthly_sorted = sorted(stock_data.items(), key=lambda x: x[1]['monthly_change'], reverse=True)[:3]
    # Top 3 yearly
    yearly_sorted = sorted(stock_data.items(), key=lambda x: x[1]['yearly_change'], reverse=True)[:3]
    
    # Calculate 5-year metrics
    avg_yearly_return = five_year_return / 5
    time_to_double = 72 / avg_yearly_return if avg_yearly_return > 0 else 0
    
    # Build the recap text
    recap = f"""🍀🍀🍀 {today} 🍀🍀🍀

📊 Rendimento Giornaliero: {portfolio_daily:+.2f}%

🔝 Top 5 Giornalieri:
"""
    
    for etoro_symbol, data in daily_sorted:
        emoji = get_emoji(etoro_symbol)
        recap += f"{emoji} {etoro_symbol}: {data['daily_change']:+.2f}%\n"
    
    recap += "\n🔝 Top 3 Mensili:\n"
    for etoro_symbol, data in monthly_sorted:
        emoji = get_emoji(etoro_symbol)
        recap += f"{emoji} {etoro_symbol}: {data['monthly_change']:+.2f}%\n"
    
    recap += "\n🔝 Top 3 Annuali:\n"
    for etoro_symbol, data in yearly_sorted:
        emoji = get_emoji(etoro_symbol)
        recap += f"{emoji} {etoro_symbol}: {data['yearly_change']:+.2f}%\n"
    
    recap += f"""
📈 Performance 5 Anni: {five_year_return:.2f}%
💰 Rendimento Medio Annuale: {avg_yearly_return:.2f}%
⏱️ Tempo per Raddoppiare: {time_to_double:.1f} anni
"""
    
    return recap

def main():
    """
    Main function to orchestrate data collection and recap generation
    """
    print("Starting daily portfolio recap generation...")
    print("=" * 50)
    
    # Get list of all portfolio symbols
    print(f"Portfolio contains {len(PORTFOLIO_TICKERS)} positions")
    print("=" * 50)
    
    # Step 1: Get yfinance data for all symbols
    stock_data = get_yfinance_data(PORTFOLIO_TICKERS)
    print(f"Successfully fetched data for {len(stock_data)} symbols")
    print("=" * 50)
    
    # Step 2: Get 5-year performance from Google Sheets
    five_year_return = get_google_sheets_data()
    print("=" * 50)
    
    # Step 3: Generate formatted recap
    recap = generate_recap(stock_data, five_year_return)
    
    # Step 4: Save to file
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
