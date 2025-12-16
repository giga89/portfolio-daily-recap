
import os
import sys
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Add src to path
sys.path.insert(0, 'src')
from config import GOOGLE_SHEETS_ID, YEARLY_PERFORMANCE_CELL

def test_update():
    print("Testing Google Sheets update...")
    
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if not creds_json:
        print("ERROR: No GOOGLE_SHEETS_CREDENTIALS found in env")
        return

    try:
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        test_value = "TEST_UPDATE"
        body = {
            'values': [[test_value]]
        }
        
        print(f"Attempting to write '{test_value}' to cell {YEARLY_PERFORMANCE_CELL}...")
        
        result = service.spreadsheets().values().update(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=YEARLY_PERFORMANCE_CELL,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        print(f"Success! Result: {json.dumps(result, indent=2)}")
        
    except Exception as e:
        print(f"FAILED with error: {e}")
        # Print detailed error if it's an HttpError
        if hasattr(e, 'content'):
            print(f"Error content: {e.content}")

if __name__ == "__main__":
    test_update()
