
import json
import os
try:
    import yfinance as yf
except ImportError:
    yf = None

# DEFAULT DATA MOVED HERE TO AVOID CIRCULAR IMPORT WITH CONFIG.PY
# REAL ACTIVE ASSETS IN ANDREA RAVALLI'S ETORO PORTFOLIO
DEFAULT_TICKERS = {
    # Nuclear & Energy
    'CCJ': ('CCJ', 'Cameco Corp.'),
    'URNM': ('URNM', 'Sprott Uranium Miners ETF'),
    'ENI.MI': ('ENI.MI', 'Eni S.p.A.'),
    'ENEL.MI': ('ENEL.MI', 'Enel S.p.A.'),
    'MAU.PA': ('MAU.PA', 'Etablissements Maurel & Prom SA'),
    
    # Financial & Banking
    'SX7PEX.DE': ('EXV1.DE', 'iShares STOXX Europe 600 Banks UCITS ETF'),
    '0005.HK': ('0005.HK', 'HSBC Holdings PLC'),
    'DB1.DE': ('DB1.DE', 'Deutsche Börse AG'),
    
    # Healthcare & Pharma
    'NOVO-B.CO': ('NOVO-B.CO', 'Novo Nordisk A/S'),
    'LLY': ('LLY', 'Eli Lilly and Co'),
    'AZN.L': ('AZN.L', 'AstraZeneca PLC'),
    'ABBV': ('ABBV', 'AbbVie Inc'),
    'ABT': ('ABT', 'Abbott Laboratories'),
    'HUM': ('HUM', 'Humana Inc'),
    
    # Tech, AI & Semiconductors
    'PLTR': ('PLTR', 'Palantir Technologies Inc'),
    'NVDA': ('NVDA', 'NVIDIA Corporation'),
    'ASML.AS': ('ASML.AS', 'ASML Holding NV'),
    'TSM': ('TSM', 'Taiwan Semiconductor Manufacturing Co'),
    'MSFT': ('MSFT', 'Microsoft Corporation'),
    'AMZN': ('AMZN', 'Amazon.com Inc'),
    'GOOG': ('GOOGL', 'Alphabet Inc'),
    'AVGO': ('AVGO', 'Broadcom Inc'),
    'SAP.DE': ('SAP.DE', 'SAP SE'),
    
    # E-Commerce & Payments
    'MELI': ('MELI', 'MercadoLibre Inc'),
    'PYPL': ('PYPL', 'PayPal Holdings Inc'),
    
    # Automotive, Industrials & Luxury
    'PRY.MI': ('PRY.MI', 'Prysmian S.p.A.'),
    'BMW.DE': ('BMW.DE', 'Bayerische Motoren Werke AG'),
    'MBG.DE': ('MBG.DE', 'Mercedes-Benz Group AG'),
    'VOW3.DE': ('VOW3.DE', 'Volkswagen AG'),
    'RACE': ('RACE', 'Ferrari N.V.'),
    'AIR.PA': ('AIR.PA', 'Airbus SE'),
    'MC.PA': ('MC.PA', 'LVMH Moët Hennessy Louis Vuitton'),
    'OR.PA': ('OR.PA', "L'Oréal SA"),
    'RMS.PA': ('RMS.PA', 'Hermès International SA'),
    '1211.HK': ('1211.HK', 'BYD Co Ltd'),
    '1919.HK': ('1919.HK', 'COSCO SHIPPING Holdings Co Ltd'),
    'GLEN.L': ('GLEN.L', 'Glencore PLC'),
    
    # Emerging Markets & Specialized ETFs
    'INDO.PA': ('INDO.PA', 'Amundi MSCI Indonesia UCITS ETF Acc'),
    'WDEF.L': ('WDEF.L', 'WisdomTree Europe Equity Income UCITS ETF'),
    
    # Crypto
    'TRX': ('TRX-USD', 'TRON'),
    
    # Cash & Liquidity Management
    'IB01.L': ('IB01.L', 'iShares $ Treasury Bond 0-1yr UCITS ETF'),
    'XEON.DE': ('XEON.DE', 'Xtrackers II EUR Overnight Rate Swap UCITS ETF'),
}

