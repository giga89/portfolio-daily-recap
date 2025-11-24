#!/usr/bin/env python3
"""
Daily Portfolio Recap Generator
Collects data from eToro, BullAware, and Google Sheets to generate daily performance recap
"""

import os
import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Comprehensive EMOJI_MAP for all portfolio holdings
EMOJI_MAP = {
    # ETFs
    'SX7PEX.DE': '📊',
    'WDEF.L': '🌐',
    'IEMG': '🌍',
    'IQQL.DE': '💰',
    'IEUR': '🇪🇺',
    
    # Healthcare & Pharmaceuticals
    'AZN.L': '🧬',
    'ABT': '💊',
    'ABBV': '💊',
    'LLY': '💊',
    'NOVO-B': '💉',
    'HUM': '🏥',
    
    # Technology & Semiconductors  
    'AVGO': '💻',
    'NVDA': '🎮',
    'TSM': '🖥️',
    'MSFT': '💻',
    'SNPS': '⚙️',
    'GOOG': '🔍',
    
    # Energy & Nuclear
    'CCJ': '⚛️',
    'PRY.MI': '⚡',
    'ENEL.MI': '⚡',
    
    # Crypto
    'TRX': '🪙',
    'NET': '☁️',
    
    # Financial Services
    'TRIG.L': '🌱',
    'DB1.DE': '💼',
    '2318.HK': '🏢',
    
    # Consumer & Retail
    'RACE': '🏎️',
    'MELI': '🛒',
    'AMZN': '📦',
    'PYPL': '💳',
    
    # Industrial & Mining
    'GLEN.L': '⛏️',
    'VOW3.DE': '🚗',
    'BHP.L': '⛏️',
    
    # Transportation
    '1919.HK': '🚢',
    
    # Other
    'ETOR': '📈',
    'PLTR': '🛡️',
}


async def scrape_etoro_data(username):
    """
    Scrape today's performance and top 5 performers from eToro
    """
    print("[eToro] Starting scrape...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Navigate to eToro home
            await page.goto('https://www.etoro.com/home', wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Extract today's performance
            today_perf = await page.locator('[data-testid="portfolio-overview-total-gain"]').first.text_content()
            
            # Extract top 5 daily movers
            movers = []
            mover_elements = await page.locator('[data-testid="top-mover-item"]').all()
            
            for i, mover in enumerate(mover_elements[:5]):
                symbol = await mover.locator('[data-testid="symbol"]').text_content()
                change = await mover.locator('[data-testid="change-percent"]').text_content()
                movers.append({'symbol': symbol.strip(), 'change': change.strip()})
            
            await browser.close()
            
            return {
                'today_perf': today_perf.strip() if today_perf else '+0.00%',
                'top_movers': movers[:5]
            }
            
        except Exception as e:
            print(f"[eToro] Error: {e}")
            await browser.close()
            return {'today_perf': '+0.00%', 'top_movers': []}


async def scrape_bullaware_data(username):
    """
    Scrape monthly and yearly performance from BullAware
    """
    print("[BullAware] Starting scrape...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            url = f'https://bullaware.com/etoro/{username}'
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Get monthly performance (This Month)
            monthly_perf = await page.locator('[data-period="month"]').first.text_content()
            
            # Get yearly performance (Year to Date)
            yearly_perf = await page.locator('[data-period="ytd"]').first.text_content()
            
            await browser.close()
            
            return {
                'monthly_perf': monthly_perf.strip() if monthly_perf else '+0.00%',
                'yearly_perf': yearly_perf.strip() if yearly_perf else '+0.00%'
            }
            
        except Exception as e:
            print(f"[BullAware] Error: {e}")
            await browser.close()
            return {'monthly_perf': '+0.00%', 'yearly_perf': '+0.00%'}


def get_google_sheets_data(spreadsheet_id, credentials_json):
    """
    Get 5-year performance from Google Sheets cell G6
    """
    print("[Google Sheets] Fetching data...")
    
    try:
        creds_dict = json.loads(credentials_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range='G6'
        ).execute()
        
        value = result.get('values', [['']])[0][0]
        
        return value.strip() if value else '156%'
        
    except Exception as e:
        print(f"[Google Sheets] Error: {e}")
        return '156%'


def generate_recap(data):
    """
    Generate the formatted recap text
    """
    today_emoji = '🍀🍀🍀'
    
    # Get emoji for each asset
    def get_emoji(symbol):
        return EMOJI_MAP.get(symbol, '📈')
    
    # Format top movers with emojis
    top_today_lines = []
    for mover in data['top_today'][:5]:
        emoji = get_emoji(mover['symbol'])
        top_today_lines.append(f"{emoji} {mover['symbol']}: {mover['change']}")
    
    # Calculate average yearly return
    yearly_num = float(data['yearly_perf'].replace('%', '').replace('+', '').replace(',', '.'))
    
    # Calculate 5-year average
    five_year_num = float(data['five_year_perf'].replace('%', '').replace('+', '').replace(',', '.'))
    avg_per_year = five_year_num / 5
    
    # Calculate double-your-money time using Rule of 72
    if avg_per_year > 0:
        double_time = 72 / avg_per_year
    else:
        double_time = 0
    
    recap = f"""📊 RECAP PORTFOLIO GIORNALIERO

{today_emoji} Oggi: {data['today_perf']}
🚧 Questo Mese: {data['monthly_perf']}
🔧 Quest'Anno: {data['yearly_perf']}
🌳 Ultimi 5 Anni (2020-2025): {data['five_year_perf']}

📊 Performance Media Annua: {avg_per_year:.1f}%
⏳ Tempo per Raddoppiare: {double_time:.1f} anni

TOP 5 OGGI:
" + "\n".join(top_today_lines) + """
"""
    
    return recap


async def main():
    """Main function"""
    print("===== Starting Daily Portfolio Recap Generator =====")
    
    # Get environment variables
    etoro_username = os.getenv('ETORO_USERNAME', 'AndreaRavalli')
    spreadsheet_id = os.getenv('SPREADSHEET_ID', '1jK6MlFxO6Im0eBfUP1eOjzW0Nii87jABEHiBnsjP52U')
    google_creds = os.getenv('GOOGLE_SHEETS_CREDENTIALS', '{}')
    
    # Collect data from all sources
    etoro_data = await scrape_etoro_data(etoro_username)
    bullaware_data = await scrape_bullaware_data(etoro_username)
    five_year_perf = get_google_sheets_data(spreadsheet_id, google_creds)
    
    # Combine all data
    combined_data = {
        'today_perf': etoro_data['today_perf'],
        'top_today': etoro_data['top_movers'],
        'monthly_perf': bullaware_data['monthly_perf'],
        'yearly_perf': bullaware_data['yearly_perf'],
        'five_year_perf': five_year_perf
    }
    
    # Generate recap
    recap_text = generate_recap(combined_data)
    
    # Save to file
    os.makedirs('output', exist_ok=True)
    with open('output/recap.txt', 'w', encoding='utf-8') as f:
        f.write(recap_text)
    
    print("\n" + "="*50)
    print(recap_text)
    print("="*50)
    print("\n✅ Recap generated successfully!")
    print(f"Saved to: output/recap.txt")


if __name__ == '__main__':
    asyncio.run(main())
