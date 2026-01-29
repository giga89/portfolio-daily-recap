
import os
import requests
import json

def mask(s):
    if not s: return "None"
    return s[:4] + "..." + s[-4:] if len(s) > 8 else "****"

print("🔍 Debugging Gist Permissions...\n")

# 1. Check Environment Variables
param_gist_token = os.environ.get('GITHUB_GIST_TOKEN')
param_github_token = os.environ.get('GITHUB_TOKEN')
gist_id = os.environ.get('GIST_ID')

print(f"1️⃣  Environment Variables:")
print(f"   - GITHUB_GIST_TOKEN: {'SET (' + mask(param_gist_token) + ')' if param_gist_token else 'NOT SET'}")
print(f"   - GITHUB_TOKEN:      {'SET (' + mask(param_github_token) + ')' if param_github_token else 'NOT SET'}")
print(f"   - GIST_ID:           {gist_id if gist_id else 'NOT SET'}")

# Determine active token
token = param_gist_token or param_github_token

if not token:
    print("\n❌ No token found! Cannot proceed.")
    exit(1)

print(f"\n   👉 Using token from: {'GITHUB_GIST_TOKEN' if param_gist_token else 'GITHUB_TOKEN'}")

# 2. Check Token Scopes
print("\n2️⃣  Checking Token Scopes (via api.github.com/user)...")
headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json'
}

try:
    response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
    
    print(f"   Status Code: {response.status_code}")
    if 'X-OAuth-Scopes' in response.headers:
        scopes = response.headers['X-OAuth-Scopes']
        print(f"   ✅ Detected Scopes: {scopes}")
        if 'gist' in scopes.split(', '):
            print("   ✅ 'gist' scope is PRESENT.")
        else:
            print("   ❌ 'gist' scope is MISSING!")
    else:
        print("   ⚠️ No 'X-OAuth-Scopes' header found. Is this a Fine-grained PAT or unexpected auth type?")
        print(f"   Response Headers keys: {list(response.headers.keys())}")

    if response.status_code == 200:
        user_data = response.json()
        print(f"   👤 Authenticated as: {user_data.get('login')}")
    elif response.status_code == 401:
        print("   ❌ Full authentication failed (401 Bad Credentials). Token might be invalid/expired.")
    elif response.status_code == 403:
        print("   ❌ Access Forbidden (403).")
        
except Exception as e:
    print(f"   ❌ Error checking user: {e}")

# 3. Check Gist Access (if ID is set)
if gist_id:
    print(f"\n3️⃣  Checking Access to Gist ID: {gist_id}...")
    try:
        response = requests.get(f'https://api.github.com/gists/{gist_id}', headers=headers, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            gist_data = response.json()
            owner = gist_data.get('owner', {}).get('login', 'unknown')
            print(f"   ✅ Gist found. Owner: {owner}")
            # Compare with authenticated user
            # (If we got user data above)
        elif response.status_code == 404:
            print("   ❌ Gist not found (404). It might handle exist or token has no read access to secret gists.")
        elif response.status_code == 403:
            print("   ❌ Access Forbidden (403). You likely do not have permission to modify this specific Gist.")
            print("      (Are you trying to write to someone else's Gist?)")
    except Exception as e:
        print(f"   ❌ Error checking gist: {e}")
else:
    print("\n3️⃣  Skipping Gist check (GIST_ID not set).")

print("\n-------------------------------------------")
