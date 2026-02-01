#!/usr/bin/env python3
"""
AI News Generator
Generates market news recap using Google Gemini API
"""

import os
import time
import re
from datetime import datetime
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️  google-genai not installed, AI news generation will be disabled")

from config import PORTFOLIO_TICKERS

# Import Gist storage module
try:
    from gist_storage import load_data, save_data, load_recap_history, save_to_history
    GIST_STORAGE_AVAILABLE = True
except ImportError:
    GIST_STORAGE_AVAILABLE = False
    print("⚠️  gist_storage module not available, using fallback")

# Maximum number of $ tags per post
MAX_TAGS_PER_POST = 5

# Valid eToro symbols for tagging (only use these in posts)
# These are confirmed to exist on eToro platform
ETORO_VALID_SYMBOLS = list(PORTFOLIO_TICKERS.keys())


def _get_all_portfolio_tags():
    """Get all valid portfolio ticker tags for eToro"""
    # Map to eToro symbols (keys of PORTFOLIO_TICKERS)
    return [symbol.replace('.', '') for symbol in PORTFOLIO_TICKERS.keys()]


def _select_tags_for_rotation(max_tags=MAX_TAGS_PER_POST, excluded_tags=None):
    """
    Select tags for the current post with rotation to ensure variety.
    
    Args:
        max_tags: Maximum number of tags to select
        excluded_tags: List of tags to exclude (e.g. already used in this post)
    
    Returns:
        list: List of selected tags
    """
    all_tags = _get_all_portfolio_tags()
    
    if excluded_tags:
        # Remove excluded tags from candidates
        excluded_normalized = [t.replace('.', '').upper() for t in excluded_tags]
        all_tags = [t for t in all_tags if t.replace('.', '').upper() not in excluded_normalized]
    
    if max_tags <= 0:
        return []
    
    try:
        data = load_data()
        used_tags = data.get('used_tags', [])
        
        # Prioritize tags that haven't been used recently
        unused_tags = [tag for tag in all_tags if tag not in used_tags]
        
        # If all tags have been used, start fresh
        if len(unused_tags) < max_tags:
            # Reset rotation - take from unused first, then from start of all_tags
            selected = unused_tags + all_tags[:max_tags - len(unused_tags)]
        else:
            selected = unused_tags[:max_tags]
        
        # Update used tags list (keep track of last 2 rounds worth)
        new_used = used_tags + selected
        # Keep only the most recent ones (about 2 rounds)
        max_history = len(all_tags) * 2
        data['used_tags'] = new_used[-max_history:] if len(new_used) > max_history else new_used
        
        save_data(data)
        
        return selected
        
    except Exception as e:
        print(f"⚠️ Error in tag rotation: {e}")
        return all_tags[:max_tags]


def _limit_tags_in_text(text, allowed_tags, max_tags=MAX_TAGS_PER_POST):
    """
    Ensure text has at most max_tags $ symbols, and only uses allowed tags.
    
    Args:
        text: The generated text
        allowed_tags: List of allowed tag symbols (without $)
        max_tags: Maximum number of tags to keep
    
    Returns:
        str: Text with limited and validated tags
    """
    # Find all $ tags in the text
    tag_pattern = r'\$([A-Za-z0-9\-\.]+)'
    
    tags_found = []
    def tag_replacer(match):
        tag = match.group(1)
        # Normalize tag (remove dots for comparison)
        tag_normalized = tag.replace('.', '').replace('-', '')
        
        # Check if this tag is in our allowed list
        allowed_normalized = [t.replace('.', '').replace('-', '') for t in allowed_tags]
        
        if tag_normalized.upper() in [t.upper() for t in allowed_normalized]:
            if len(tags_found) < max_tags:
                tags_found.append(tag)
                return f'${tag}'
            else:
                # Exceeded max tags, remove the $ prefix
                return tag
        else:
            # Not an allowed tag, remove the $ prefix
            return tag
    
    return re.sub(tag_pattern, tag_replacer, text)


def _remove_market_section_tags(text):
    """
    Remove all $ tags from the MARKET OVERVIEW section.
    Keep tags only in PORTFOLIO FOCUS section.
    
    Args:
        text: The full recap text
    
    Returns:
        str: Text with tags removed from market section
    """
    # Split into sections
    sections = text.split('💼 PORTFOLIO FOCUS')
    
    if len(sections) == 2:
        market_section = sections[0]
        portfolio_section = sections[1]
        
        # Remove all $ tags from market section
        tag_pattern = r'\$([A-Za-z0-9\-\.]+)'
        market_section_clean = re.sub(tag_pattern, r'\1', market_section)
        
        return market_section_clean + '💼 PORTFOLIO FOCUS' + portfolio_section
    
    return text



