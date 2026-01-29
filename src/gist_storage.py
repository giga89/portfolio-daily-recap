#!/usr/bin/env python3
"""
GitHub Gist Storage Module
Handles reading and writing data to GitHub Gist for persistent storage outside the repo.
"""

import os
import json
import requests
from datetime import datetime

# Gist configuration
GIST_ID = os.environ.get('GIST_ID', '')  # Will be set after first run
GIST_FILENAME = 'portfolio_recap_data.json'

# Legacy data to migrate if Gist is empty
LEGACY_HISTORY = [
  {
    "timestamp": "2025-12-31T15:12:13.884067",
    "content": "\ud83c\udf0d MARKET NEWS RECAP\n\nGlobal markets traded with a modest year-end pullback amid extremely thin holiday volumes, with US $S&P 500 and $Nasdaq 100 futures signaling a soft open, down 0.2% and 0.3% respectively. European bourses were similarly muted, as the Stoxx Europe 600 fell 0.1% and France's CAC 40 declined 0.4% in early trading. In Asia, the $Shanghai Composite managed a marginal gain of 0.1%, contrasting with a 0.9% drop in the Hang Seng index, as investors booked profits on the final trading day of the year.\n\n\ud83d\udcbc PORTFOLIO FOCUS\n\nThe AI and chip sector, which includes $NVDA, $AVGO, $TSM, $MSFT, and $SNPS, saw a major catalyst with news of $NVDA's potential $20 billion acquisition of Groq's AI inferencing technology, positioning it for the next growth phase in AI adoption. In the GLP-1 space, $NOVO-B.CO submitted a New Drug Application (NDA) to the FDA for its once-weekly CagriSema combination for weight management, intensifying competition with $LLY. Separately, a new FDA-approved m"
  },
  {
    "timestamp": "2025-12-31T22:17:45.867978",
    "content": "\ud83c\udf0d MARKET NEWS RECAP\n\nGlobal markets closed out the final trading day of the year on a soft note amid extremely thin holiday volumes. US indices declined, with the $S&P 500 falling 0.33% and the $Nasdaq 100 down 0.34%, primarily driven by weakness in chip and data storage stocks. European stocks were also slightly lower, with the Euro Stoxx 50 easing 0.08%, while China's Shanghai Composite showed resilience, climbing 0.1% following stronger-than-expected December Manufacturing and Non-Manufacturing PMI data. The unexpected drop in US weekly jobless claims to a one-month low was a hawkish factor contributing to higher bond yields and pressure on equities.\n\n\ud83d\udcbc PORTFOLIO FOCUS\n\nThe AI and Semiconductor cohort, including $NVDA, $TSM, $AVGO, $MSFT, $SNPS, $AMZN, and $GOOG, faced selling pressure, as chip stocks led the broader $Nasdaq decline. The Healthcare sector, featuring $LLY and $NOVO-B.CO, continued to be driven by the prevailing narrative of $LLY's dominance in the GLP-1 weight-loss d"
  },
  {
    "timestamp": "2026-01-01T10:15:19.384074",
    "content": "\ud83c\udf0d MARKET NEWS RECAP\n\nGlobal financial markets were universally closed today for the New Year's Day holiday, resulting in no trading activity for major indices including the $S&P 500, $Nasdaq, and the $Euro Stoxx. The focus has entirely shifted to policy announcements and economic forecasts for the year ahead, with all eyes now on the first trading session of 2026 tomorrow. Asian markets, including the Shanghai Composite, also observed the holiday, leaving volume at negligible levels worldwide. The lack of trading volume has led analysts to issue numerous sector outlooks, setting the stage for tomorrow\u2019s open.\n\n\ud83d\udcbc PORTFOLIO FOCUS\n\nWith markets closed, attention is on the 2026 outlook for key sectors. The Healthcare cohort, including $AZN.L, $ABT, $ABBV, $LLY, and $NOVO-B.CO, is poised for continued growth based on new product pipelines and a strong M&A environment, with particular momentum expected in obesity and immunology treatments. AI and Semiconductor names like $NVDA, $TSM, $MSFT, "
  },
  {
    "timestamp": "2026-01-01T15:12:11.179788",
    "content": "\ud83c\udf0d MARKET NEWS RECAP\n\nGlobal financial markets, including the $S&P 500, $Nasdaq, and $Euro Stoxx, were universally closed today for the New Year's Day holiday, resulting in extremely limited trading activity. A key European policy event saw Bulgaria officially adopt the euro, becoming the 21st country to join the single currency. In trade news, China announced it will impose additional 55% tariffs on beef imports from key global suppliers, including the US and Australia, effective today.\n\n\ud83d\udcbc PORTFOLIO FOCUS\n\nWith no major company-specific news during the holiday, the focus remains on macro drivers for the portfolio's core holdings. The AI/Cloud infrastructure sector, including $NVDA, $AVGO, $MSFT, and $GOOG, enters the new year with strong momentum following $GOOG's best year since 2009 due to strengthening AI sentiment. Healthcare and Pharma holdings ($LLY, $NOVO-B.CO, $ABBV) are centered on upcoming Q4 earnings and continued legislative uncertainty regarding drug pricing. China's new t"
  },
  {
    "timestamp": "2026-01-01T22:17:10.839813",
    "content": "\ud83c\udf0d MARKET NEWS RECAP\n\nGlobal financial markets were largely closed for the New Year's Day holiday, severely limiting major index trading in the US and Europe. The $S&P 500 and $Euro Stoxx saw no activity, with attention shifting to overnight commodity moves. The $Shanghai Composite, however, provided a final data point, managing a slight gain, closing up 0.1% at 3,968.84. Gold prices remain a macro focus after recording an astonishing annual gain of approximately 64% in 2025, while oil prices ended the year down nearly 20%.\n\n\ud83d\udcbc PORTFOLIO FOCUS\n\nThe AI/Semiconductor complex, including $NVDA and $TSM, is poised for a strong start to 2026 following reports that $NVDA is ramping up production for its H200 AI chips in a dramatic push to meet Chinese orders exceeding 2 million units for the year. Broader AI-driven demand for high-bandwidth memory chips is expected to accelerate a supply crunch, potentially driving consumer electronics prices up by 5% to 20% in 2026. In Healthcare, $ABT, $ABBV,"
  }
]

