"""
Format the recap output in a nice readable format
"""

from datetime import datetime
from config import EMOJI_MAP
import os
import random
import ai_news_generator


def get_emoji(etoro_symbol):
    """Get emoji for a given eToro symbol"""
    return EMOJI_MAP.get(etoro_symbol, '📊')


def format_ticker(etoro_symbol, company_name, performance, use_tag=False):
    """Format a ticker line with eToro link and performance"""
    emoji = get_emoji(etoro_symbol)
    symbol_str = f"${etoro_symbol}" if use_tag else etoro_symbol
    return f"{emoji} {symbol_str} {performance:+.2f}%"


def generate_recap(stock_data, portfolio_daily, sheets_data, benchmark_data=None, portfolio_weekly=None):
    """
    Generate the formatted daily recap matching the desired output format
    """
    print("Generating recap...")
    
    # Get today's date
    today = datetime.now().strftime('%d/%m/%Y')
    
    # Extract sheets data
    five_year_return = sheets_data['five_year_return']
    
    # Calculate 5-year metrics
    avg_yearly_return = five_year_return / 5
    
    # Get market session from environment variable
    market_session = os.getenv('MARKET_SESSION', 'Daily recap')
    is_weekly = "WEEKLY" in market_session.upper()
    
    # Calculate top performers
    # If weekly, we use weekly_change for the "TOP 5" section
    if is_weekly:
        daily_sorted = sorted(stock_data.items(), key=lambda x: x[1]['weekly_change'], reverse=True)[:5]
    else:
        daily_sorted = sorted(stock_data.items(), key=lambda x: x[1]['daily_change'], reverse=True)[:5]
        
    monthly_sorted = sorted(stock_data.items(), key=lambda x: x[1]['monthly_change'], reverse=True)[:3]
    yearly_sorted = sorted(stock_data.items(), key=lambda x: x[1]['yearly_change'], reverse=True)[:3]

    
    # Determine dynamic header based on session
    session_upper = market_session.upper()
    if "WEEKLY" in session_upper:
         header = f"📅 {session_upper} 📆"
    elif "OPEN" in session_upper:
        header = f"🌅 {session_upper} 📊"
    elif "RECAP" in session_upper:
        header = f"🌠 {session_upper} 🌙"
    else:
        header = f"✨ {session_upper} ✨"

    # Determine dynamic performance line
    # Use weekly performance if this is a weekly recap
    current_perf = portfolio_weekly if (is_weekly and portfolio_weekly is not None) else portfolio_daily
    
    if current_perf > 2.0:
        perf_text = "🚀 TO THE MOON"
        perf_emoji = "🔥"
    elif current_perf > 0.5:
        perf_text = "🍀 GREAT GREEN" # Removed "DAY" to be generic
        perf_emoji = "✅"
    elif current_perf >= 0:
        perf_text = "🌿 SLIGHT GAINS"
        perf_emoji = "🌱"
    elif current_perf > -0.5:
        perf_text = "📉 MINOR DIP"
        perf_emoji = "⚖️"
    elif current_perf > -2.0:
        perf_text = "💀 ROUGH" # Removed "DAY"
        perf_emoji = "🩸"
    else:
        perf_text = "🧨 MARKET CRASH"
        perf_emoji = "🆘"

    recap = f"""{header}

{perf_emoji} {perf_emoji} {perf_emoji} {perf_text}: {current_perf:+.2f}% {perf_emoji} {perf_emoji} {perf_emoji}

TOP 5 {"WEEKLY" if is_weekly else "TODAY"} PERFORMANCE OF PORTFOLIO 📈
"""
    
    # --- TAG SELECTION LOGIC ---
    # Goal: Max 5 tags total. Randomly select from Daily/Monthly/Yearly lists, 
    # prioritizing those NOT used in the last 36h (approx 25 tags).
    
    # 1. Collect all candidates
    candidates = []
    # Store as tuples: (symbol, category_priority) 
    # Using simple set later to avoid duplicates if a stock appears in multiple lists
    for item in daily_sorted: candidates.append(item[0])   # Top 5 Daily
    for item in monthly_sorted: candidates.append(item[0]) # Top 3 Monthly
    for item in yearly_sorted: candidates.append(item[0])  # Top 3 Yearly
    
    # Remove duplicates while preserving order
    unique_candidates = list(dict.fromkeys(candidates))
    
    # 2. Get recent history to exclude (last ~36h -> approx 25 tags)
    # 3 runs/day * 5 tags = 15 tags/day * 1.5 days = 22.5 -> round to 25
    recent_history = ai_news_generator.get_recent_tags(limit=25)
    normalized_history = set(t.replace('$', '').upper() for t in recent_history)
    
    # 3. Filter candidates available for tagging (not recently used)
    available_candidates = [c for c in unique_candidates if c.upper() not in normalized_history]
    
    # 4. Select tags for this run
    tags_selected_map = set() # Set of symbols to be tagged
    
    # If we have available candidates that haven't been used recently, pick from them
    if available_candidates:
        # Shuffle to give random chance to Monthly/Yearly if Daily are used
        # We take up to 5.
        # Note: If you prefer strict priority (Daily > Monthly > Yearly) remove shuffle.
        # User requested "randomico mettendo a pari priorità", so shuffle is correct.
        random.shuffle(available_candidates)
        
        # Take max 5
        selected = available_candidates[:5]
        tags_selected_map.update(selected)
    
    # (Optional fallback) If we have very few fresh candidates (e.g. < 2) and plenty of space, 
    # we *could* reuse some old ones, but it's better to leave the budget for AI news 
    # which might find something new. So we do nothing here.
    
    # --- FORMATTING WITH TAGS ---
    
    for etoro_symbol, data in daily_sorted:
        should_tag = etoro_symbol in tags_selected_map
        performance = data['weekly_change'] if is_weekly else data['daily_change']
        recap += format_ticker(etoro_symbol, data['company_name'], performance, use_tag=should_tag) + "\n"
    
    recap += "\nTOP 3 MONTHLY PERFORMANCE OF PORTFOLIO 📈\n"
    for etoro_symbol, data in monthly_sorted:
        should_tag = etoro_symbol in tags_selected_map
        recap += format_ticker(etoro_symbol, data['company_name'], data['monthly_change'], use_tag=should_tag) + "\n"
    
    recap += "\nTOP 3 HOLDING YEARLY PERFORMANCE OF PORTFOLIO 📈\n"
    for etoro_symbol, data in yearly_sorted:
        should_tag = etoro_symbol in tags_selected_map
        recap += format_ticker(etoro_symbol, data['company_name'], data['yearly_change'], use_tag=should_tag) + "\n"
    
    # Calculate used count and remaining budget
    tags_used_count = len(tags_selected_map)
    tag_budget_remaining = 5 - tags_used_count
    if tag_budget_remaining < 0: tag_budget_remaining = 0

    # Update rotation history immediately with the tags we just used
    if tags_selected_map:
        ai_news_generator.update_rotation_history(list(tags_selected_map))

    # Add AI-generated market news recap
    # We exclude: 
    # 1. Recently used tags (history)
    # 2. Tags just used in this run (tags_selected_map)
    # This forces AI to find truly fresh news/tickers if possible
    current_exclusions = list(set(recent_history + list(tags_selected_map)))
    
    print(f"Generating AI market news (Budget for tags: {tag_budget_remaining})...")
    ai_news = ai_news_generator.generate_market_news_recap(max_tags=tag_budget_remaining, excluded_tags=current_exclusions)
    if ai_news:
        recap += ai_news
    
    # Add fixed "why copy" message with performance data
    recap += ai_news_generator.get_why_copy_message(
        five_year_return=five_year_return,
        avg_yearly_return=avg_yearly_return,
        benchmark_performance=benchmark_data
    )
    
    return recap

