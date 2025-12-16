"""
Fetch data from Google Sheets
"""

import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import GOOGLE_SHEETS_ID, FIVE_YEAR_CELL


def fetch_google_sheets_data():
    """
    Get performance data from Google Sheets
    Returns dict with: five_year_return, monthly_performance, yearly_performance, dividend
    """
    print("Fetching Google Sheets data...")
    
    try:
        # Get credentials from environment variable
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if not creds_json:
            print("No Google Sheets credentials found, using fallback values")
            return {
                'five_year_return': 156.0,
                'monthly_performance': None,
                'yearly_performance': None,
                'dividend': None
            }
        
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # Fetch 5-year return
        result = service.spreadsheets().values().get(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=FIVE_YEAR_CELL
        ).execute()
        
        values = result.get('values', [])
        if values and len(values[0]) > 0:
            value_str = str(values[0][0]).replace('%', '').strip()
            five_year_return = float(value_str)
            print(f"5-year return from Google Sheets: {five_year_return}%")
        else:
            five_year_return = 156.0
        
        return {
            'five_year_return': five_year_return,
            'monthly_performance': None,
            'yearly_performance': None,
            'dividend': None
        }
            
    except Exception as e:
        print(f"Error fetching Google Sheets data: {e}")
        return {
            'five_year_return': 156.0,
            'monthly_performance': None,
            'yearly_performance': None,
            'dividend': None
        }

def update_yearly_performance(value):
    """
    Update the yearly performance cell in Google Sheets
    """
    if value is None:
        print("No YTD value to update in Sheets")
        return

    print(f"Updating yearly performance in Google Sheets to: {value}%...")
    
    try:
        from config import YEARLY_PERFORMANCE_CELL
        
        # Get credentials from environment variable
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if not creds_json:
            print("No Google Sheets credentials found, cannot update")
            return
        
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        body = {
            'values': [[f"{value}%"]]
        }
        
        service.spreadsheets().values().update(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=YEARLY_PERFORMANCE_CELL,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        print("✓ Successfully updated Google Sheets")
        
    except Exception as e:
        print(f"Error updating Google Sheets: {e}")
