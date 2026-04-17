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
            'monthly_performance': None,  # Add fetching logic if needed
            'yearly_performance': None,   # Add fetching logic if needed
            'dividend': None              # Add fetching logic if needed
        }
            
    except Exception as e:
        print(f"Error fetching Google Sheets data: {e}")
        return {
            'five_year_return': 156.0,
            'monthly_performance': None,
            'yearly_performance': None,
            'dividend': None
        }


def update_google_sheets_cell(cell_range, value):
    """
    Update a specific cell in Google Sheets with a value
    """
    print(f"Updating Google Sheets cell {cell_range} with value: {value}...")
    
    try:
        # Get credentials from environment variable
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if not creds_json:
            print("No Google Sheets credentials found, cannot update")
            return False
            
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # Prepare the value update
        # Format with comma as decimal separator (Italian style)
        value_str = f"{value:.2f}%".replace('.', ',')
        body = {
            'values': [[value_str]]
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=cell_range,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        print(f"✓ Successfully updated cell {cell_range}: {result.get('updatedCells')} cells updated")
        return True
        
    except Exception as e:
        print(f"❌ Error updating Google Sheets: {e}")
        return False

def init_historical_sheet_if_missing():
    """Ensure the historical sheet 'Storico' exists."""
    try:
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if not creds_json:
            return False
            
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)
        
        # Check if "Storico" exists
        sheet_metadata = service.spreadsheets().get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
        sheets = sheet_metadata.get('sheets', '')
        if not any(s.get("properties", {}).get("title", "") == "Storico" for s in sheets):
            # Create it
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': 'Storico'
                    }
                }
            }]
            service.spreadsheets().batchUpdate(
                spreadsheetId=GOOGLE_SHEETS_ID,
                body={'requests': requests}
            ).execute()
            
            # Add header
            body = {
                'values': [['Date', 'Performance %', 'ATH %']]
            }
            service.spreadsheets().values().update(
                spreadsheetId=GOOGLE_SHEETS_ID,
                range='Storico!A1:C1',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
        return True
    except Exception as e:
        print(f"Error initializing historical sheet: {e}")
        return False

def append_historical_data(date_str, current_performance, current_ath):
    """Append a row to the 'Storico' sheet."""
    try:
        init_historical_sheet_if_missing()
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if not creds_json:
            return False
            
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)
        
        # We append unformatted numbers to make charting easier
        body = {
            'values': [[date_str, current_performance, current_ath]]
        }
        
        service.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range='Storico!A:C',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        print(f"✓ Appended {date_str} data to Storico sheet.")
        return True
    except Exception as e:
        print(f"❌ Error appending to Google Sheets: {e}")
        return False

def fetch_historical_from_sheets():
    """Fetch the historical data from the 'Storico' sheet as a Pandas DataFrame."""
    import pandas as pd
    try:
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if not creds_json:
            return None
            
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range='Storico!A:C'
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values) <= 1:
            return None
            
        # First row is header
        df = pd.DataFrame(values[1:], columns=['Date', 'Performance', 'ATH'])
        df['Date'] = pd.to_datetime(df['Date'])
        # Clean potential % strings and convert to float
        df['Performance'] = df['Performance'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
        df['ATH'] = df['ATH'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
        return df
    except Exception as e:
        print(f"Error fetching historical data from sheets: {e}")
        return None