def get_recent_tags(limit=None):
    """
    Get list of recently used tags from storage.
    Args:
        limit: Return only the last N tags. If None, return all history.
    """
    if not GIST_STORAGE_AVAILABLE:
        return []
    
    try:
        data = load_data()
        tags = data.get('used_tags', [])
        if limit:
            return tags[-limit:]
        return tags
    except Exception:
        return []


def update_rotation_history(new_tags):
    """
    Update the list of used tags in Gist storage.
    Call this when tags are used outside of this module (e.g. in formatter).
    """
    if not GIST_STORAGE_AVAILABLE or not new_tags:
        return

    try:
        # Normalize tags
        normalized_new = [t.replace('$', '').replace('.', '').upper() for t in new_tags]
        
        data = load_data()
        used_tags = data.get('used_tags', [])
        
        # Add new tags
        updated_used = used_tags + normalized_new
        
        # Keep history limited (e.g. 20 items)
        all_tickers = _get_all_portfolio_tags()
        max_history = len(all_tickers) * 2
        
        data['used_tags'] = updated_used[-max_history:] if len(updated_used) > max_history else updated_used
        save_data(data)
        print(f"🔄 Updated tag rotation history with: {normalized_new}")
            
    except Exception as e:
        print(f"⚠️ Error updating tag rotation: {e}")


