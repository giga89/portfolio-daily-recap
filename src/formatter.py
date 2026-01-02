"""
Format the recap output in a nice readable format
"""

from datetime import datetime
from config import EMOJI_MAP
import os
import ai_news_generator


def get_emoji(etoro_symbol):
    """Get emoji for a given eToro symbol"""
    return EMOJI_MAP.get(etoro_symbol, '📊')


def format_ticker(etoro_symbol, company_name, performance, use_tag=False):
    """Format a ticker line with eToro link and performance"""
    emoji = get_emoji(etoro_symbol)
    symbol_str = f"${etoro_symbol}" if use_tag else etoro_symbol
    return f"{emoji} {symbol_str} {performance:+.2f}%"


def generate_recap(stock_data, portfolio_daily, sheets_data, benchmark_data=None):
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
    
    # Calculate top performers
    daily_sorted = sorted(stock_data.items(), key=lambda x: x[1]['daily_change'], reverse=True)[:5]
    monthly_sorted = sorted(stock_data.items(), key=lambda x: x[1]['monthly_change'], reverse=True)[:3]
    yearly_sorted = sorted(stock_data.items(), key=lambda x: x[1]['yearly_change'], reverse=True)[:3]

        # Get market session from environment variable
    market_session = os.getenv('MARKET_SESSION', 'Daily recap')
    
    # Determine dynamic header based on session
    session_upper = market_session.upper()
    if "OPEN" in session_upper:
        header = f"🌅 {session_upper} 📊"
    elif "RECAP" in session_upper:
        header = f"🌠 {session_upper} 🌙"
    else:
        header = f"✨ {session_upper} ✨"

    # Determine dynamic performance line
    if portfolio_daily > 2.0:
        perf_text = "🚀 TO THE MOON"
        perf_emoji = "🔥"
    elif portfolio_daily > 0.5:
        perf_text = "🍀 GREAT GREEN DAY"
        perf_emoji = "✅"
    elif portfolio_daily >= 0:
        perf_text = "🌿 SLIGHT GAINS"
        perf_emoji = "🌱"
    elif portfolio_daily > -0.5:
        perf_text = "📉 MINOR DIP"
        perf_emoji = "⚖️"
    elif portfolio_daily > -2.0:
        perf_text = "💀 ROUGH DAY"
        perf_emoji = "🩸"
    else:
        perf_text = "🧨 MARKET CRASH"
        perf_emoji = "🆘"

    recap = f"""{header}

{perf_emoji} {perf_emoji} {perf_emoji} {perf_text}: {portfolio_daily:+.2f}% {perf_emoji} {perf_emoji} {perf_emoji}

TOP 5 TODAY PERFORMANCE OF PORTFOLIO 📈
"""
    
    # Track used tags to enforce limit and rotation
    # We prioritize the Top 5 Daily, BUT ONLY IF they haven't been used recently
    daily_symbols = [item[0] for item in daily_sorted]
    
    # Get last 15 tags (covers roughly the last 3 runs/24h)
    # This prevents repeating the same Top 5 tags 3 times a day
    recent_history = ai_news_generator.get_recent_tags(limit=15)
    normalized_history = [t.replace('$', '').upper() for t in recent_history]
    
    tags_applied_in_list = []
    
    for etoro_symbol, data in daily_sorted:
        # Check if we should tag this symbol
        should_tag = False
        
        # Criteria:
        # 1. We haven't reached the limit of 5 for this run yet
        # 2. This symbol wasn't tagged recently (rotation)
        if len(tags_applied_in_list) < 5:
            if etoro_symbol.upper() not in normalized_history:
                should_tag = True
                tags_applied_in_list.append(etoro_symbol)
        
        recap += format_ticker(etoro_symbol, data['company_name'], data['daily_change'], use_tag=should_tag) + "\n"
    
    # Calculate remaining budget for AI
    tag_budget_remaining = 5 - len(tags_applied_in_list)
    if tag_budget_remaining < 0:
        tag_budget_remaining = 0

    recap += "\nTOP 3 MONTHLY PERFORMANCE OF PORTFOLIO 📈\n"
    for etoro_symbol, data in monthly_sorted:
        # Do not use tags for monthly/yearly to save budget and keep clean
        recap += format_ticker(etoro_symbol, data['company_name'], data['monthly_change'], use_tag=False) + "\n"
    
    recap += "\nTOP 3 HOLDING YEARLY PERFORMANCE OF PORTFOLIO 📈\n"
    for etoro_symbol, data in yearly_sorted:
        recap += format_ticker(etoro_symbol, data['company_name'], data['yearly_change'], use_tag=False) + "\n"
    
    # Update rotation history with tags used in Top 5 (this run)
    if tags_applied_in_list:
        ai_news_generator.update_rotation_history(tags_applied_in_list)

    # Add AI-generated market news recap
    # We pass the recently used tags + the ones showing in the list as "excluded"
    # so the AI doesn't repeat what we just showed OR what was shown recently
    current_exclusions = list(set(recent_history + tags_applied_in_list))
    
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

