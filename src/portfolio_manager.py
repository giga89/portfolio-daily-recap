
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
    'IEMG': ('IEMG', 'iShares Core MSCI Emerging Markets ETF'),
    'WDEF.L': ('WDEF.L', 'WisdomTree Europe Equity Income UCITS ETF'),
    'INDO.PA': ('INDO.PA', 'Amundi MSCI Indonesia UCITS ETF Acc'),
    'MNODL.L': ('MNODL.L', 'Mondi PLC'),
    'NVTKL.L': ('NVTKL.L', 'Novatek'),
    
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
    'IEMG': '🌍',
    'WDEF.L': '💼',
    'INDO.PA': '🇮🇩',
    'MNODL.L': '📦',
    'NVTKL.L': '🔥',
    
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

from gist_storage import get_portfolio_config, save_portfolio_config as save_gist_config

def load_config():
    """
    Load portfolio configuration, prioritizing Gist storage.
    Migration path:
    1. Try Gist: If valid config found, use it.
    2. Try Local File: If Gist empty/fail, load local JSON.
    3. Fallback: Use Defaults.
    
    If loaded from local/defaults but Gist was empty, we SAVE to Gist to sync it.
    """
    # 1. Try Gist
    try:
        gist_tickers, gist_emojis = get_portfolio_config()
        if gist_tickers:
            print("✅ Loaded portfolio config from Gist")
            return {
                "tickers": gist_tickers,
                "emojis": gist_emojis
            }
    except Exception as e:
        print(f"⚠️ Failed to load config from Gist: {e}")

    # 2. Try Local File
    if os.path.exists(CONFIG_FILE):
        print("ℹ️ Verify local config fallback...")
        try:
            with open(CONFIG_FILE, 'r') as f:
                local_data = json.load(f)
                # If we are here, it means Gist was empty or failed. 
                # We should try to push this local data to Gist to initialize it.
                print("📤 Initializing Gist config from local file...")
                save_gist_config(local_data.get('tickers', {}), local_data.get('emojis', {}))
                return local_data
        except Exception as e:
            print(f"Error loading config file: {e}")

    # 3. Defaults
    return migrate_from_defaults()

def get_added_dates():
    """Get the dictionary of when tickers were added."""
    return load_config().get('added_dates', {})

def migrate_from_defaults():
    """Create JSON config from the defaults."""
    print("⚠️ Using hardcoded defaults")
    config_data = {
        "tickers": DEFAULT_TICKERS,
        "emojis": DEFAULT_EMOJIS
    }
    # Try to save to both Gist and Local
    save_config(config_data) 
    return config_data

def save_config(data):
    """Save configuration to BOTH Gist and local JSON."""
    # 1. Local Save
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)
        print(f"✅ Portfolio configuration saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"❌ Error saving local config: {e}")

    # 2. Gist Save
    try:
        save_gist_config(data.get('tickers', {}), data.get('emojis', {}))
        print("✅ Portfolio configuration sync to Gist")
    except Exception as e:
        print(f"❌ Error syncing config to Gist: {e}")

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
        from datetime import date
        today_iso = date.today().isoformat()
        
        # Initialize added_dates if not present
        if 'added_dates' not in current_config:
            current_config['added_dates'] = {}
            
        for k in to_add:
            yahoo_ticker, name = lookup_ticker_info(k)
            current_tickers[k] = [yahoo_ticker, name] # Use list for JSON compatibility
            # Try to assign a default emoji
            current_emojis[k] = "🆕" 
            current_config['added_dates'][k] = today_iso
            
    # 3. MAINTENANCE: Check for expired "New" icons (older than 7 days)
    # This runs every sync to keep icons clean
    if 'added_dates' in current_config:
        from datetime import date, datetime
        today_date = date.today()
        
        for k, added_str in current_config['added_dates'].items():
            if k in current_emojis and current_emojis[k] == "🆕":
                try:
                    added_date = datetime.fromisoformat(added_str).date()
                    delta = (today_date - added_date).days
                    if delta > 7:
                        print(f"🕒 Asset {k} is no longer new ({delta} days). Resetting emoji.")
                        # Reset to a default logic or generic chart
                        # We can try to match against DEFAULT_EMOJIS if available, or just use generic
                        if k in DEFAULT_EMOJIS:
                            current_emojis[k] = DEFAULT_EMOJIS[k]
                        else:
                            current_emojis[k] = "📊"
                except Exception as e:
                    print(f"Error checking date for {k}: {e}")

    # Save if changes were made or maintenance happened
    # We always save to ensure added_dates are persisted locally and in Gist (if we update Gist schema support)
    current_config['tickers'] = current_tickers
    current_config['emojis'] = current_emojis
    # Note: added_dates is currently stored in local JSON structure. 
    # Gist storage might filter it out if not updated to support it, 
    # but currently saving the whole dict to local file preserves it.
    save_config(current_config)

    return current_tickers
