#!/usr/bin/env python3
"""
Daily Portfolio Recap Generator - Main Orchestrator
Collects data from yfinance and Google Sheets to generate daily performance recap
"""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import finance_fetcher
import gist_storage
import formatter
import social_publisher
import chart_generator
import pie_chart_generator
import ai_cover_generator
import etoro_history

def main():
    """
    Main function to orchestrate data collection and recap generation
    """
    
    print("Starting daily portfolio recap generation...~")
    print("=" * 50)
    
    # Step 1: Get yfinance data for all symbols
    stock_data = finance_fetcher.fetch_stock_data()
    print(f"Successfully fetched data for {len(stock_data)} symbols")
    print("=" * 50)
    
    # Step 2: Calculate portfolio daily performance (will auto-fetch weights from BullAware)
    # We fetch weights once to reuse them for both Daily and YTD calculations
    print("📊 Fetching portfolio weights...")
    portfolio_weights = finance_fetcher.fetch_portfolio_weights_from_bullaware()
    
    portfolio_daily = finance_fetcher.calculate_portfolio_daily_change(stock_data, portfolio_weights)
    print(f"Portfolio daily performance: {portfolio_daily:.2f}%")
    print("=" * 50)
    
    # Step 2b: Get reliable Portfolio YTD (Annual Yield) from eToro public API
    # Data comes directly from eToro's stats page - no auth required
    print("📈 Fetching Portfolio YTD from eToro...")
    portfolio_ytd = finance_fetcher.fetch_portfolio_ytd_from_etoro()
    
    # Fallback to calculated YTD if BullAware fails
    if portfolio_ytd is None:
        print("⚠️ Falling back to calculated YTD from market data...")
        portfolio_ytd = finance_fetcher.calculate_portfolio_ytd(stock_data, portfolio_weights)
    
    # Step 3: Compute cumulative performance from eToro monthly history + YTD
    print("📊 Computing cumulative performance from eToro data...")
    port_hist_etoro = finance_fetcher.fetch_portfolio_history_from_etoro(start_year=2020)
    five_year_return = 156.0  # fallback (approx cumulative from 2020)
    if port_hist_etoro is not None and not port_hist_etoro.empty and portfolio_ytd is not None:
        current_year = pd.Timestamp.now().year
        prev_year_data = port_hist_etoro[port_hist_etoro.index.year < current_year]
        if not prev_year_data.empty:
            prev_year_end = float(prev_year_data.iloc[-1])
            five_year_return = round(((1 + prev_year_end / 100) * (1 + portfolio_ytd / 100) - 1) * 100, 2)
            print(f"✓ Cumulative performance: {five_year_return:.2f}% (prev year-end: {prev_year_end:.2f}%, YTD: {portfolio_ytd:.2f}%)")
        elif portfolio_ytd is not None:
            five_year_return = portfolio_ytd
    elif portfolio_ytd is not None:
        five_year_return = portfolio_ytd

    sheets_data = {
        'five_year_return': five_year_return,
        'monthly_performance': None,
        'yearly_performance': portfolio_ytd,
        'dividend': None
    }
    print("=" * 50)
    
    # Step 4: Get benchmark comparison data
    benchmark_data = finance_fetcher.fetch_benchmarks_performance(start_date='2020-01-01')
    print("=" * 50)
    
    # Step 4b: Calculate weekly/monthly performance if needed
    market_session = os.getenv('MARKET_SESSION', 'Daily recap')
    is_weekly = "WEEKLY" in market_session.upper()
    is_monthly = "MONTHLY" in market_session.upper()
    
    portfolio_weekly = None
    portfolio_monthly = None
    
    if is_weekly:
        print("📊 Calculating WEEKLY portfolio performance...")
        portfolio_weekly = finance_fetcher.calculate_portfolio_weighted_change(stock_data, portfolio_weights, metric='weekly_change')
        print("=" * 50)
    
    if is_monthly:
        print("📊 Calculating MONTHLY portfolio performance...")
        portfolio_monthly = finance_fetcher.calculate_portfolio_weighted_change(stock_data, portfolio_weights, metric='monthly_change')
        print("=" * 50)
    
    
    # Step 5: Generate Performance Chart
    print("📈 Generating performance comparison chart...")
    chart_path = None
    ath_distance = None
    try:
        current_perf = five_year_return

        # Load history from Gist (replaces Sheets "Storico" tab)
        port_hist_records = gist_storage.get_perf_history()

        if port_hist_records:
            df = pd.DataFrame(port_hist_records)
            df['Date'] = pd.to_datetime(df['date'])
            df.rename(columns={'perf': 'Performance', 'ath': 'ATH'}, inplace=True)
            port_hist = df[['Date', 'Performance', 'ATH']].reset_index(drop=True)
        else:
            port_hist = None

        # Seed from eToro monthly history if Gist is empty
        if port_hist is None or len(port_hist) < 2:
            print("   ⚠️ No history in Gist, seeding from eToro monthly data...")
            if port_hist_etoro is not None and not port_hist_etoro.empty:
                max_so_far = -999.0
                seed_records = []
                for index, current_cum in port_hist_etoro.items():
                    current_cum = float(current_cum)
                    if current_cum > max_so_far:
                        max_so_far = current_cum
                    seed_records.append({'date': index.strftime('%Y-%m-%d'), 'perf': current_cum, 'ath': max_so_far})
                gist_storage.seed_perf_history(seed_records)
                port_hist_records = gist_storage.get_perf_history()
                if port_hist_records:
                    df = pd.DataFrame(port_hist_records)
                    df['Date'] = pd.to_datetime(df['date'])
                    df.rename(columns={'perf': 'Performance', 'ath': 'ATH'}, inplace=True)
                    port_hist = df[['Date', 'Performance', 'ATH']].reset_index(drop=True)

        ath_value = current_perf
        if port_hist is not None and not port_hist.empty:
            max_hist_perf = port_hist['Performance'].max()
            ath_value = float(max(max_hist_perf, current_perf))
            current_perf_float = float(current_perf)

            # Upsert today's snapshot into Gist
            today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
            gist_storage.upsert_perf_record(today_str, current_perf_float, ath_value)

            # Prepare deduplicated series for chart
            port_hist = port_hist.drop_duplicates(subset='Date', keep='last')
            port_hist.set_index('Date', inplace=True)
            port_series = port_hist['Performance']

            bench_hist = finance_fetcher.fetch_benchmarks_history(start_date='2020-01-01')
            if not bench_hist.empty:
                chart_path = chart_generator.generate_performance_chart(port_series, bench_hist)

            ath_distance = current_perf_float - ath_value
            if ath_distance >= 0:
                ath_distance = 0.0  # True new ATH
            print(f"📊 Calculated ATH Distance: {ath_distance:.2f}% (ATH: {ath_value:.2f}%, Current: {current_perf_float:.2f}%)")
        else:
            print("⚠️ Skipping chart generation due to missing data")

    except Exception as e:
        print(f"❌ Error generating chart: {e}")
        import traceback
        traceback.print_exc()

    # Step 6: Generate formatted recap
    recap = formatter.generate_recap(
        stock_data, 
        portfolio_daily, 
        sheets_data, 
        benchmark_data, 
        portfolio_weekly=portfolio_weekly,
        portfolio_monthly=portfolio_monthly,
        ath_distance=ath_distance
    )
    
    # Step 7: Save to file
    os.makedirs('output', exist_ok=True)
    output_path = 'output/recap.txt'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(recap)
    
    print(f"Recap saved to {output_path}")
    print("=" * 50)
    print("RECAP OUTPUT:")
    print("=" * 50)
    print(recap)
    print("=" * 50)
    print("Daily portfolio recap generation completed successfully!")

    # Step 8: Publish to all social platforms
    print("=" * 50)
    print("Publishing recap to social platforms...")

    # Generate AI cover image for the session
    ai_cover_path = None
    try:
        # Use the first ~300 chars of recap as context for image mood
        recap_summary = recap[:300] if recap else ""
        ai_cover_path = ai_cover_generator.generate_session_cover(
            session_name=market_session,
            recap_summary=recap_summary,
            portfolio_daily=portfolio_daily,
            output_path='output/ai_cover.png',
        )
    except Exception as exc:
        print(f"⚠️ AI cover image generation failed: {exc}")

    # Generate pie chart (alternates each session via Gist counter)
    pie_chart_path = None
    try:
        pie_type = gist_storage.get_next_pie_chart_type()
        print(f"🥧 Generating pie chart: {pie_type}")
        os.makedirs('output', exist_ok=True)
        if pie_type == 'allocation':
            pie_chart_path = pie_chart_generator.generate_allocation_pie(
                portfolio_weights or {}, 'output/pie_allocation.png'
            )
        elif pie_type == 'sector':
            pie_chart_path = pie_chart_generator.generate_sector_pie(
                portfolio_weights or {}, 'output/pie_sector.png'
            )
        elif pie_type == 'geo':
            pie_chart_path = pie_chart_generator.generate_geo_pie(
                portfolio_weights or {}, 'output/pie_geo.png'
            )
        elif pie_type == 'pnl_history':
            history = etoro_history.get_history_from_gist()
            pnl_by_type = history.get('stats', {}).get('pnl_by_type', {})
            if pnl_by_type:
                pie_chart_path = pie_chart_generator.generate_pnl_history_pie(
                    pnl_by_type, 'output/pie_pnl_history.png'
                )
    except Exception as exc:
        print(f"⚠️ Pie chart generation failed: {exc}")

    social_publisher.publish_all(
        recap_file_path=output_path,
        image_path=chart_path,
        pie_chart_path=pie_chart_path,
        ai_cover_path=ai_cover_path,
        data={
            "portfolio_daily": portfolio_daily,
            "stock_data": stock_data,
            "portfolio_weights": portfolio_weights or {},
            "portfolio_perf": five_year_return,
            "portfolio_weekly": portfolio_weekly,
        }
    )
    print("=" * 50)

if __name__ == '__main__':
    main()
