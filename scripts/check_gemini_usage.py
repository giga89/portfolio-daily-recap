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
    
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    try:
        from ai_model_cascade import FAST_GEMINI_MODELS, build_http_options
        test_model = FAST_GEMINI_MODELS[0]
        http_opts = build_http_options(types, timeout_seconds=30.0)
    except Exception:
        test_model = 'gemini-3.5-flash-lite'
        http_opts = types.HttpOptions(timeout=30000, api_version='v1beta') if hasattr(types, 'HttpOptions') else None

    try:
        client = genai.Client(api_key=api_key, http_options=http_opts) if http_opts else genai.Client(api_key=api_key)

        # Try a minimal API call to check if the key works
        print(f"🧪 Testing API key with a minimal request ({test_model})...")

        response = client.models.generate_content(
            model=test_model,
            contents='Say "OK" if you can read this.',
            config=types.GenerateContentConfig(
                max_output_tokens=64,
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
        
        print("📋 Active Free Tier Roster (verified on runner):")
        print("   • Gemini 3.5 / 3.1 Flash Lite: sub-second responses for replies & quick checks")
        print("   • Gemini 3.6 / 3.5 Flash: full Italian financial recap & dual-check reviews")
        print("   • Gemini 4 Hydrogen: Free Tier Gemini 4 model (needs >=45s HTTP timeout)")
        print("   • Gemini 2.5 Flash: stable baseline fallback (via v1beta)")
        print()
        
        print("💡 TIP: If you're hitting limits, consider:")
        print("   1. Adding delays between requests (time.sleep)")
        print("   2. Using Flash Lite (3.5/3.1) for fast interactive replies")
        print("   3. Upgrading to Pay-as-you-go for Search Grounding & Gemini 4 Argon/Carbon")
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