def _get_headers():
    """Get authorization headers for GitHub API"""
    token = os.environ.get('GIST_ACCESS_TOKEN') or os.environ.get('GITHUB_GIST_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        # Debug: print only if we really can't find anything
        # print("Debug: No token found in env vars")
        return None
    
    # Simple check to warn if using potential default token without gist scope
    if not os.environ.get('GIST_ACCESS_TOKEN') and not os.environ.get('GITHUB_GIST_TOKEN'):
        print("ℹ️  Using default GITHUB_TOKEN (might lack gist permissions)")
        
    return {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

def verify_token_permissions(token):
    """Verify if the token has 'gist' scope"""
    try:
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        response = requests.get('https://api.github.com/user', headers=headers, timeout=5)
        if 'X-OAuth-Scopes' in response.headers:
            scopes = response.headers['X-OAuth-Scopes']
            if 'gist' not in scopes.split(', '):
                print(f"⚠️  WARNING: Token scopes are: {scopes}. Missing 'gist' scope!")
                return False
        return True
    except Exception:
        return True # Assume ok if check fails to avoid blocking

def _get_default_data():
    """Return default data structure, migrating local history if available"""
    default_data = {
        'recap_history': [],
        'used_tags': [],
        'last_updated': None
    }
    
    # Use embedded legacy history for migration
    print(f"📦 checking for migration: Using embedded legacy history ({len(LEGACY_HISTORY)} items).")
    default_data['recap_history'] = LEGACY_HISTORY
            
    return default_data

def load_data():
    """
    Load data from GitHub Gist
    
    Returns:
        dict: Data containing recap_history, used_tags, etc.
    """
    headers = _get_headers()
    gist_id = os.environ.get('GIST_ID', '')
    
    if not headers:
        print("⚠️ No GitHub token found, using empty data")
        return _get_default_data()
    
    if not gist_id:
        print("ℹ️ No GIST_ID set, will create new gist on save")
        return _get_default_data()
    
    try:
        response = requests.get(
            f'https://api.github.com/gists/{gist_id}',
            headers=headers,
            timeout=10
        )
        
        migrated = False
        data = _get_default_data() # Start with defaults (including legacy history)

        if response.status_code == 200:
            gist_data = response.json()
            if GIST_FILENAME in gist_data.get('files', {}):
                content = gist_data['files'][GIST_FILENAME]['content']
                loaded_data = json.loads(content)
                print(f"✅ Loaded data from Gist (ID: {gist_id[:8]}...)")
                
                # Check if we need to merge legacy history (if Gist history is empty)
                if not loaded_data.get('recap_history') and LEGACY_HISTORY:
                    print("🔄 Gist history is empty. Merging legacy history...")
                    loaded_data['recap_history'] = LEGACY_HISTORY
                    migrated = True
                
                data = loaded_data
            else:
                print(f"⚠️ File {GIST_FILENAME} not found in gist, using defaults (will migrate)")
                migrated = True
        elif response.status_code == 404:
            print(f"⚠️ Gist not found (ID: {gist_id}), using defaults (will migrate)")
            migrated = True
        else:
            print(f"⚠️ Error loading gist: {response.status_code} - {response.text}")
            # Fallback to defaults (with legacy history)
            migrated = True
            
        # If we performed a migration (merge or fresh default), we should ideally save it.
        # But this function is a 'load', so we just return the data. 
        # The next 'save_data' call (which happens after generating news) will persist it.
        # If the news generation fails, we might lose the migration for this run, but it will try again next time.
        return data
            
    except Exception as e:
        print(f"⚠️ Error loading from Gist: {e}")
        return _get_default_data()

def save_data(data):
    """
    Save data to GitHub Gist
    
    Args:
        data: Dict containing recap_history, used_tags, etc.
    
    Returns:
        bool: True if save was successful
    """
    headers = _get_headers()
    gist_id = os.environ.get('GIST_ID', '')
    
    if not headers:
        print("⚠️ No GitHub token found, cannot save to Gist")
        return False
    
    data['last_updated'] = datetime.now().isoformat()
    content = json.dumps(data, indent=2)
    
    gist_payload = {
        'description': 'Portfolio Daily Recap - Data Storage',
        'files': {
            GIST_FILENAME: {
                'content': content
            }
        }
    }
    
    try:
        if gist_id:
            # Update existing gist
            response = requests.patch(
                f'https://api.github.com/gists/{gist_id}',
                headers=headers,
                json=gist_payload,
                timeout=10
            )
        else:
            # Create new gist (private)
            gist_payload['public'] = False
            response = requests.post(
                'https://api.github.com/gists',
                headers=headers,
                json=gist_payload,
                timeout=10
            )
        
        if response.status_code in [200, 201]:
            result = response.json()
            new_gist_id = result.get('id', '')
            if not gist_id and new_gist_id:
                print(f"🆕 Created new Gist! Add this as secret GIST_ID: {new_gist_id}")
            else:
                print(f"✅ Data saved to Gist (ID: {new_gist_id[:8]}...)")
            return True

        elif response.status_code == 403:
            print(f"❌ Error saving to Gist: 403 - Forbidden.")
            print("   👉 Check that your GIST_ID is correct (if set).")
            print("   👉 If using GITHUB_TOKEN in Actions, it may lack 'gist' permissions.")
            return False
        elif response.status_code == 401:
            print(f"❌ Error saving to Gist: 401 - Unauthorized.")
            print("   👉 The token provided is invalid or expired.")
            print("   👉 If using GIST_ACCESS_TOKEN, check if you copied it correctly.")
            return False
        else:
            print(f"❌ Error saving to Gist: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error saving to Gist: {e}")
        return False

def load_recap_history():
    """Load only recap history for backwards compatibility"""
    data = load_data()
    return data.get('recap_history', [])

def save_to_history(recap_text):
    """Save recap to history"""
    data = load_data()
    history = data.get('recap_history', [])
    
    # Keep only the last 5 recaps
    history.append({
        'timestamp': datetime.now().isoformat(),
        'content': recap_text[:1000]
    })
    history = history[-5:]
    
    data['recap_history'] = history
    save_data(data)

def get_used_tags():
    """Get list of recently used tags"""
    data = load_data()
    return data.get('used_tags', [])

def save_used_tags(tags):
    """Save the list of used tags for rotation"""
    data = load_data()
    data['used_tags'] = tags
    save_data(data)

def get_portfolio_config():
    """Get portfolio items (tickers) from Gist"""
    data = load_data()
    return data.get('portfolio_config', {}), data.get('portfolio_emojis', {})

def save_portfolio_config(tickers, emojis):
    """Save portfolio items (tickers) and emojis to Gist"""
    data = load_data()
    data['portfolio_config'] = tickers
    data['portfolio_emojis'] = emojis
    save_data(data)
