#!/usr/bin/env python3
"""
Script to check Gemini API usage and quota information
"""

import os
from datetime import datetime

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️  google-genai not installed")
    exit(1)

def check_api_quota():
    """Check Gemini API quota and usage"""
    
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("❌ GEMINI_API_KEY not set in environment variables")
        print("Set it with: $env:GEMINI_API_KEY='your-key-here'")
        return
    
    print("=" * 60)
    print("🔑 GEMINI API QUOTA CHECKER")
    print("=" * 60)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔐 API Key: {api_key[:10]}...{api_key[-5:]}")
    print()
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Try a minimal API call to check if the key works
        print("🧪 Testing API key with a minimal request...")
        
        response = client.models.generate_content(
            model='gemini-2.0-flash-lite',
            contents='Say "OK" if you can read this.',
            config=types.GenerateContentConfig(
                max_output_tokens=10,
                temperature=0.0
            )
        )
        
        if response and response.text:
            print("✅ API Key is VALID and working!")
            print(f"   Response: {response.text.strip()}")
        else:
            print("⚠️  Empty response from API")
        
        print()
        print("=" * 60)
        print("📊 QUOTA INFORMATION")
        print("=" * 60)
        print()
        print("To see detailed quota usage, visit:")
        print("🔗 https://aistudio.google.com/app/apikey")
        print("🔗 https://console.cloud.google.com/apis/dashboard")
        print()
        
        print("📋 Free Tier Limits (Typical):")
        print("   • Gemini 2.0 Flash Lite:")
        print("     - 15 RPM (Requests Per Minute)")
        print("     - 1,500 RPD (Requests Per Day)")
        print("     - 1M TPM (Tokens Per Minute)")
        print()
        print("   • Gemini 2.0 Flash:")
        print("     - 10 RPM")
        print("     - 1,500 RPD")
        print("     - 4M TPM")
        print()
        
        print("💡 TIP: If you're hitting limits, consider:")
        print("   1. Adding delays between requests (time.sleep)")
        print("   2. Using Flash Lite instead of Flash")
        print("   3. Upgrading to a paid plan")
        print()
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"❌ Error: {e}")
        print()
        
        if 'quota' in error_msg or 'resource_exhausted' in error_msg or '429' in error_msg:
            print("🔴 QUOTA EXCEEDED!")
            print("   You've hit your daily/minute limit.")
            print("   Wait a while for the quota to reset.")
            print()
        elif 'invalid' in error_msg or 'api_key' in error_msg:
            print("🔴 INVALID API KEY!")
            print("   Check your API key at:")
            print("   https://aistudio.google.com/app/apikey")
            print()
        elif 'permission' in error_msg:
            print("🔴 PERMISSION DENIED!")
            print("   Enable the Generative Language API in Cloud Console")
            print()
        
        print("For detailed diagnostics, visit Google Cloud Console:")
        print("🔗 https://console.cloud.google.com/apis/dashboard")
    
    print("=" * 60)

if __name__ == "__main__":
    check_api_quota()
