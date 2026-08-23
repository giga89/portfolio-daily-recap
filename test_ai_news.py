#!/usr/bin/env python3
"""
Test script for AI news generator
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_news_generator import generate_market_news_recap, get_why_copy_message

def test_ai_news():
    """Test AI news generation"""
    print("=" * 60)
    print("🧪 TEST: AI News Generator")
    print("=" * 60)
    
    # Test 1: Fixed message (should always work)
    print("\n📝 Test 1: Fixed 'Why Copy' Message")
    print("-" * 60)
    fixed_msg = get_why_copy_message()
    print(fixed_msg)
    print("✅ Fixed message (fallback) generated successfully!")

    print("\n📝 Test 1b: 'Why Copy' Message with custom benchmarks (Bug Fix test)")
    print("-" * 60)
    mock_benchmarks = {
        "SPX500": 136,      # Delta: 200 - 136 = +64 (sovraperformance)
        "NSDQ100": 230,     # Delta: 200 - 230 = -30 (sottoperformance)
        "CHINA50": -8       # Delta: 200 - (-8) = +208 (sovraperformance)
    }
    bug_fix_msg = get_why_copy_message(benchmark_performance=mock_benchmarks)
    print(bug_fix_msg)
    if "VS NSDQ100 : -30% (sottoperformance)" in bug_fix_msg:
        print("✅ Bug fix verified: Negative delta correctly labeled as (sottoperformance)!")
    else:
        print("❌ Bug fix failed: Negative delta not correctly labeled!")
    
    # Test 2: AI news (depends on API key)
    print("\n🤖 Test 2: AI Market News (requires GEMINI_API_KEY)")
    print("-" * 60)
    
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("⚠️  GEMINI_API_KEY not set - AI news will be skipped in production")
        print("   To test this feature, set the environment variable:")
        print("   export GEMINI_API_KEY='your_key_here'")
    else:
        print(f"✅ GEMINI_API_KEY found (length: {len(api_key)})")
        ai_news = generate_market_news_recap()
        if ai_news:
            print("\n" + ai_news)
            print("✅ AI news generated successfully!")
        else:
            print("❌ AI news generation failed (check logs above)")
    
    print("\n" + "=" * 60)
    print("🎉 Test completed!")
    print("=" * 60)

if __name__ == '__main__':
    test_ai_news()