def generate_monthly_ai_recap(max_tags=MAX_TAGS_PER_POST, excluded_tags=None):
    """
    Generate AI-powered monthly market recap summarizing major events over the past month
    
    Args:
        max_tags: Maximum number of $ tags allowed in the AI output
        excluded_tags: List of tags already used elsewhere in the post
        
    Returns:
        str: Formatted monthly recap or empty string if API key not set
    """
    if not GENAI_AVAILABLE:
        print("⚠️  google-genai package not available, skipping AI monthly recap")
        return ""
    
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("⚠️  Warning: GEMINI_API_KEY not set, skipping AI monthly recap")
        return ""
    
    # List of models to try
    models_to_try = [
        'gemini-2.0-flash-lite',
        'gemini-2.0-flash',
        'gemini-2.5-flash',
        'gemini-flash-latest',
    ]
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Select tags for this post (with rotation)
        selected_tags = []
        selected_tags_str = "None"
        tag_instruction = ""
        
        if max_tags > 0:
            selected_tags = _select_tags_for_rotation(max_tags, excluded_tags)
            selected_tags_str = ', '.join([f'${tag}' for tag in selected_tags])
            tag_instruction = f"""
- You MUST use ONLY these $ tags (max {max_tags}): {selected_tags_str}
- Only use these exact tags, no other $ symbols.
"""
        else:
            tag_instruction = """
- Do NOT use any $ tags in this section.
"""
        
        # Get current month/year for context
        now = datetime.now()
        current_month = now.strftime('%B %Y')  # e.g., "January 2026"
        
        prompt = f"""You are a senior financial analyst. Generate a comprehensive MONTHLY MARKET RECAP for {current_month}.

Use your search tool to find the MAJOR EVENTS and TRENDS that defined this month across:
1. USA Markets (S&P500, Nasdaq, Dow Jones)
2. European Markets (Euro Stoxx, DAX, FTSE)
3. Asian Markets (Shanghai, Nikkei, Hang Seng)
4. Key Economic Data (inflation, employment, GDP, central bank decisions)
5. Major Corporate News (earnings, M&A, product launches)
6. Geopolitical Events (if market-relevant)

Structure your response in TWO sections with a TOPIC-BASED FORMAT:

1. 🌍 MONTHLY MARKET OVERVIEW
Organize this section into MAX 5 MAJOR TOPICS/THEMES that defined {current_month}.
For each topic:
- Use 3 relevant emojis at the start (e.g., 🏛️💵🔔 for Fed decisions, 📊📈💹 for market trends, etc.)
- Write the topic title
- Write a 2-3 sentence summary with specific data points
- IMPORTANT: Do NOT use any $ tags in this section

Example format:
🏛️💵🔔 Fed Rate Decision
The Federal Reserve cut rates by 25bps to 4.25-4.50%, signaling a more dovish stance...

2. 💼 PORTFOLIO IMPACT & OUTLOOK
Organize this section into MAX 5 TOPICS showing how the month's events impacted portfolio stocks.
For each topic, if you have available tags from this list: {selected_tags_str}:
- Use 3 relevant emojis + $TAG (e.g., 🤖💡🚀 $NVDA)
- Write a 2-3 sentence summary about impact and outlook
- If no tags available, just use emojis without tags
{tag_instruction}

Example format (when tag is available):
🤖💡🚀 $NVDA
NVIDIA's new AI chip announcement drove 15% gains this month. Looking ahead to strong Q1 earnings...

STRICT LIMITS:
- MAXIMUM 5 topics per section (total 10 topics max)
- MAXIMUM {MAX_TAGS_PER_POST} $ tags TOTAL across both sections
- Use $ prefix ONLY for the allowed tags listed above
- Focus on HIGH-IMPACT events that shaped the month
- Total character count must stay under 2200 for this AI section

Output format:
🌍 MONTHLY MARKET OVERVIEW

[emoji emoji emoji] Topic Title
Brief summary with data points...

[emoji emoji emoji] Topic Title
Brief summary with data points...

💼 PORTFOLIO IMPACT & OUTLOOK

[emoji emoji emoji] $TAG (if available)
Impact and outlook summary...

[emoji emoji emoji] Topic Title
Impact and outlook summary...
"""
        
        print(f"🤖 Generating monthly AI recap for {current_month}...")
        print(f"   Selected tags: {selected_tags_str}")
        
        # Configure with search tool
        config = None
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7
            )
        except Exception as config_err:
            print(f"⚠️ Search tool unavailable: {config_err}")
            config = types.GenerateContentConfig(temperature=0.7)
        
        # Try models
        for model_name in models_to_try:
            try:
                print(f"   Trying model: {model_name}...")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                
                if response and response.text:
                    print(f"✅ Monthly recap generated using {model_name}!")
                    recap_text = response.text.strip()
                    
                    # Post-process: remove tags from overview section
                    recap_text = _remove_market_section_tags(recap_text)
                    
                    # Limit tags
                    recap_text = _limit_tags_in_text(recap_text, selected_tags, MAX_TAGS_PER_POST)
                    
                    return "\n" + recap_text + "\n"
                else:
                    print(f"⚠️  Empty response from {model_name}")
                    continue
                    
            except Exception as model_error:
                error_msg = str(model_error).lower()
                print(f"⚠️  Model {model_name} failed: {model_error}")
                time.sleep(2)
                
                # Try without tools if not supported
                if 'not supported' in error_msg or 'invalid' in error_msg:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt
                        )
                        if response and response.text:
                            print(f"✅ Monthly recap generated (no tools) using {model_name}!")
                            recap_text = response.text.strip()
                            recap_text = _remove_market_section_tags(recap_text)
                            recap_text = _limit_tags_in_text(recap_text, selected_tags, MAX_TAGS_PER_POST)
                            return "\n" + recap_text + "\n"
                    except Exception as e2:
                        print(f"   Retry failed: {e2}")
                
                continue
        
        print("❌ All models failed for monthly recap")
        return ""
        
    except Exception as e:
        print(f"❌ Error generating monthly recap: {e}")
        return ""


def generate_market_news_recap(max_tags=MAX_TAGS_PER_POST, excluded_tags=None):
    """
    Generate AI-powered market news recap for USA, CHINA, and EU markets
    
    Args:
        max_tags: Maximum number of $ tags allowed in the AI output
        excluded_tags: List of tags already used elsewhere in the post
        
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
    models_to_try = [
        'gemini-2.0-flash-lite',
        'gemini-2.0-flash',
        'gemini-2.5-flash',
        'gemini-flash-latest',
    ]
    
    try:
        # Configure Gemini client
        client = genai.Client(api_key=api_key)
        
        # Select tags for this post (with rotation)
        selected_tags = []
        selected_tags_str = "None" # Fix UnboundLocalError
        tag_instruction = ""
        
        if max_tags > 0:
            selected_tags = _select_tags_for_rotation(max_tags, excluded_tags)
            selected_tags_str = ', '.join([f'${tag}' for tag in selected_tags])
            tag_instruction = f"""
- IMPORTANT: You MUST use ONLY these $ tags in this section (max {max_tags}): {selected_tags_str}
- Only use these exact tags, no other $ symbols.
"""
        else:
            tag_instruction = """
