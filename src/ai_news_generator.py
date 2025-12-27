#!/usr/bin/env python3
"""
AI News Generator
Generates market news recap using Google Gemini API
"""

import os
import json
from datetime import datetime
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️  google-genai not installed, AI news generation will be disabled")

from config import PORTFOLIO_TICKERS

# Path for storing recap history to avoid repetition
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "recap_history.json")

def _load_history():
    """Load previous news recaps to avoid repetition"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading history file: {e}")
            return []
    return []

def _save_to_history(recap_text):
    """Save the current recap to history"""
    try:
        history = _load_history()
        # Keep only the last 5 recaps to provide context without hitting token limits
        history.append({
            "timestamp": datetime.now().isoformat(),
            "content": recap_text[:1000] # Store the first 1000 chars for context
        })
        history = history[-5:]
        
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving to history file: {e}")


def generate_market_news_recap():
    """
    Generate AI-powered market news recap for USA, CHINA, and EU markets
    Uses multiple model fallbacks to handle quota limits gracefully
    
    Returns:
        str: Formatted news recap or empty string if API key not set
    """
    if not GENAI_AVAILABLE:
        print("⚠️  google-genai package not available, skipping AI news generation")
        return ""
    
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("⚠️  Warning: GEMINI_API_KEY not set, skipping AI news generation")
        return ""
    
    # List of models to try (in order of preference)
    # Using exact names found in the debug list
    models_to_try = [
        'gemini-2.0-flash',       # Stable 2.0
        'gemini-flash-latest',    # Alias for latest 1.5 flash
        'gemini-pro-latest',     # Alias for latest 1.5 pro
        'gemini-2.0-flash-exp',   # Experimental 2.0 (fallback)
    ]
    
    try:
        # Configure Gemini client
        client = genai.Client(api_key=api_key)
        
        # Extract portfolio context - Use all tickers as requested
        portfolio_symbols = list(PORTFOLIO_TICKERS.keys())
        portfolio_context = ", ".join(portfolio_symbols)
        
        # Load previous history to avoid repetition
        history = _load_history()
        previous_topics_str = ""
        if history:
            previous_topics_str = "\nCRITICAL: DO NOT REPEAT the following news which were already reported recently:\n"
            for entry in history:
                # Extract a mini-summary if possible or just part of the text
                previous_topics_str += f"- {entry['content'][:300]}...\n"
        
        # Create prompt with strict daily focus and separated sections
        current_date = datetime.now().strftime('%Y-%m-%d')
        prompt = f"""You are a senior financial market analyst. Generate a concise daily market recap for today ({current_date}).

CRITICAL REQUIREMENT: Focus ONLY on events from the last 24 hours. Use your search tool to find the most recent news.

{previous_topics_str}

Structure your response in TWO distinct sections:

1. 🌍 MARKET OVERVIEW
- Summarize the most important movements TODAY in USA, CHINA, and EU markets.
- Mention specific indices (S&P500, Nasdaq, Shanghai Composite, Euro Stoxx) only if they had significant moves today.
- Include specific data points (percentages, levels) if available.
- Limit to 3-4 concise, high-impact sentences.

2. 💼 PORTFOLIO FOCUS
- Provide specific updates, catalysts, or performance drivers for these holdings: {portfolio_context}
- Focus exclusively on news affecting these specific tickers in the last 24 hours.
- If no specific news is available for these tickers today, briefly mention the sector trends (e.g., AI, Healthcare, Energy) impacting them right now.
- Limit to 4-5 concise, high-impact sentences.

Rules:
- Professional, objective, and engaging tone.
- Format for Telegram (plain text, use emoji sparingly).
- Use **bold text** for key tickers or index names.
- Ensure the news is FRESH and relevant to today.

Output format:
🌍 MARKET NEWS RECAP

[Market Overview section]

💼 PORTFOLIO FOCUS

