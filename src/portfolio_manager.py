
import json
import os
import yfinance as yf

# DEFAULT DATA MOVED HERE TO AVOID CIRCULAR IMPORT WITH CONFIG.PY
DEFAULT_TICKERS = {
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
    'MAU.PA': ('MAU.PA', 'Etablissements Maurel & Prom SA'),
    'PRY.MI': ('PRY.MI', 'Prysmian'),
    'RACE': ('RACE', 'Ferrari'),
    'VOW3.DE': ('VOW3.DE', 'Volkswagen'),
    'MELI': ('MELI', 'MercadoLibre'),
    'PYPL': ('PYPL', 'PayPal'),
    'GLEN.L': ('GLEN.L', 'Glencore'),
    '1919.HK': ('1919.HK', 'COSCO SHIPPING Holdings'),
    '2318.HK': ('2318.HK', 'Ping An Insurance'),
}

DEFAULT_EMOJIS = {
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
    'MAU.PA': '🛢️',
    'PRY.MI': '🔌',
    'RACE': '🏎️',
    'VOW3.DE': '🚗',
    'MELI': '🛒',
    'PYPL': '💳',
    'GLEN.L': '⛏️',
    '1919.HK': '🚢',
    '2318.HK': '🏦',
}

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../portfolio_config.json')

def load_config():
    """Load portfolio configuration from JSON, migrating from defaults if needed."""
    if not os.path.exists(CONFIG_FILE):
        return migrate_from_defaults()
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file: {e}")
        return migrate_from_defaults()

def migrate_from_defaults():
    """Create JSON config from the defaults."""
    config_data = {
        "tickers": DEFAULT_TICKERS,
        "emojis": DEFAULT_EMOJIS
    }
    save_config(config_data)
    return config_data

def save_config(data):
    """Save configuration to JSON."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)
    print(f"✅ Portfolio configuration saved to {CONFIG_FILE}")

def get_tickers():
    """Get the active tickers dictionary."""
    return load_config().get('tickers', {})

def get_emojis():
    """Get the emoji mapping."""
    return load_config().get('emojis', {})

def lookup_ticker_info(symbol):
    """
    Attempt to find valid Yahoo Finance ticker and name for a given symbol.
    Returns (yahoo_ticker, name) or None if validation fails.
    """
    candidates = [symbol]
    
    # Heuristics for common variations
    if not '.' in symbol:
        candidates.append(f"{symbol}-USD")  # Crypto
        candidates.append(f"{symbol}.L")    # London
        candidates.append(f"{symbol}.DE")   # Germany
        candidates.append(f"{symbol}.MI")   # Milan
    
    print(f"🔎 Attempting to resolve details for new asset: {symbol}")
    
    for cand in candidates:
        try:
            ticker = yf.Ticker(cand)
            # Fetch minimal data to verify
            info = ticker.info
            # Check if it has a valid price or name
            if info and ('regularMarketPrice' in info or 'currentPrice' in info):
                name = info.get('longName', info.get('shortName', symbol))
                print(f"   ✓ Found match: {cand} ({name})")
                return cand, name
        except Exception:
            continue
            
    print(f"   ⚠️ Could not automatically resolve Yahoo ticker for {symbol}. Using symbol as is.")
    return symbol, symbol  # Fallback

def sync_portfolio(bullaware_weights):
    """
    Synchronize the local configuration with the weights fetched from BullAware.
    - Adds new tickers found in BullAware
    - Removes tickers no longer in BullAware
    """
    if not bullaware_weights:
        return {}
        
    current_config = load_config()
    current_tickers = current_config.get('tickers', {})
    current_emojis = current_config.get('emojis', {})
    
    bullaware_keys = set(bullaware_weights.keys())
    config_keys = set(current_tickers.keys())
    
    # 1. REMOVE: Tickers in local config but NOT in BullAware
    to_remove = config_keys - bullaware_keys
    if to_remove:
        print(f"♻️  Removing {len(to_remove)} assets no longer in portfolio: {', '.join(to_remove)}")
        for k in to_remove:
            current_tickers.pop(k, None)
            current_emojis.pop(k, None) # Optional cleanup
            
    # 2. ADD: Tickers in BullAware but NOT in local config
    to_add = bullaware_keys - config_keys
    if to_add:
        print(f"🆕 Discovered {len(to_add)} new assets. Attempting to auto-configure...")
        for k in to_add:
            yahoo_ticker, name = lookup_ticker_info(k)
            current_tickers[k] = [yahoo_ticker, name] # Use list for JSON compatibility
            # Try to assign a default emoji
            current_emojis[k] = "🆕" 
            
    # Save if changes were made
    if to_remove or to_add:
        current_config['tickers'] = current_tickers
        current_config['emojis'] = current_emojis
        save_config(current_config)
    else:
        print("✅ Portfolio config is already in sync.")

    return current_tickers