DEFAULT_EMOJIS = {
    # ETFs
    'SX7PEX.DE': '🏛️', # Banking
    'VWCE.L': '🌐',
    'IEUR': '�🇺',     # Europe
    'IQQL.DE': '🔥',
    'IEMG': '🌍',
    'WDEF.L': '💼',
    'INDO.PA': '🇮🇩',
    'MNODL.L': '📦',
    'NVTKL.L': '🔥',
    
    # Healthcare & Pharmaceuticals
    'AZN.L': '🧬',
    'ABT': '🏥',
    'ABT.US': '🏥',
    'ABBV': '💉',
    'LLY': '💊',
    'NOVO-B.CO': '💉',
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
    'ENI.MI': '⛽',
    'ENI': '⛽',
    
    # Crypto
    'TRX': '🪙',
    'ETOR': '🏛️',
    
    # Financial Services & Others
    'DB1.DE': '📊',
    'TRIG.L': '🌬️',    # Renewables (Wind/Solar)
    'MAU.PA': '🛢️',
    'PRY.MI': '🔌',
    'RACE': '🏎️',
    'VOW3.DE': '🚗',
    'MELI': '🛒',
    'PYPL': '💳',
    'GLEN.L': '⛏️',
    'XEON.DE': '💤',    # EUR overnight rate (cash/liquidity)
    'IB01.L': '💵',    # US Treasury short-term bonds
    '1919.HK': '🚢',
    '2318.HK': '🏦',
    '1211.HK': '🔋',   # BYD
    'PPFB.DE': '🥇',   # Physical Gold/Metals
    'ULVR.L': '🧼',    # Unilever
    'VOF.L': '🇻🇳',     # Vietnam Opportunity Fund
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
            config = {
                "tickers": gist_tickers,
                "emojis": gist_emojis
            }
            # Auto-migration for bad tickers
            needs_save = False
            if config["tickers"].get("MNODL.L", [""])[0] == "MNODL.L":
                config["tickers"]["MNODL.L"] = ["MNDI.L", "Mondi PLC"]
                needs_save = True
            if config["tickers"].get("NVTKL.L", [""])[0] == "NVTKL.L":
                config["tickers"]["NVTKL.L"] = ["NVTK.ME", "Novatek"]
                needs_save = True
            if "ABT.US" not in config["tickers"]:
                config["tickers"]["ABT.US"] = ["ABT", "Abbott Laboratories"]
                config["emojis"]["ABT.US"] = config["emojis"].get("ABT", "🏥")
                needs_save = True
            # Fix ABT.US yahoo ticker if it was stored as "ABT.US" instead of "ABT"
            if config["tickers"].get("ABT.US", [""])[0] == "ABT.US":
                config["tickers"]["ABT.US"] = ["ABT", "Abbott Laboratories"]
                needs_save = True
            # Fix 01211.HK (BYD HK): leading zero not valid on Yahoo Finance, correct symbol is 1211.HK
            if "01211.HK" in config["tickers"]:
                config["tickers"].pop("01211.HK")
                config["tickers"]["1211.HK"] = ["1211.HK", "BYD Company"]
                if "01211.HK" in config.get("emojis", {}):
                    config["emojis"]["1211.HK"] = config["emojis"].pop("01211.HK")
                else:
                    config.setdefault("emojis", {}).setdefault("1211.HK", "🔋")
                if "01211.HK" in config.get("added_dates", {}):
                    config["added_dates"]["1211.HK"] = config["added_dates"].pop("01211.HK")
                needs_save = True
            
            # Fix ENI emoji
            for eni_key in ["ENI", "ENI.MI"]:
                if eni_key in config["tickers"]:
                    if config["emojis"].get(eni_key) in ["🆕", None]:
                        config["emojis"][eni_key] = "⛽"
                        needs_save = True

            # Fix NOVO-B → NOVO-B.CO emoji key
            if "NOVO-B" in config["emojis"] and "NOVO-B.CO" not in config["emojis"]:
                config["emojis"]["NOVO-B.CO"] = config["emojis"].pop("NOVO-B")
                needs_save = True

            # Fix NOVO-B.CO YF ticker: use native Copenhagen listing instead of US ADR
            if config["tickers"].get("NOVO-B.CO", [""])[0] == "NVO":
                config["tickers"]["NOVO-B.CO"] = ["NOVO-B.CO", "Novo Nordisk"]
                needs_save = True

            # Add new positions: XEON.DE and IB01.L
            if "XEON.DE" not in config["tickers"]:
                config["tickers"]["XEON.DE"] = ["XEON.DE", "Xtrackers II EUR Overnight Rate Swap UCITS ETF"]
                config["emojis"]["XEON.DE"] = "💤"
                needs_save = True
            if "IB01.L" not in config["tickers"]:
                config["tickers"]["IB01.L"] = ["IB01.L", "iShares Treasury Bond 0-1yr UCITS ETF"]
                config["emojis"]["IB01.L"] = "💵"
                needs_save = True

            if needs_save:
                print("🔄 Applying auto-migration to fix ticker mappings in Gist...")
                save_config(config)

            # Always check for expired '\ud83c\udd95' badges — independent of BullAware sync
            if expire_new_emojis(config):
                save_config(config)

            return config
    except Exception as e:
        print(f"⚠️ Failed to load config from Gist: {e}")

    # 2. Try Local File
    if os.path.exists(CONFIG_FILE):
        print("ℹ️ Verify local config fallback...")
        try:
            with open(CONFIG_FILE, 'r') as f:
                local_data = json.load(f)
                if expire_new_emojis(local_data):
                    save_config(local_data)
                # If we are here, it means Gist was empty or failed. 
                # We should try to push this local data to Gist to initialize it.
                print("📤 Initializing Gist config from local file...")
                save_gist_config(local_data.get('tickers', {}), local_data.get('emojis', {}))
                return local_data
        except Exception as e:
            print(f"Error loading config file: {e}")

    # 3. Defaults
    cfg = migrate_from_defaults()
    if expire_new_emojis(cfg):
        save_config(cfg)
    return cfg

def get_added_dates():
    """Get the dictionary of when tickers were added."""
    return load_config().get('added_dates', {})


def expire_new_emojis(config: dict) -> bool:
    """
    Check every ticker whose emoji is still '🆕' (\U0001F195) (NEW) and
    replace it with a permanent emoji once it has been in the portfolio
    for more than 7 days.

    This function is safe to call at any time — it modifies `config` in-place
    and returns True if any emoji was updated (so the caller knows to persist).

    The replacement priority:
      1. DEFAULT_EMOJIS (hardcoded per ticker)
      2. '📊' generic chart fallback
    """
    from datetime import date as _date, datetime as _datetime

    added_dates = config.get('added_dates', {})
    emojis      = config.get('emojis', {})
    changed     = False

    today = _date.today()
    for ticker, emoji in list(emojis.items()):
        if emoji not in ['\U0001F195', '🆕']:
            continue   # nothing to do for non-new tickers

        added_str = added_dates.get(ticker)
        if not added_str:
            # Ticker marked as new but no date recorded — treat as old
            days = 999
        else:
            try:
                days = (today - _datetime.fromisoformat(added_str).date()).days
            except Exception:
                days = 0  # can't parse — leave as-is

        if days > 7:
            replacement = DEFAULT_EMOJIS.get(ticker, '📊')
            print(f"🕒 {ticker}: 🆕 expired ({days}d) → {replacement}")
            emojis[ticker] = replacement
            changed = True

    return changed

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

    # For HK tickers with 5-digit codes (BullAware pads some with leading zero),
    # also try the 4-digit canonical Yahoo Finance form (e.g., 01211.HK -> 1211.HK)
    if symbol.endswith('.HK'):
        numeric_part = symbol[:-3]
        if len(numeric_part) == 5 and numeric_part[0] == '0':
            candidates.insert(1, numeric_part[1:] + '.HK')
    
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
            
    # 3. MAINTENANCE: expire '🆕' badges older than 7 days
    if expire_new_emojis(current_config):
        # expire_new_emojis already printed per-ticker messages
        pass

    # Save if changes were made or maintenance happened
    # We always save to ensure added_dates are persisted locally and in Gist (if we update Gist schema support)
    current_config['tickers'] = current_tickers
    current_config['emojis'] = current_emojis
    # Note: added_dates is currently stored in local JSON structure. 
    # Gist storage might filter it out if not updated to support it, 
    # but currently saving the whole dict to local file preserves it.
    save_config(current_config)

    return current_tickers


# ── Dual / Multi-Exchange Ticker Tags & Related Competitors Mapping ───────────

MULTI_TAG_MAP = {
    'ENI.MI': ['$ENI.MI', '$E'],
    'ENI': ['$ENI.MI', '$E'],
    'NOVO-B.CO': ['$NOVO-B.CO', '$NVO'],
    'AZN.L': ['$AZN.L', '$AZN'],
    '1211.HK': ['$1211.HK', '$BYDDY'],
    '1919.HK': ['$1919.HK', '$CICOY'],
    '2318.HK': ['$2318.HK', '$PNGAY'],
    'RACE': ['$RACE', '$RACE.MI'],
    'ULVR.L': ['$ULVR.L', '$UL'],
    'VOW3.DE': ['$VOW3.DE', '$VWAGY'],
    'ABT.US': ['$ABT.US', '$ABT'],
    'ABT': ['$ABT.US', '$ABT'],
    'PRY.MI': ['$PRY.MI', '$PRY'],
    'ENEL.MI': ['$ENEL.MI', '$ENLAY'],
}

RELATED_TICKERS_MAP = {
    'NVDA': ['$AMD', '$AVGO', '$TSM'],
    'MSFT': ['$GOOG', '$AMZN', '$AAPL'],
    'AMZN': ['$MELI', '$WMT', '$MSFT'],
    'GOOG': ['$MSFT', '$AMZN', '$META'],
    'LLY': ['$NOVO-B.CO', '$NVO', '$PFE'],
    'NOVO-B.CO': ['$LLY', '$NVO', '$PFE'],
    'PLTR': ['$SNOW', '$AI', '$MSFT'],
    'AVGO': ['$NVDA', '$QCOM', '$TXN'],
    'TSM': ['$NVDA', '$AVGO', '$INTC'],
    'ABBV': ['$LLY', '$AZN.L', '$JNJ'],
    'ABT.US': ['$MDT', '$BSX', '$SYK'],
    'HUM': ['$UNH', '$CVS', '$CI'],
    'CCJ': ['$URA', '$LEU', '$NXE'],
    'ENEL.MI': ['$IBE.MC', '$EDP.LS', '$RWE.DE'],
    'ENI.MI': ['$SHEL', '$TTE', '$BP'],
    'ETOR': ['$HOOD', '$COIN', '$IBKR'],
    'GLEN.L': ['$RIO.L', '$BHP.L', '$AAL.L'],
    'MAU.PA': ['$TTE', '$ENI.MI', '$SHEL'],
    'PRY.MI': ['$NEX.PA', '$NKT.CO', '$ENEL.MI'],
    'RACE': ['$VOW3.DE', '$MBG.DE', '$P911.DE'],
    'VOW3.DE': ['$RACE', '$MBG.DE', '$BMW.DE'],
    'MELI': ['$AMZN', '$BABA', '$SE'],
    '1211.HK': ['$TSLA', '$9866.HK', '$9868.HK'],
    '1919.HK': ['$1138.HK', '$ZIM', '$MATX'],
    '2318.HK': ['$2628.HK', '$3968.HK', '$939.HK'],
    'SX7PEX.DE': ['$BAC', '$JPM', '$HSBA.L'],
    'IEUR': ['$VGK', '$EZU', '$FEZ'],
    'IQQL.DE': ['$QUAL', '$IWDA.L', '$VWCE.L'],
    'IEMG': ['$EEM', '$VWO', '$IEMG'],
    'WDEF.L': ['$IDVY.L', '$VHYL.L', '$WDEF.L'],
    'INDO.PA': ['$EIDO', '$INDO.PA', '$IEMG'],
    'PPFB.DE': ['$GLD', '$IAU', '$SLV'],
    'XEON.DE': ['$CSH2.PA', '$XEON.DE', '$IB01.L'],
    'IB01.L': ['$SHY', '$BIL', '$XEON.DE'],
    'TRIG.L': ['$UKW.L', '$FSFL.L', '$TRIG.L'],
    'VOF.L': ['$VNM', '$VEIL.L', '$VOF.L'],
    'TRX': ['$BTC', '$ETH', '$SOL'],
    'NET': ['$CRWD', '$PANW', '$DDOG'],
    'PYPL': ['$SQ', '$V', '$MA'],
    'AZN.L': ['$LLY', '$NOVO-B.CO', '$PFE'],
    'MNODL.L': ['$PKG', '$IP', '$DSMI.L'],
    'NVTKL.L': ['$GAZP.ME', '$ROSN.ME', '$LKOH.ME'],
}


def get_ticker_all_tags(ticker: str) -> list[str]:
    """
    Return all ticker tags associated with a stock across different exchanges (e.g. ENI.MI -> ['$ENI.MI', '$E']).
    """
    clean = ticker.upper()
    if clean in MULTI_TAG_MAP:
        return MULTI_TAG_MAP[clean]
    # Default fallback
    base_tag = f"${clean}"
    return [base_tag]


def get_related_tickers(ticker: str) -> list[str]:
    """
    Return 2-3 related/competitor ticker tags for a given ticker.
    """
    clean = ticker.upper()
    if clean in RELATED_TICKERS_MAP:
        return RELATED_TICKERS_MAP[clean]
    return ["$S&P500", "$NSDQ100"]

