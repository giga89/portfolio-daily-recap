"""
Configuration file for portfolio ticker mappings, company names, and emoji
"""

from portfolio_manager import get_tickers, get_emojis

# Load dynamically from JSON
try:
    PORTFOLIO_TICKERS = get_tickers()
    EMOJI_MAP = get_emojis()
except Exception:
    # Fallback if manager fails or during migration
    PORTFOLIO_TICKERS = {}
    EMOJI_MAP = {}

# Google Sheets configuration
GOOGLE_SHEETS_ID = '1jK6MlFxO6Im0eBfUP1eOjzW0Nii87jABEHiBnsjP52U'
FIVE_YEAR_CELL = 'G6'
MONTHLY_PERFORMANCE_CELL = 'G7'  # Add if you have monthly data
YEARLY_PERFORMANCE_CELL = 'G8'   # Add if you have yearly data
DIVIDEND_CELL = 'G9'              # Add if you have dividend data

# Benchmarks for comparison
BENCHMARKS = {
    'SPX500': '^GSPC',
    'NSDQ100': '^NDX',
    'SWDA.L': 'SWDA.L',
    'EUSTX50': '^STOXX50E',
    'CHINA50': 'FXI'  # Using FXI as a proxy for China 50 on eToro
}
