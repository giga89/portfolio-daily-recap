"""
Format the recap output in a nice readable format
"""

from datetime import datetime
from config import EMOJI_MAP
import os


def get_emoji(etoro_symbol):
    """Get emoji for a given eToro symbol"""
    return EMOJI_MAP.get(etoro_symbol, '📊')


def format_ticker(etoro_symbol, company_name, performance):
    """Format a ticker line with eToro link and performance"""
    emoji = get_emoji(etoro_symbol)
    return f"{emoji} [${etoro_symbol} ({company_name})] {performance:+.2f}%"


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
    recap = f"""✨✨✨{market_session.upper()} PORTFOLIO ✨✨✨

    TODAY PERFORMANCE {{portfolio_daily:+.2f}}% {performance_emoji} {performance_emoji} {performance_emoji}
    # Choose emoji based on performance
    performance_emoji = "🍀" if portfolio_daily >= 0 else "💀"
    
{five_year_return:.0f}% SINCE CHANGE OF STRATEGY (2020) 🚀🚀🚀
{avg_yearly_return:.0f}% PER YEAR (DOUBLE YOUR MONEY IN {time_to_double:.2f} YEARS)

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
    
    return recap