- IMPORTANT: Do NOT use any $ tags in this section.
- Write all ticker symbols as plain text (e.g. NVDA, MSFT) without the $ prefix.
"""
        
        # Get all portfolio tickers for context
        portfolio_symbols = list(PORTFOLIO_TICKERS.keys())
        portfolio_context = ", ".join(portfolio_symbols)
        
        # Load previous history to avoid repetition
        history = load_recap_history() if GIST_STORAGE_AVAILABLE else []
        previous_topics_str = ""
        if history:
            previous_topics_str = "\nCRITICAL: DO NOT REPEAT the following news which were already reported recently:\n"
            for entry in history:
                previous_topics_str += f"- {entry['content'][:300]}...\n"
        
        # Create prompt with strict daily focus and topic-organized format
        current_date = datetime.now().strftime('%Y-%m-%d')
        prompt = f"""You are a senior financial market analyst. Generate a concise daily market recap for today ({current_date}).

CRITICAL REQUIREMENT: Focus ONLY on events from the last 24 hours. Use your search tool to find the most recent news.

{previous_topics_str}

Structure your response in TWO distinct sections with a TOPIC-BASED FORMAT:

1. 🌍 MARKET OVERVIEW
Organize this section into MAX 5 TOPICS/THEMES from today's markets.
For each topic:
- Use 3 relevant emojis at the start (e.g., 📊📈💹 for market trends, 🏛️💵🔔 for Fed decisions, etc.)
- Write a 1-2 sentence summary of that specific topic
- IMPORTANT: Do NOT use any $ tags in this section

Example format:
📊📈💹 S&P500 Rally
The S&P 500 surged 1.2% today driven by strong tech earnings...

2. 💼 PORTFOLIO FOCUS
Organize this section into MAX 5 TOPICS related to the portfolio stocks.
For each topic, if you have available tags from this list: {selected_tags_str}:
- Use 3 relevant emojis + $TAG (e.g., 📦📦📦 $AMZN)
- Write a 1-2 sentence summary about that stock/sector
- If no tags available, just use emojis without tags
{tag_instruction}

Example format (when tag is available):
📦📦📦 $AMZN
Amazon announced new AI-powered logistics system...

STRICT LIMITS:
- MAXIMUM 5 topics per section (total 10 topics max)
- MAXIMUM {MAX_TAGS_PER_POST} $ tags TOTAL across both sections
- Use $ prefix ONLY for the allowed tags listed above
- Keep each topic to 1-2 sentences maximum
- Total character count must stay under 2000 for this AI section

Output format:
🌍 MARKET OVERVIEW

[emoji emoji emoji] Topic Title
Brief summary...

[emoji emoji emoji] Topic Title
Brief summary...

💼 PORTFOLIO FOCUS

[emoji emoji emoji] $TAG (if available)
Brief summary...

[emoji emoji emoji] Topic Title
Brief summary...
"""
        
        print("🤖 Generating AI market news recap...")
        print(f"   Selected tags for this post: {selected_tags_str}")
        
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
                    
                    # Post-process: remove any $ tags from market section
                    recap_text = _remove_market_section_tags(recap_text)
                    
                    # Post-process: ensure only allowed tags are used and limit count
                    recap_text = _limit_tags_in_text(recap_text, selected_tags, MAX_TAGS_PER_POST)
                    
                    # Save to history (using Gist storage)
                    if GIST_STORAGE_AVAILABLE:
                        save_to_history(recap_text)
                    
                    return "\n" + recap_text + "\n"
                else:
                    print(f"⚠️  Empty response from {model_name}, trying next model...")
                    continue
                    
            except Exception as model_error:
                error_msg = str(model_error).lower()
                print(f"⚠️  Model {model_name} failed: {model_error}")
                time.sleep(2)
                
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
                            
                            # Post-process
                            recap_text = _remove_market_section_tags(recap_text)
                            recap_text = _limit_tags_in_text(recap_text, selected_tags, MAX_TAGS_PER_POST)
                            
                            if GIST_STORAGE_AVAILABLE:
                                save_to_history(recap_text)
                            return "\n" + recap_text + "\n"
                    except Exception as e2:
                        print(f"   Retry failed: {e2}")
                
                if 'quota' in error_msg or 'resource_exhausted' in error_msg or '429' in error_msg:
                    print(f"   Quota exceeded for {model_name}, trying next model...")
                    last_error = model_error
                    continue
                else:
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
            benchmark_lines += f"✓ VS {ticker} : {delta:+.0f}% {perf_label}\n"
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
