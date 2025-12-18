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


def format_ticker(etoro_symbol, company_name, performance):
    """Format a ticker line with eToro link and performance"""
    emoji = get_emoji(etoro_symbol)
    return f"{emoji} ${etoro_symbol} {performance:+.2f}%"


def generate_recap(stock_data, portfolio_daily, sheets_data):
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
    time_to_double = 72 / avg_yearly_return if avg_yearly_return > 0 else 0
    
    # Calculate top performers
    daily_sorted = sorted(stock_data.items(), key=lambda x: x[1]['daily_change'], reverse=True)[:5]
    monthly_sorted = sorted(stock_data.items(), key=lambda x: x[1]['monthly_change'], reverse=True)[:3]
    yearly_sorted = sorted(stock_data.items(), key=lambda x: x[1]['yearly_change'], reverse=True)[:3]

        # Get market session from environment variable
    market_session = os.getenv('MARKET_SESSION', 'Daily recap')
    
    # Build the recap text
    performance_emoji = "🍀" if portfolio_daily >= 0 else "💀"

    recap = f"""✨✨✨{market_session.upper()} PORTFOLIO ✨✨✨

{performance_emoji} {performance_emoji} {performance_emoji} TODAY PERFORMANCE {portfolio_daily:+.2f}% {performance_emoji} {performance_emoji} {performance_emoji}

TOP 5 TODAY PERFORMANCE OF PORTFOLIO 📈
"""
    
    for etoro_symbol, data in daily_sorted:
        recap += format_ticker(etoro_symbol, data['company_name'], data['daily_change']) + "\n"
    
    recap += "\nTOP 3 MONTHLY PERFORMANCE OF PORTFOLIO 📈\n"
    for etoro_symbol, data in monthly_sorted:
        recap += format_ticker(etoro_symbol, data['company_name'], data['monthly_change']) + "\n"
    
    recap += "\nTOP 3 HOLDING YEARLY PERFORMANCE OF PORTFOLIO 📈\n"
    for etoro_symbol, data in yearly_sorted:
        recap += format_ticker(etoro_symbol, data['company_name'], data['yearly_change']) + "\n"
    
    recap += "\n@AndreaRavalli\n"
    
    # Add AI-generated market news recap
    print("Generating AI market news...")
    ai_news = ai_news_generator.generate_market_news_recap()
    if ai_news:
        recap += ai_news
    
    # Add fixed "why copy" message with performance data
    recap += ai_news_generator.get_why_copy_message(
        five_year_return=five_year_return,
        avg_yearly_return=avg_yearly_return
    )
    
    return recap

