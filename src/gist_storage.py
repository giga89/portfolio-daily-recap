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

def _get_headers():
    """Get authorization headers for GitHub API"""
    token = os.environ.get('GITHUB_GIST_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        return None
    return {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

def _get_default_data():
    """Return default data structure"""
    return {
        'recap_history': [],
        'used_tags': [],
        'last_updated': None
    }

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
        
        if response.status_code == 200:
            gist_data = response.json()
            if GIST_FILENAME in gist_data.get('files', {}):
                content = gist_data['files'][GIST_FILENAME]['content']
                data = json.loads(content)
                print(f"✅ Loaded data from Gist (ID: {gist_id[:8]}...)")
                return data
            else:
                print(f"⚠️ File {GIST_FILENAME} not found in gist, using defaults")
                return _get_default_data()
        elif response.status_code == 404:
            print(f"⚠️ Gist not found (ID: {gist_id}), using defaults")
            return _get_default_data()
        else:
            print(f"⚠️ Error loading gist: {response.status_code} - {response.text}")
            return _get_default_data()
            
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
