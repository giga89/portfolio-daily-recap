#!/usr/bin/env python3
"""
Daily Portfolio Recap Generator - Main Orchestrator
Collects data from yfinance and Google Sheets to generate daily performance recap
"""

import os
import sys
import math
from typing import Tuple

# Add src directory to path
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import finance_fetcher
import gist_storage
import formatter
import social_publisher
import chart_generator
import pie_chart_generator
import cover_generator
import winners_losers_card
import etoro_history

def _fetch_etoro_current_month_gain():
    """
    Fetch the real monthly gain for the current month directly from eToro
    via etoro_client.fetch_gain_history(granularity='monthly').

    Returns:
        float: monthly gain % (e.g. -2.35 means -2.35%), or None if unavailable.
    """
    try:
        import etoro_client
        if not etoro_client.is_configured():
            print("⚠️  _fetch_etoro_current_month_gain: etoro_client not configured")
            return None

        from datetime import datetime
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        target_prefix = f"{current_year}-{current_month:02d}"

        # Strategy 1: fetch_gain_history monthly array
        gain_history = etoro_client.fetch_gain_history(granularity="monthly")
        if gain_history:
            print(f"   📋 gain_history entries: {len(gain_history)}")
            # Log the last 3 entries to see date format
            for entry in gain_history[-3:]:
                print(f"      sample entry: date={entry.get('date','?')} gain={entry.get('gain','?')}")
            for entry in gain_history:
                date_str = str(entry.get('date', ''))
                if date_str.startswith(target_prefix):
                    gain = float(entry.get('gain', 0.0))
                    print(f"✓ eToro real monthly gain (gain_history): {gain:+.2f}% (date: {date_str})")
                    return gain
            print(f"⚠️  No entry found for prefix '{target_prefix}' in gain_history")

        # Strategy 2: fetch_trader_rankings with period=CurrMonth
        print("   Trying fetch_trader_rankings(period='CurrMonth')...")
        rankings = etoro_client.fetch_trader_rankings(period="CurrMonth")
        if rankings and "gain" in rankings:
            gain_val = float(rankings["gain"]) * 100.0
            print(f"✓ eToro real monthly gain (rankings CurrMonth): {gain_val:+.2f}%")
            return gain_val

        return None
    except Exception as e:
        print(f"⚠️  _fetch_etoro_current_month_gain error: {e}")
        import traceback
        traceback.print_exc()
        return None



def _is_symbol_degraded(info: dict) -> bool:
    """Return True if a symbol's metrics were marked degraded or are all zero/non-finite."""
    if not isinstance(info, dict):
        return True
    if info.get('data_degraded') is True:
        return True
    metrics = ('daily_change', 'weekly_change', 'monthly_change', 'yearly_change')
    for m in metrics:
        val = info.get(m, 0.0)
        try:
            fval = float(val)
        except (TypeError, ValueError):
            return True
        if not math.isfinite(fval):
            return True
        if abs(fval) >= 1e-9:
            return False
    return True


def validate_session_market_data(stock_data: dict, market_session: str) -> Tuple[bool, str]:
    """
    Pre-publication circuit breaker checking that fetched market data is not
    degraded (e.g., Yahoo Finance overnight Close=NaN collapsed to 0.0) and
    matches the expected active exchange for live US/EU market sessions.
    """
    if not stock_data:
        return False, "No stock data fetched (0 symbols)"

    total_symbols = len(stock_data)
    degraded_count = sum(1 for info in stock_data.values() if _is_symbol_degraded(info))
    if total_symbols >= 10 and (degraded_count / total_symbols) >= 0.50:
        return (
            False,
            f"Catastrophic market data degradation: {degraded_count}/{total_symbols} "
            f"symbols have degraded/all-zero metrics",
        )

    session_upper = (market_session or "").upper()
    if "U.S. MARKET" in session_upper and ("CLOSE" in session_upper or "OPEN" in session_upper):
        us_stocks = {
            k: v for k, v in stock_data.items()
            if isinstance(v, dict) and v.get("is_us_stock") and k != "TRX"
        }
        if len(us_stocks) >= 5:
            active_us = [
                k for k, v in us_stocks.items()
                if v.get("has_traded_today") and not v.get("data_degraded")
            ]
            non_zero_us = [
                k for k in active_us
                if abs(float(us_stocks[k].get("daily_change", 0.0))) > 1e-6
            ]
            min_active = max(3, int(len(us_stocks) * 0.30))
            if len(active_us) < min_active or len(non_zero_us) < 3:
                return (
                    False,
                    f"Insufficient active US market data for '{market_session}': "
                    f"{len(active_us)}/{len(us_stocks)} active, {len(non_zero_us)} non-zero",
                )

    if "EUROPEAN" in session_upper and "OPEN" in session_upper:
        eu_exts = (".L", ".PA", ".MI", ".DE", ".AS", ".CO")
        eu_stocks = {
            k: v for k, v in stock_data.items()
            if isinstance(v, dict)
            and any(str(v.get("yahoo_ticker", k)).endswith(ext) for ext in eu_exts)
        }
        if len(eu_stocks) >= 5:
            active_eu = [
                k for k, v in eu_stocks.items()
                if v.get("has_traded_today") and not v.get("data_degraded")
            ]
            non_zero_eu = [
                k for k in active_eu
                if abs(float(eu_stocks[k].get("daily_change", 0.0))) > 1e-6
            ]
            if len(non_zero_eu) < 2:
                return (
                    False,
                    f"Insufficient active EU market data for '{market_session}': "
                    f"{len(non_zero_eu)}/{len(eu_stocks)} non-zero",
                )

    return True, "OK"


