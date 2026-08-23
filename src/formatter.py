"""
Format the recap output in a nice readable format
"""

from datetime import datetime
from config import EMOJI_MAP
import os
import random
import ai_news_generator

# Russian stocks to exclude from all rankings and AI news (sanctioned/untradeable)
EXCLUDED_TICKERS = {'MNODL.L', 'NVTKL.L'}

# Import API usage tracker
try:
    from api_usage_tracker import save_usage_report
    API_TRACKER_AVAILABLE = True
except ImportError:
    API_TRACKER_AVAILABLE = False


def get_emoji(etoro_symbol):
    """Get emoji for a given eToro symbol"""
    return EMOJI_MAP.get(etoro_symbol, '📊')


def format_ticker(etoro_symbol, company_name, performance, use_tag=False):
    """Format a ticker line with eToro link and performance"""
    emoji = get_emoji(etoro_symbol)
    symbol_str = f"${etoro_symbol}" if use_tag else etoro_symbol
    return f"{emoji} {symbol_str} {performance:+.2f}%"


def generate_recap(stock_data, portfolio_daily, sheets_data, benchmark_data=None, portfolio_weekly=None, portfolio_monthly=None, ath_distance=None):
    """
    Generate the formatted daily recap matching the desired output format
    """
    print("Generating recap...")
    
    # Get today's date
    today = datetime.now().strftime('%d/%m/%Y')
    
    # Extract sheets data
    five_year_return = sheets_data['five_year_return']
    
    # Calculate CAGR (Compound Annual Growth Rate) from strategy change date (Jan 2020)
    from datetime import date
    strategy_start = date(2020, 1, 1)
    years_since_start = (date.today() - strategy_start).days / 365.25
    if years_since_start > 0 and five_year_return > 0:
        avg_yearly_return = ((1 + five_year_return / 100) ** (1 / years_since_start) - 1) * 100
    else:
        avg_yearly_return = 0
    
    # Get market session from environment variable
    market_session = os.getenv('MARKET_SESSION', 'Daily recap')
    is_weekly = "WEEKLY" in market_session.upper()
    is_monthly = "MONTHLY" in market_session.upper()
    
    # Check if we're in January (for special handling)
    current_month = datetime.now().month
    is_january = (current_month == 1)
    
    # Filter out assets with NaN values in any performance metric (safety net)
    import math
    nan_tickers = [k for k, v in stock_data.items()
                   if any(isinstance(v.get(m), float) and math.isnan(v.get(m, 0))
                          for m in ('daily_change', 'weekly_change', 'monthly_change', 'yearly_change'))]
    if nan_tickers:
        print(f"⚠️  Filtering out {len(nan_tickers)} assets with NaN values: {nan_tickers}")
        stock_data = {k: v for k, v in stock_data.items() if k not in nan_tickers}

    # Filter out excluded tickers (e.g. Russian stocks) from all rankings and news
    excluded_found = [k for k in stock_data if k in EXCLUDED_TICKERS]
    if excluded_found:
        print(f"🚫 Excluding {len(excluded_found)} tickers from recap: {excluded_found}")
        stock_data = {k: v for k, v in stock_data.items() if k not in EXCLUDED_TICKERS}

    # Calculate top performers
    # Filter for active trading today for the "Daily" list
    stock_data_active = {k: v for k, v in stock_data.items() if v.get('has_traded_today', True)}
    
    # If weekly, we use weekly_change for the "TOP 5" section
    # If monthly, we skip the daily/weekly section entirely
    if is_monthly:
        daily_sorted = []  # Skip daily performance for monthly recap
    elif is_weekly:
        daily_sorted = sorted(stock_data.items(), key=lambda x: x[1]['weekly_change'], reverse=True)[:5]
    else:
        # For daily, only show those that traded
        daily_sorted = sorted(stock_data_active.items(), key=lambda x: x[1]['daily_change'], reverse=True)[:5]
        
    print(f"Active assets today: {len(stock_data_active)}/{len(stock_data)}")
    
    # For monthly recap in January, show only YTD (since monthly = yearly)
    # Otherwise show both monthly and yearly
    if is_monthly and is_january:
        # In January, show only YTD (don't duplicate)
        monthly_sorted = []  # Skip monthly
        yearly_sorted = sorted(stock_data.items(), key=lambda x: x[1]['yearly_change'], reverse=True)[:5]
    else:
        monthly_sorted = sorted(stock_data.items(), key=lambda x: x[1]['monthly_change'], reverse=True)[:5 if is_monthly else 3]
        yearly_sorted = sorted(stock_data.items(), key=lambda x: x[1]['yearly_change'], reverse=True)[:5 if is_monthly else 3]

    
    # Determine dynamic header based on session
    session_upper = market_session.upper()
    if "MONTHLY" in session_upper:
        header = f"📅 RESOCONTO MENSILE PORTAFOGLIO 🗓️"
    elif "WEEKLY" in session_upper:
        if "SAT" in session_upper:
            header = f"📅 RESOCONTO SETTIMANALE (SABATO) 📆"
        elif "SUN" in session_upper:
            header = f"🏆 CLASSIFICA SETTIMANALE DEI TITOLI 📊"
        else:
            header = f"📅 RESOCONTO SETTIMANALE 📆"
    elif "OPEN" in session_upper:
        if "EUROPEAN" in session_upper:
            header = f"🌅 APERTURA MERCATI EUROPEI 🇪🇺"
        else:
            header = f"🌅 APERTURA WALL STREET 🇺🇸"
    elif "CLOSE" in session_upper:
        header = f"🌆 CHIUSURA DEI MERCATI 📈"
    elif "RECAP" in session_upper:
        header = f"🌠 RESOCONTO GIORNALIERO 🌙"
    else:
        header = f"✨ {market_session.upper()} ✨"

    # Determine dynamic performance line
    # Use monthly performance if this is a monthly recap, weekly if weekly, else daily
    if is_monthly:
        current_perf = portfolio_monthly if portfolio_monthly is not None else portfolio_daily
        period_label = "MESE"
    elif is_weekly and portfolio_weekly is not None:
        current_perf = portfolio_weekly
        period_label = "SETTIMANA"
    else:
        current_perf = portfolio_daily
        period_label = "GIORNATA"
    
    if current_perf > 2.0:
        perf_text = "PORTAFOGLIO IN VOLO! 🚀"
        perf_emoji = "🔥"
    elif current_perf > 0.5:
        perf_text = f"OTTIMA {period_label}! 🟢"
        perf_emoji = "✅"
    elif current_perf >= 0:
        perf_text = f"LIEVE CRESCITA 🌱"
        perf_emoji = "🌱"
    elif current_perf > -0.5:
        perf_text = f"STABILE / LIEVE CALO ⚖️"
        perf_emoji = "⚖️"
    elif current_perf > -2.0:
        perf_text = f"{period_label} DIFFICILE 🩸"
        perf_emoji = "🩸"
    else:
        perf_text = f"FORTE CORREZIONE! 🆘"
        perf_emoji = "🆘"

    recap = f"""{header}

{perf_emoji} {perf_emoji} {perf_emoji} {perf_text}: {current_perf:+.2f}% {perf_emoji} {perf_emoji} {perf_emoji}
"""
    
    # Optional: Display ATH distance
    if ath_distance is not None and ath_distance < 0:
        recap += f"🏔️ Distanza dal Massimo Storico (ATH): {ath_distance:.2f}%\n"
    elif ath_distance is not None and ath_distance >= 0:
        recap += f"🏔️ Nuovo Massimo Storico Raggiunto! 🎉\n"
        
    recap += "\n"
    
    # --- TAG SELECTION LOGIC ---
    # Goal: Max 4 tags total. Randomly select from Daily/Monthly/Yearly lists, 
    # prioritizing those NOT used in the last 36h (approx 20 tags).
    
    # 1. Collect all candidates
    candidates = []
    # Store as tuples: (symbol, category_priority) 
    # Using simple set later to avoid duplicates if a stock appears in multiple lists
    if not is_monthly:  # Only include daily if not monthly recap
        for item in daily_sorted: candidates.append(item[0])   # Top 5 Daily/Weekly
    for item in monthly_sorted: candidates.append(item[0]) # Top 3-5 Monthly
    for item in yearly_sorted: candidates.append(item[0])  # Top 3-5 Yearly
    
    # Remove duplicates while preserving order
    unique_candidates = list(dict.fromkeys(candidates))
    
    # 2. Get recent history to exclude (last ~36h -> approx 20 tags)
    # 3 runs/day * 4 tags = 12 tags/day * 1.5 days = 18 -> round to 20
    recent_history = ai_news_generator.get_recent_tags(limit=20)
    normalized_history = set(t.replace('$', '').upper() for t in recent_history)
    
    # 3. Filter candidates available for tagging (not recently used)
    available_candidates = [c for c in unique_candidates if c.upper() not in normalized_history]
    
    # Filter by region if morning open
    EUROPEAN_TICKERS = ['ENEL.MI', 'ENI.MI', 'PRY.MI', 'RACE', 'VOW3.DE', 'NOVO-B.CO', 'AZN.L', 'GLEN.L', 'TRIG.L', 'SX7PEX.DE', 'IEUR', 'WDEF.L']
    US_TICKERS = ['AMZN', 'AVGO', 'GOOG', 'LLY', 'MSFT', 'NET', 'PLTR', 'PYPL', 'TSM', 'ABBV', 'ABT', 'ABT.US', 'CCJ', 'HUM', 'MELI', 'IB01.L']
    
    if "EUROPEAN" in session_upper and "OPEN" in session_upper:
        available_candidates = [c for c in available_candidates if c.upper() in [t.upper() for t in EUROPEAN_TICKERS]]
    elif "U.S." in session_upper and "OPEN" in session_upper:
        available_candidates = [c for c in available_candidates if c.upper() in [t.upper() for t in US_TICKERS]]
    
    # Determine whether we should output the dry tables of top performers
    # Opening sessions and Saturday weekly recap should NOT show them; Daily Close and Sunday Recap DO show them.
    show_perf_lists = True
    if "OPEN" in session_upper or ("WEEKLY" in session_upper and "SAT" in session_upper):
        show_perf_lists = False

    # 4. Select tags for this run
    tags_selected_map = set() # Set of symbols to be tagged
    
    # Only select tags for the tables if we are showing the performance lists
    if show_perf_lists:
        # If we have available candidates that haven't been used recently, pick from them
        if available_candidates:
            random.shuffle(available_candidates)
            selected = available_candidates[:3]
            tags_selected_map.update(selected)
    
    # --- FORMATTING WITH TAGS ---

    if show_perf_lists:
        # Only show daily/weekly performance if not monthly recap
        if not is_monthly and daily_sorted:
            recap += f"MIGLIORI 5 {'SETTIMANALI' if is_weekly else 'DI OGGI'} DEL PORTAFOGLIO 📈\n"
            for etoro_symbol, data in daily_sorted:
                should_tag = etoro_symbol in tags_selected_map
                performance = data['weekly_change'] if is_weekly else data['daily_change']
                recap += format_ticker(etoro_symbol, data['company_name'], performance, use_tag=should_tag) + "\n"
            recap += "\n"
        
        # Show monthly performance (skip in January for monthly recap since it equals YTD)
        if monthly_sorted:
            recap += f"MIGLIORI {len(monthly_sorted)} PERFORMANCE MENSILI 📈\n"
            for etoro_symbol, data in monthly_sorted:
                should_tag = etoro_symbol in tags_selected_map
                recap += format_ticker(etoro_symbol, data['company_name'], data['monthly_change'], use_tag=should_tag) + "\n"
            recap += "\n"
        
        # Show yearly performance (always show for monthly recap, otherwise top 3)
        if yearly_sorted:
            yearly_label = "YTD" if (is_monthly and is_january) else ("DELL'ANNO" if is_monthly else "DI SEMPRE (YTD)")
            recap += f"MIGLIORI {len(yearly_sorted)} {yearly_label} DEL PORTAFOGLIO 📈\n"
            for etoro_symbol, data in yearly_sorted:
                should_tag = etoro_symbol in tags_selected_map
                recap += format_ticker(etoro_symbol, data['company_name'], data['yearly_change'], use_tag=should_tag) + "\n"
            recap += "\n"
    
    # Calculate used count and remaining budget
    tags_used_count = len(tags_selected_map)
    tag_budget_remaining = 4 - tags_used_count
    if tag_budget_remaining < 0: tag_budget_remaining = 0

    # Update rotation history immediately with the tags we just used
    if tags_selected_map:
        ai_news_generator.update_rotation_history(list(tags_selected_map))

    # Add AI-generated market news recap
    current_exclusions = list(set(recent_history + list(tags_selected_map)))
    
    # Use monthly AI recap for monthly sessions, daily for others
    if is_monthly:
        print(f"Generating monthly AI recap (Budget for tags: {tag_budget_remaining})...")
        ai_news = ai_news_generator.generate_monthly_ai_recap(max_tags=tag_budget_remaining, excluded_tags=current_exclusions)
    else:
        print(f"Generating AI market news (Budget for tags: {tag_budget_remaining}, Session: {market_session})...")
        ai_news = ai_news_generator.generate_market_news_recap(
            max_tags=tag_budget_remaining, 
            excluded_tags=current_exclusions,
            market_session=market_session
        )
    
    if ai_news:
        recap += ai_news
    
    # Add fixed "why copy" message with performance data (tags @AndreaRavalli only on US close)
    recap += ai_news_generator.get_why_copy_message(
        five_year_return=five_year_return,
        avg_yearly_return=avg_yearly_return,
        benchmark_performance=benchmark_data,
        market_session=market_session
    )
    
    # Enforce maximum recap length matching Telegram's 4000-character limit (using 3950 for safety)
    MAX_RECAP_LENGTH = 3950
    if len(recap) > MAX_RECAP_LENGTH:
        print(f"⚠️  Recap length ({len(recap)} chars) exceeds Telegram limit. Trimming...")
        # Trim at the last paragraph break that still fits, so we never cut mid-sentence
        cut = recap.rfind('\n\n', 0, MAX_RECAP_LENGTH - 50)
        if cut == -1:
            cut = recap.rfind('\n', 0, MAX_RECAP_LENGTH - 50)
        if cut == -1:
            cut = MAX_RECAP_LENGTH - 50
        recap = recap[:cut].rstrip()
        print(f"✅ Recap trimmed to {len(recap)} chars")
    else:
        print(f"✅ Recap length: {len(recap)} chars (within Telegram limit of {MAX_RECAP_LENGTH})")
    
    # Generate and save API usage report
    if API_TRACKER_AVAILABLE:
        try:
            save_usage_report()
            print("📊 API usage report generated")
        except Exception as e:
            print(f"⚠️  Could not generate API usage report: {e}")
    
    return recap

