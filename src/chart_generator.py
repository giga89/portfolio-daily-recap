
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
    
    # Set dark theme
    plt.style.use('dark_background')
    sns.set_theme(style="darkgrid")
    
    fig = plt.figure(figsize=(12, 7), facecolor='#0a0a0a')
    ax = plt.gca()
    ax.set_facecolor('#0f0f0f')
    
    # Customize grid for dark theme
    ax.grid(True, alpha=0.15, color='#333333', linestyle='-', linewidth=0.5)
    
    # Plot Portfolio - Make it stand out!
    if portfolio_series is not None and not portfolio_series.empty:
        # Ensure index is datetime
        portfolio_series.index = pd.to_datetime(portfolio_series.index)
        
        # Bold, prominent line for portfolio with higher z-order to be on top
        plt.plot(portfolio_series.index, portfolio_series.values, 
                 label='💼 My Portfolio', 
                 linewidth=5, 
                 color='#00C805', 
                 marker='o', 
                 markersize=6,
                 markeredgewidth=2,
                 markeredgecolor='white',
                 zorder=10,  # Ensure it's drawn on top
                 alpha=1.0)
        
        # Add annotation for latest value
        last_date = portfolio_series.index[-1]
        last_val = portfolio_series.iloc[-1]
        plt.annotate(f'{last_val:.1f}%', xy=(last_date, last_val), 
                     xytext=(10, 0), textcoords='offset points', 
                     color='#00FF00', fontweight='bold', fontsize=13,
                     bbox=dict(boxstyle='round,pad=0.5', facecolor='#1a1a1a', edgecolor='#00FF00', alpha=0.95))

    # Plot Benchmarks - Uniform dashed style for all
    if benchmark_df is not None and not benchmark_df.empty:
        benchmark_df.index = pd.to_datetime(benchmark_df.index)
        
        # Use a muted color palette for benchmarks
        palette = sns.color_palette("muted", len(benchmark_df.columns))
        
        for i, col in enumerate(benchmark_df.columns):
            # Drop NaNs to plot what we have
            series = benchmark_df[col].dropna()
            if series.empty:
                continue
                
            # All benchmarks use dashed lines with uniform styling
            plt.plot(series.index, series.values, 
                     label=col, 
                     linewidth=1.5, 
                     linestyle='--',  # All dashed
                     alpha=0.6,  # More transparent
                     color=palette[i],
                     zorder=5)  # Behind the portfolio line
            
            # Label at the end of line
            # last_date_b = series.index[-1]
            # last_val_b = series.iloc[-1]
            # plt.text(last_date_b, last_val_b, f' {col}', fontsize=8, verticalalignment='center')

    # Formatting of the chart
    plt.title('Performance Comparison (Since 2020)', fontsize=16, fontweight='bold', pad=20, color='white')
    plt.xlabel('Date', fontsize=12, color='#cccccc')
    plt.ylabel('Cumulative Return (%)', fontsize=12, color='#cccccc')
    
    # Style the legend for dark theme
    legend = plt.legend(loc='upper left', fontsize=10, frameon=True, shadow=False, 
                       facecolor='#1a1a1a', edgecolor='#333333')
    plt.setp(legend.get_texts(), color='white')
    
    # Format X axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.tick_params(colors='#cccccc')
    
    # Add y=0 line
    plt.axhline(0, color='#555555', linewidth=1, alpha=0.7, linestyle='--')
    
    # Tight layout
    plt.tight_layout()
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Chart saved to {output_path}")
    return output_path