def main():

    """
    Main function to orchestrate data collection and recap generation
    """
    market_session = os.getenv('MARKET_SESSION', 'Daily recap')
    print("=" * 60)
    print(f"Starting portfolio session: '{market_session}'")
    print(f"Timestamp: {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    # ── Check Market Holidays & Special Routing ─────────────────────────────
    import market_calendar
    holiday_action = market_calendar.should_skip_or_meme_session(market_session)

    if holiday_action["action"] == "SKIP":
        print(f"🛑 SESSION SKIPPED: {holiday_action['reason']}")
        os.makedirs('output', exist_ok=True)
        with open('output/recap.txt', 'w', encoding='utf-8') as f:
            f.write(f"🛑 SESSION SKIPPED: {holiday_action['reason']}\n")
        print("Done. Exiting cleanly.")
        sys.exit(0)

    if holiday_action["action"] == "HOLIDAY_MEME":
        print(f"🏖️ HOLIDAY DETECTED: {holiday_action['holiday_name']} ({holiday_action['market']} markets closed)")
        print(f"🎭 Publishing Holiday Theme Meme card for '{market_session}'...")
        res = market_calendar.publish_holiday_meme_session(
            session_name=market_session,
            holiday_name=holiday_action["holiday_name"],
            market=holiday_action["market"],
            output_dir='output'
        )
        print("Holiday Meme session completed successfully:", res)
        sys.exit(0)

    # Step 1: Get yfinance data for all symbols
    stock_data = finance_fetcher.fetch_stock_data()
    print(f"Successfully fetched data for {len(stock_data)} symbols")

    data_ok, data_reason = validate_session_market_data(stock_data, market_session)
    if not data_ok:
        if os.getenv('FORCE_RUN', '').lower() == 'true':
            print(f"⚠️ FORCE_RUN active: bypassing data-quality circuit breaker ({data_reason})")
        else:
            print(f"🛑 DATA QUALITY CIRCUIT BREAKER TRIGGERED: {data_reason}")
            sys.exit(1)

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
        print("📊 Fetching MONTHLY portfolio performance from eToro (real gain)...")
        portfolio_monthly = _fetch_etoro_current_month_gain()
        if portfolio_monthly is not None:
            print(f"✓ eToro real monthly gain: {portfolio_monthly:+.2f}%")
        else:
            print("⚠️ eToro monthly gain unavailable, falling back to yfinance weighted average...")
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

    # Generate cover image for the session
    ai_cover_path = None
    try:
        portfolio_perf_for_cover = portfolio_monthly if is_monthly else (portfolio_weekly if is_weekly and portfolio_weekly is not None else portfolio_daily)
        ai_cover_path = cover_generator.generate_cover(
            session_name=market_session,
            portfolio_daily=portfolio_perf_for_cover,
            output_path='output/ai_cover.png',
        )
    except Exception as exc:
        print(f"Warning: cover image generation failed: {exc}")

    # Generate Top & Flop card or Market Meme Card
    engagement_card_path = None
    try:
        import random
        import meme_generator
        from config import EMOJI_MAP

        # Contextual meme rotation:
        # - For monthly recap, always show the Winners & Losers card with monthly change
        # - Movimenti più marcati (|daily| >= 0.5%): 66% chance for sentiment meme
        # - Movimento contenuto (-0.5% < daily < 0.5%): 33% chance la sera (e 33% altre sessioni)
        use_meme = False if is_monthly else meme_generator.should_use_meme(
            portfolio_daily=portfolio_daily,
            market_session=market_session,
            is_weekly=is_weekly,
        )

        if use_meme:
            print(f"🎭 Generating Contextual Market Meme Card (daily move: {portfolio_daily:+.2f}%)...")
            top_performers = social_publisher._extract_top_performers("", stock_data)
            engagement_card_path = meme_generator.generate_meme_card(
                portfolio_daily=portfolio_daily,
                top_performers=top_performers,
                lang="it",
                is_weekend=is_weekly,
            )
        else:
            print("📊 Generating Top & Flop (Winners & Losers) Card...")
            engagement_card_path = winners_losers_card.build_card_from_stock_data(
                stock_data=stock_data,
                session_name=market_session,
                emoji_map=EMOJI_MAP,
                output_path='output/winners_losers.png',
            )
    except Exception as exc:
        print(f"Warning: Visual card generation failed: {exc}")

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
        engagement_card_path=engagement_card_path,
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
