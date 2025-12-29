"""
Configuration file for portfolio ticker mappings, company names, and emoji
"""

# Portfolio symbols mapping: eToro symbol -> (Yahoo Finance ticker, Company Name)
PORTFOLIO_TICKERS = {
    # ETFs
    'SX7PEX.DE': ('EXV1.DE', 'iShares STOXX Europe 600 Banks UCITS ETF'),
    'IEUR': ('IEUR', 'iShares Core MSCI Europe UCITS ETF'),
    'IQQL.DE': ('IQQL.DE', 'iShares MSCI World Quality Factor UCITS ETF'),
    'IEMG': ('IEMG', 'iShares Core MSCI Emerging Markets ETF'),
    'WDEF.L': ('WDEF.L', 'WisdomTree Europe Equity Income UCITS ETF'),
    
    # Healthcare & Pharmaceuticals
    'AZN.L': ('AZN.L', 'AstraZeneca'),
    'ABT': ('ABT', 'Abbott Laboratories'),
    'ABBV': ('ABBV', 'AbbVie'),
    'LLY': ('LLY', 'Eli Lilly & Co'),
    'NOVO-B.CO': ('NVO', 'Novo Nordisk'),
    'HUM': ('HUM', 'Humana'),
    
    # Technology & Semiconductors
    'AVGO': ('AVGO', 'Broadcom Inc'),
    'NVDA': ('NVDA', 'NVIDIA'),
    'TSM': ('TSM', 'Taiwan Semiconductor'),
    'MSFT': ('MSFT', 'Microsoft'),
    'SNPS': ('SNPS', 'Synopsys'),
    'AMZN': ('AMZN', 'Amazon'),
    'GOOG': ('GOOGL', 'Alphabet'),
    'PLTR': ('PLTR', 'Palantir Technologies Inc'),
    'NET': ('NET', 'Cloudflare'),
    
    # Energy & Nuclear
    'CCJ': ('CCJ', 'Cameco'),
    'ENEL.MI': ('ENEL.MI', 'Enel'),
    
    # Crypto
    'TRX': ('TRX-USD', 'TRON'),
    'ETOR': ('ETOR', 'Etoro'),
    
    # Financial Services & Others
    'DB1.DE': ('DB1.DE', 'Deutsche Börse AG'),
    'TRIG.L': ('TRIG.L', 'Trig PLC'),
    'BHP.L': ('BHP', 'BHP Group'),
    'PRY.MI': ('PRY.MI', 'Prysmian'),
    'RACE': ('RACE', 'Ferrari'),
    'VOW3.DE': ('VOW3.DE', 'Volkswagen'),
    'MELI': ('MELI', 'MercadoLibre'),
    'PYPL': ('PYPL', 'PayPal'),
    'GLEN': ('GLEN.L', 'Glencore'),
    '1919.HK': ('1919.HK', 'COSCO SHIPPING Holdings'),
    '2318.HK': ('2318.HK', 'Ping An Insurance'),
}

# Emoji mapping for each eToro symbol
EMOJI_MAP = {
    # ETFs
    'SX7PEX.DE': '📊',
    'VWCE.L': '🌐',
    'IEUR': '🏦',
    'IQQL.DE': '🔥',
    'IEMG': '🌍',
    'WDEF.L': '💼',
    
    # Healthcare & Pharmaceuticals
    'AZN.L': '🧬',
    'ABT': '🏥',
    'ABBV': '💉',
    'LLY': '💊',
    'NOVO-B': '💉',
    'HUM': '🏥',
    
    # Technology & Semiconductors
    'AVGO': '💻',
    'NVDA': '🤖',
    'TSM': '🏭',
    'MSFT': '💻',
    'SNPS': '🖥️',
    'AMZN': '📦',
    'GOOG': '🔍',
    'PLTR': '🛡️',
    'NET': '☁️',
    
    # Energy & Nuclear
    'CCJ': '⚡',
    'ENEL.MI': '🔋',
    
    # Crypto
    'TRX': '🪙',
    'ETOR': '🏛️',
    
    # Financial Services & Others
    'DB1.DE': '📊',
    'TRIG.L': '🔺',
    'BHPL': '⛏️',
    'PRY.MI': '🔌',
    'RACE': '🏎️',
    'VOW3.DE': '🚗',
    'MELI': '🛒',
    'PYPL': '💳',
    'GLEN': '⛏️',
    '1919.HK': '🚢',
    '2318.HK': '🏦',
}

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