[Portfolio Focus section]
"""
        
        print("🤖 Generating AI market news recap...")
        
        # Configure search tool if available in the SDK
        config = None
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7
            )
        except Exception as config_err:
            print(f"⚠️ Could not initialize Google Search tool: {config_err}")
            config = types.GenerateContentConfig(temperature=0.7)

        # Try each model until one works
        last_error = None
        for model_name in models_to_try:
            try:
                print(f"   Trying model: {model_name}...")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                
                if response and response.text:
                    print(f"✅ AI news recap generated successfully using {model_name}!")
                    recap_text = response.text.strip()
                    # Save to history to avoid repetition next time
                    _save_to_history(recap_text)
                    return "\n" + recap_text + "\n"
                else:
                    print(f"⚠️  Empty response from {model_name}, trying next model...")
                    continue
                    
            except Exception as model_error:
                error_msg = str(model_error).lower()
                print(f"⚠️  Model {model_name} failed: {model_error}")
                
                # Check if it's a quota error or something that might be fixed by removing tools
                if 'not supported' in error_msg or 'invalid' in error_msg:
                    print(f"   Model {model_name} might not support search tools, trying without...")
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt
                        )
                        if response and response.text:
                            print(f"✅ AI news recap generated successfully (without tools) using {model_name}!")
                            recap_text = response.text.strip()
                            _save_to_history(recap_text)
                            return "\n" + recap_text + "\n"
                    except Exception as e2:
                        print(f"   Retry failed: {e2}")
                
                if 'quota' in error_msg or 'resource_exhausted' in error_msg or '429' in error_msg:
                    print(f"   Quota exceeded for {model_name}, trying next model...")
                    last_error = model_error
                    continue
                else:
                    # Other error, try next model anyway
                    last_error = model_error
                    continue
        
        # All models failed
        print(f"❌ All models failed. Last error: {last_error}")
        print("💡 Tip: Wait a few minutes for quota reset, or check your API key at https://makersuite.google.com/")
        return ""
            
    except Exception as e:
        print(f"❌ Error generating AI news recap: {e}")
        print(f"Error type: {type(e).__name__}")
        return ""



def get_why_copy_message(five_year_return=161, avg_yearly_return=32, benchmark_performance=None):
    """
    Returns the fixed message explaining why to copy this portfolio
    
    Args:
        five_year_return: Total return since strategy change (default 161%)
        avg_yearly_return: Average yearly return (default 32%)
        benchmark_performance: Dict of {etoro_ticker: performance_value}
    
    Returns:
        str: Formatted fixed message with performance data
    """
    # Calculate years to double using Rule of 72
    time_to_double = 72 / avg_yearly_return if avg_yearly_return > 0 else 0
    
    benchmark_lines = ""
    if benchmark_performance:
        for ticker, perf in benchmark_performance.items():
            # Calculate the difference (delta) between our return and benchmark
            delta = five_year_return - perf
            perf_label = "(outperformance)" if delta >= 0 else "(underperformance)"
            benchmark_lines += f"✓ VS ${ticker} : {delta:+.0f}% {perf_label}\n"
    else:
        # Fallback if no data
        benchmark_lines = "✓ Outperforming S&P500\n✓ Outperforming MSCI World\n✓ Outperforming Euro Stoxx 50"

    message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 WHY COPY THIS PORTFOLIO?

📈 TRACK RECORD:
+{five_year_return:.0f}% since strategy change (2020)
~{avg_yearly_return:.0f}% average annual return
Double your money in ~{time_to_double:.1f} years

✅ STRATEGY HIGHLIGHTS:
• Smart diversification across 3 continents
• Focus on megatrends: AI, Healthcare, Energy
• Mix of ETFs + high-potential individual stocks
• Active and transparent management

📊 PERFORMANCE DELTA vs. BENCHMARKS (Since 2020):
{benchmark_lines.strip()}

🎯 Long-term strategy based on solid fundamentals
🔄 Periodic rebalancing to optimize risk/reward

@AndreaRavalli
━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return message
