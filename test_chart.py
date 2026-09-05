#!/usr/bin/env python3
"""
Quick test script to generate and preview the performance chart
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chart_generator import generate_performance_chart

def generate_test_chart():
    """Generate a test chart with sample data"""
    print("📊 Generating test performance chart...")
    print("=" * 60)
    
    # Create sample portfolio data (monthly returns since 2020)
    dates = pd.date_range(start='2020-01-01', end='2026-01-31', freq='ME')
    
    # Simulate portfolio performance (strong growth with volatility)
    portfolio_returns = [0]
    base_return = 1.0
    for i in range(1, len(dates)):
        # Simulate monthly growth with some volatility
        monthly_growth = 1.015 + (i % 12) * 0.005  # Average 1.5% per month with seasonal variation
        base_return *= monthly_growth
        portfolio_returns.append((base_return - 1) * 100)
    
    portfolio_series = pd.Series(portfolio_returns, index=dates, name='My Portfolio')
    
    # Create benchmark data (daily for smoother lines)
    dates_daily = pd.date_range(start='2020-01-01', end='2026-01-31', freq='D')
    
    benchmark_data = {}
    
    # S&P 500 - steady growth
    spx_returns = [(1.10 ** (i / 365.25) - 1) * 100 for i in range(len(dates_daily))]
    benchmark_data['SPX500'] = pd.Series(spx_returns, index=dates_daily)
    
    # NASDAQ - higher growth
    nsdq_returns = [(1.15 ** (i / 365.25) - 1) * 100 for i in range(len(dates_daily))]
    benchmark_data['NSDQ100'] = pd.Series(nsdq_returns, index=dates_daily)
    
    # SWDA - moderate growth
    swda_returns = [(1.08 ** (i / 365.25) - 1) * 100 for i in range(len(dates_daily))]
    benchmark_data['SWDA.L'] = pd.Series(swda_returns, index=dates_daily)
    
    # EUROSTOXX50 - lower growth
    eur_returns = [(1.05 ** (i / 365.25) - 1) * 100 for i in range(len(dates_daily))]
    benchmark_data['EUSTX50'] = pd.Series(eur_returns, index=dates_daily)
    
    # CHINA50 - volatile
    china_returns = [(1.03 ** (i / 365.25) - 1) * 100 for i in range(len(dates_daily))]
    benchmark_data['CHINA50'] = pd.Series(china_returns, index=dates_daily)
    
    benchmark_df = pd.DataFrame(benchmark_data)
    
    # Generate the chart
    output_path = 'output/performance_chart.png'
    chart_path = generate_performance_chart(portfolio_series, benchmark_df, output_path)
    
    print(f"\n✅ Chart generated successfully!")
    print(f"📁 Saved to: {chart_path}")
    print(f"📊 Portfolio final return: {portfolio_returns[-1]:.1f}%")
    print("=" * 60)
    
    return chart_path

if __name__ == '__main__':
    generate_test_chart()
