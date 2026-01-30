
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
import matplotlib.dates as mdates

def generate_performance_chart(portfolio_series, benchmark_df, output_path='output/performance_chart.png'):
    """
    Generate a line chart comparing portfolio performance vs benchmarks.
    
    Args:
        portfolio_series (pd.Series): Cumulative return of portfolio % (index is Date)
        benchmark_df (pd.DataFrame): Cumulative return of benchmarks % (index is Date, cols are tickers)
        output_path (str): Path to save the image
    """
    print("📊 Generating performance chart...")
    
    # Set style
    sns.set_theme(style="darkgrid")
    plt.figure(figsize=(12, 7))
    
    # Plot Portfolio
    if portfolio_series is not None and not portfolio_series.empty:
        # Resample portfolio to daily if it is monthly, using forward fill for step-like or interpolation
        # Actually linear interpolation might be misleading if we only have month-end.
        # But for visual comparison, simple line plot is fine.
        # Ensure index is datetime
        portfolio_series.index = pd.to_datetime(portfolio_series.index)
        
        plt.plot(portfolio_series.index, portfolio_series.values, 
                 label='My Portfolio', linewidth=3, color='#00C805', marker='o', markersize=4)
        
        # Add annotation for latest value
        last_date = portfolio_series.index[-1]
        last_val = portfolio_series.iloc[-1]
        plt.annotate(f'{last_val:.1f}%', xy=(last_date, last_val), 
                     xytext=(10, 0), textcoords='offset points', 
                     color='#00C805', fontweight='bold', fontsize=12)

    # Plot Benchmarks
    if benchmark_df is not None and not benchmark_df.empty:
        benchmark_df.index = pd.to_datetime(benchmark_df.index)
        
        # Define some colors for common benchmarks if needed, or let seaborn handle it
        # Try to match eToro colors if possible, or distinct ones
        palette = sns.color_palette("husl", len(benchmark_df.columns))
        
        for i, col in enumerate(benchmark_df.columns):
            # Drop NaNs to plot what we have
            series = benchmark_df[col].dropna()
            if series.empty:
                continue
                
            # Differentiate line styles
            linestyle = '-'
            if 'SPX' in col or 'NSDQ' in col:
                linestyle = '--' # Dashed for major indices
                
            plt.plot(series.index, series.values, label=col, linewidth=2, linestyle=linestyle, alpha=0.8)
            
            # Label at the end of line
            # last_date_b = series.index[-1]
            # last_val_b = series.iloc[-1]
            # plt.text(last_date_b, last_val_b, f' {col}', fontsize=8, verticalalignment='center')

    # Formatting of the chart
    plt.title('Performance Comparison (Since 2020)', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Cumulative Return (%)', fontsize=12)
    plt.legend(loc='upper left', fontsize=10, frameon=True, shadow=True)
    
    # Format X axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    plt.gca().xaxis.set_major_locator(mdates.YearLocator())
    
    # Add grid
    plt.grid(True, alpha=0.3)
    
    # Add y=0 line
    plt.axhline(0, color='black', linewidth=1, alpha=0.5)
    
    # Tight layout
    plt.tight_layout()
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Chart saved to {output_path}")
    return output_path
