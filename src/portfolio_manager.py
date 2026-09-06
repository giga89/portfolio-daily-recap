
import json
import os
try:
    import yfinance as yf
except ImportError:
    yf = None

# DEFAULT DATA MOVED HERE TO AVOID CIRCULAR IMPORT WITH CONFIG.PY
# REAL ACTIVE ASSETS IN ANDREA RAVALLI'S ETORO PORTFOLIO
DEFAULT_TICKERS = {
    # Cash, Fixed Income & Macro ETFs
    'IB01.L': ('IB01.L', 'iShares $ Treasury Bond 0-1yr UCITS ETF'),
    'INDO.PA': ('INDO.PA', 'Amundi MSCI Indonesia UCITS ETF Acc'),
    'PPFB.DE': ('PPFB.DE', 'iShares Physical Gold ETC'),
    'SX7PEX.DE': ('EXV1.DE', 'iShares STOXX Europe 600 Banks UCITS ETF'),
    'TRIG.L': ('TRIG.L', 'The Renewables Infrastructure Group Ltd'),
    'WDEF.L': ('WDEF.L', 'WisdomTree Europe Defence UCITS ETF'),
    'IEUR': ('IEUR', 'iShares Core MSCI Europe ETF'),
    'IQQL.DE': ('IQQL.DE', 'iShares Listed Private Equity UCITS ETF'),
    'VOF.L': ('VOF.L', 'VinaCapital Vietnam Opportunity Fund'),
    
    # Healthcare & Pharma
    'ABT.US': ('ABT', 'Abbott Laboratories'),
    'HUM': ('HUM', 'Humana Inc'),
    'NOVO-B.CO': ('NOVO-B.CO', 'Novo Nordisk A/S'),
    'ABBV': ('ABBV', 'AbbVie Inc'),
    'AZN.L': ('AZN.L', 'AstraZeneca PLC'),
    'LLY': ('LLY', 'Eli Lilly and Co'),
    
    # Tech, AI & Semiconductors
    'AMZN': ('AMZN', 'Amazon.com Inc'),
    'MRVL': ('MRVL', 'Marvell Technology Inc'),
    'MSFT': ('MSFT', 'Microsoft Corporation'),
    'GOOG': ('GOOGL', 'Alphabet Inc'),
    'TSM': ('TSM', 'Taiwan Semiconductor Manufacturing Co'),
    'NVDA': ('NVDA', 'NVIDIA Corporation'),
    'AVGO': ('AVGO', 'Broadcom Inc'),
    'PLTR': ('PLTR', 'Palantir Technologies Inc'),
    
    # Energy, Nuclear, Utilities & Commodities
    'ENI.MI': ('ENI.MI', 'Eni S.p.A.'),
    'MAU.PA': ('MAU.PA', 'Etablissements Maurel & Prom SA'),
    'ENEL.MI': ('ENEL.MI', 'Enel S.p.A.'),
    'CCJ': ('CCJ', 'Cameco Corp.'),
    'GLEN.L': ('GLEN.L', 'Glencore PLC'),
    
    # Automotive, Luxury & Industrials
    'RACE': ('RACE', 'Ferrari N.V.'),
    'PRY.MI': ('PRY.MI', 'Prysmian S.p.A.'),
    '1919.HK': ('1919.HK', 'COSCO SHIPPING Holdings Co Ltd'),
    'VOW3.DE': ('VOW3.DE', 'Volkswagen AG'),
    '1211.HK': ('1211.HK', 'BYD Co Ltd'),
    'ULVR.L': ('ULVR.L', 'Unilever PLC'),
    
    # E-Commerce, Fintech, Pre-IPO, Retail & Crypto
    'MELI': ('MELI', 'MercadoLibre Inc'),
    'ETOR': ('ETOR', 'eToro Group Ltd'),
    '2318.HK': ('2318.HK', 'Ping An Insurance Group'),
    'WMT': ('WMT', 'Walmart Inc.'),
    'TRX': ('TRX-USD', 'TRON'),
    'SPCX.RTH': ('SPCX.RTH', 'Space Exploration Technologies Corp.'),
}

DEFAULT_EMOJIS = {
    # Cash, Fixed Income & Macro ETFs
    'IB01.L': '💵',    # US Treasury short-term bonds
    'INDO.PA': '🇮🇩',   # Indonesia
    'PPFB.DE': '🥇',   # Physical Gold
    'SX7PEX.DE': '🏛️', # Banking
    'TRIG.L': '🌬️',    # Renewables (Wind/Solar)
    'WDEF.L': '🛡️',    # European Defence
    'IEUR': '🇪🇺',     # Europe
    'IQQL.DE': '🔥',   # Listed Private Equity
    'VOF.L': '🇻🇳',     # Vietnam Opportunity Fund
    
    # Healthcare & Pharmaceuticals
    'AZN.L': '🧬',
    'ABT': '🏥',
    'ABT.US': '🏥',
    'ABBV': '💉',
    'LLY': '💊',
    'NOVO-B.CO': '💉',
    'HUM': '🏥',
    
    # Technology & Semiconductors
    'AVGO': '🔌',
    'NVDA': '🤖',
    'TSM': '🏭',
    'MSFT': '💻',
    'AMZN': '📦',
    'GOOG': '🔍',
    'PLTR': '🛡️',
    'NET': '☁️',
    'MRVL': '📊',
    
    # Energy, Utilities & Commodities
    'CCJ': '⚡',
    'ENEL.MI': '🔋',
    'ENI.MI': '⛽',
    'ENI': '⛽',
    'GLEN.L': '⛏️',
    'MAU.PA': '🛢️',
    'PRY.MI': '🔌',
    
    # Automotive, Luxury & Industrials
    'RACE': '🏎️',
    'VOW3.DE': '🚗',
    '1919.HK': '🚢',
    '1211.HK': '🔋',   # BYD
    'ULVR.L': '🧼',    # Unilever
    
    # E-Commerce, Fintech, Pre-IPO, Retail & Crypto
    'MELI': '🛒',
    'WMT': '🛒',
    'ETOR': '🏛️',
    '2318.HK': '🏦',
    'SPCX.RTH': '🚀',
    'TRX': '🪙',
    'DB1.DE': '📊',
    'PYPL': '💳',
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
            # Purge any Russian / untradeable assets
            for russian_t in ["MNODL.L", "NVTKL.L"]:
                if russian_t in config["tickers"]:
                    config["tickers"].pop(russian_t, None)
                    needs_save = True
                if russian_t in config.get("emojis", {}):
                    config["emojis"].pop(russian_t, None)
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

            # Add new positions: IB01.L
            if "IB01.L" not in config["tickers"]:
                config["tickers"]["IB01.L"] = ["IB01.L", "iShares Treasury Bond 0-1yr UCITS ETF"]
            # Ensure purged positions are removed: XEON.DE and legacy unheld assets
            for purged in ["XEON.DE", "VWCE.L", "IEMG", "ABT", "NET", "ENI", "DB1.DE", "PYPL"]:
                if purged in config.get("tickers", {}):
                    del config["tickers"][purged]
                    needs_save = True
                if purged in config.get("emojis", {}):
                    del config["emojis"][purged]
                    needs_save = True

            if "IB01.L" not in config.get("tickers", {}):
                config["tickers"]["IB01.L"] = ["IB01.L", "iShares $ Treasury Bond 0-1yr UCITS ETF"]
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
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
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
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, sort_keys=True, ensure_ascii=False)
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
    # Guard: If symbol is purely numeric without an exchange suffix (e.g. "1035"),
    # it's an unresolved eToro instrument ID, NOT a valid ticker! Never resolve to random HK tickers.
    if str(symbol).isdigit():
        print(f"⚠️ Rejecting pure numeric symbol '{symbol}' — looks like an unresolved eToro instrument ID, not a ticker.")
        return symbol, symbol

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
    '1211.HK': ['$1211.HK'],
    '1919.HK': ['$1919.HK'],
    '2318.HK': ['$2318.HK'],
    'RACE': ['$RACE'],
    'ULVR.L': ['$ULVR.L', '$UL'],
    'VOW3.DE': ['$VOW3.DE'],
    'ABT.US': ['$ABT'],
    'ABT': ['$ABT'],
    'PRY.MI': ['$PRY.MI'],
    'ENEL.MI': ['$ENEL.MI'],
    'WMT': ['$WMT'],
    'MRVL': ['$MRVL'],
}

RELATED_TICKERS_MAP = {
    'NVDA': ['$AMD', '$AVGO', '$TSM'],
    'MSFT': ['$GOOG', '$AMZN', '$AAPL'],
    'AMZN': ['$MELI', '$WMT', '$MSFT'],
    'WMT': ['$AMZN', '$COST', '$TGT'],
    'GOOG': ['$MSFT', '$AMZN', '$META'],
    'LLY': ['$NOVO-B.CO', '$NVO', '$PFE'],
    'NOVO-B.CO': ['$LLY', '$NVO', '$PFE'],
    'PLTR': ['$SNOW', '$AI', '$MSFT'],
    'AVGO': ['$NVDA', '$QCOM', '$TXN'],
    'TSM': ['$NVDA', '$AVGO', '$INTC'],
    'MRVL': ['$NVDA', '$AVGO', '$AMD'],
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
    'ULVR.L': ['$PG', '$NESN.SW', '$KO'],
    'MELI': ['$AMZN', '$BABA', '$SE'],
    '1211.HK': ['$TSLA', '$NIO', '$XPEV'],
    '1919.HK': ['$ZIM', '$MATX', '$1138.HK'],
    '2318.HK': ['$2628.HK', '$3968.HK', '$939.HK'],
    'SX7PEX.DE': ['$BAC', '$JPM', '$HSBA.L'],
    'IEUR': ['$VGK', '$EZU', '$FEZ'],
    'IQQL.DE': ['$BX', '$KKR', '$PSP'],
    'IEMG': ['$EEM', '$VWO'],
    'WDEF.L': ['$RHM.DE', '$BA.L', '$LMT'],
    'INDO.PA': ['$EIDO', '$IEMG'],
    'PPFB.DE': ['$GLD', '$IAU', '$SLV'],
    'IB01.L': ['$SHY', '$BIL', '$TLT'],
    'TRIG.L': ['$UKW.L', '$FSFL.L', '$ENEL.MI'],
    'VOF.L': ['$VNM', '$VEIL.L'],
    'TRX': ['$BTC', '$ETH', '$SOL'],
    'AZN.L': ['$LLY', '$NOVO-B.CO', '$PFE'],
}

# ══════════════════════════════════════════════════════════════════════════════
# MASTER PORTFOLIO ASSETS METADATA CATALOG (SINGLE SOURCE OF TRUTH)
# ══════════════════════════════════════════════════════════════════════════════
PORTFOLIO_ASSETS_METADATA = {
    # ── US Tech & AI Megatrend ───────────────────────────────────────────────
    "NVDA": {
        "ticker": "NVDA", "yahoo_ticker": "NVDA", "name": "NVIDIA Corporation", "emoji": "🤖",
        "asset_class": "Stock", "sector": "AI & Semiconduttori", "geo": "USA", "tier": "Core Growth",
        "is_dividend_paying": False, "dividend_policy": "Dividendo simbolico trimestrale (~0.03%), focus prioritario su reinvestimento in R&D e crescita AI", "annual_yield_pct": 0.03, "frequency": "Trimestrale",
        "domain": "nvidia.com", "color": (118, 185, 0),
        "desc": "Undisputed global leader in accelerated computing GPUs and full-stack AI enterprise infrastructure.",
        "thesis": "Monopolio di fatto nell'accelerazione hardware per l'AI generativa, ecosistema software CUDA insostituibile e leadership tecnologica con architetture Blackwell e Vera Rubin.",
        "upside_catalysts": [
            "Domanda insaziabile di cluster GPU da parte di tutti i big cloud hyperscaler (Microsoft, Amazon, Google, Meta)",
            "Lancio a pieno regime e spedizioni record delle nuove piattaforme Blackwell",
            "Monetizzazione crescente del software enterprise NVIDIA AI Enterprise e networking InfiniBand/Spectrum-X"
        ],
        "downside_risks": [
            "Ciclicità della spesa in capex dei grandi clienti tecnologici",
            "Restrizioni geopolitiche ed export control sui chip avanzati verso la Cina",
            "Concorrenza emergente su chip custom ASIC per carichi di sola inferenza"
        ],
        "related_tickers": ["$AMD", "$AVGO", "$TSM"], "primary_tags": ["$NVDA"]
    },
    "MSFT": {
        "ticker": "MSFT", "yahoo_ticker": "MSFT", "name": "Microsoft Corporation", "emoji": "💻",
        "asset_class": "Stock", "sector": "Software Enterprise & Cloud AI", "geo": "USA", "tier": "Core Holding",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione trimestrale costante e in crescita continua (~0.8% yield)", "annual_yield_pct": 0.8, "frequency": "Trimestrale (Feb/Mag/Ago/Nov)",
        "domain": "microsoft.com", "color": (0, 164, 239),
        "desc": "Enterprise software titan, Azure hyperscale cloud, and exclusive foundational partnership with OpenAI.",
        "thesis": "Fortezza finanziaria AAA con leadership dominante nel cloud hyperscale (Azure), monopolio del software per la produttività aziendale (Office 365) e integrazione pervasiva di Copilot e OpenAI.",
        "upside_catalysts": [
            "Accelerazione della crescita dei ricavi Azure guidata da servizi e modelli AI di OpenAI",
            "Monetizzazione su larga scala degli abbonamenti Microsoft 365 Copilot su centinaia di milioni di postazioni aziendali",
            "Margini operativi eccezionali e continuo incremento di dividendi e buyback"
        ],
        "downside_risks": [
            "Elevata spesa in investimenti infrastrutturali (capex data center) che comprime temporaneamente il free cash flow",
            "Intensa concorrenza nel cloud da parte di AWS e Google Cloud",
            "Scrutinio antitrust globale sulle partnership e acquisizioni strategiche"
        ],
        "related_tickers": ["$GOOG", "$AMZN", "$AAPL"], "primary_tags": ["$MSFT"]
    },
    "AMZN": {
        "ticker": "AMZN", "yahoo_ticker": "AMZN", "name": "Amazon.com Inc", "emoji": "📦",
        "asset_class": "Stock", "sector": "E-Commerce Globale & Cloud AWS", "geo": "USA", "tier": "Core Holding",
        "is_dividend_paying": False, "dividend_policy": "Nessun dividendo distribuito; autofinanziamento completo e reinvestimento massiccio in logistica, AWS e AI", "annual_yield_pct": 0.0, "frequency": "Nessuna",
        "domain": "amazon.com", "color": (255, 153, 0),
        "desc": "Global e-commerce monopoly, cloud computing infrastructure leader (AWS), and high-margin digital advertising.",
        "thesis": "Ecosistema trifase ad altissima barriera all'entrata: cloud infrastructure n.1 al mondo (AWS), rete logistica e retail e-commerce ineguagliata, e business pubblicitario ad altissima marginalità.",
        "upside_catalysts": [
            "Riaccelelerazione della crescita di AWS supportata dai chip custom Trainium/Inferentia e bedrock AI",
            "Espansione costante dei margini operativi grazie all'automazione robotica della rete logistica",
            "Crescita a doppia cifra del segmento pubblicitario e monetizzazione di Prime Video"
        ],
        "downside_risks": [
            "Sensibilità dei consumatori all'inflazione e rallentamento della spesa retail discrezionale",
            "Concorrenza agguerrita di retailer cinesi low-cost (Temu, Shein)",
            "Pressione regolatoria FTC e antitrust sull'ecosistema marketplace"
        ],
        "related_tickers": ["$MELI", "$WMT", "$MSFT"], "primary_tags": ["$AMZN"]
    },
    "GOOG": {
        "ticker": "GOOG", "yahoo_ticker": "GOOGL", "name": "Alphabet Inc", "emoji": "🔍",
        "asset_class": "Stock", "sector": "Search, Cloud & Intelligenza Artificiale", "geo": "USA", "tier": "Core Holding",
        "is_dividend_paying": True, "dividend_policy": "Dividendo trimestrale introdotto di recente (~0.5% yield) unito a massicci programmi di riacquisto azioni proprie", "annual_yield_pct": 0.5, "frequency": "Trimestrale (Mar/Giu/Set/Dic)",
        "domain": "google.com", "color": (66, 133, 244),
        "desc": "Unrivaled global search monopoly, YouTube streaming ecosystem, Android OS, and Gemini multimodal AI.",
        "thesis": "Monopolio indiscusso nella ricerca web globale, leadership nello streaming video con YouTube, rapida espansione della redditività di Google Cloud e sviluppo proprietario dei modelli multimodali Gemini e chip TPU.",
        "upside_catalysts": [
            "Espansione dei margini e accelerazione dei contratti enterprise su Google Cloud",
            "Integrazione efficace dell'AI Overviews nei risultati di ricerca senza cannibalizzare i ricavi pubblicitari",
            "Crescita dei ricavi da abbonamenti (YouTube Premium, YouTube TV, Google One)"
        ],
        "downside_risks": [
            "Contenziosi antitrust negli USA e in Europa sulla posizione dominante nei motori di ricerca e nell'ad-tech",
            "Cambiamento nelle abitudini di ricerca degli utenti verso motori conversazionali AI",
            "Volatilità della spesa pubblicitaria globale legata al ciclo macroeconomico"
        ],
        "related_tickers": ["$MSFT", "$AMZN", "$META"], "primary_tags": ["$GOOG", "$GOOGL"]
    },
    "PLTR": {
        "ticker": "PLTR", "yahoo_ticker": "PLTR", "name": "Palantir Technologies Inc", "emoji": "🛡️",
        "asset_class": "Stock", "sector": "Enterprise AI & Difesa Governativo", "geo": "USA", "tier": "High Growth",
        "is_dividend_paying": False, "dividend_policy": "Nessun dividendo distribuito; reinvestimento totale del free cash flow in espansione commerciale e tecnologia", "annual_yield_pct": 0.0, "frequency": "Nessuna",
        "domain": "palantir.com", "color": (0, 220, 255),
        "desc": "Mission-critical AIP data intelligence platforms deployed across US defense, intelligence, and major global enterprises.",
        "thesis": "Posizione monopolistica nelle piattaforme software operative per la difesa e sicurezza nazionale USA (Gotham), combinata con l'esplosione dell'adozione commerciale della piattaforma AIP (Artificial Intelligence Platform).",
        "upside_catalysts": [
            "Adozione commerciale record di Palantir AIP attraverso i bootcamp intensivi con cicli di vendita rapidissimi",
            "Espansione dei budget militari USA e NATO per l'integrazione di sistemi decisionali autonomi e data fusion",
            "Margini operativi 'Rule of 40+' e continua crescita del free cash flow"
        ],
        "downside_risks": [
            "Multipli di valutazione storicamente elevati che espongono il titolo a volatilità in caso di trimestrali inferiori alle attese",
            "Cicli di approvazione dei contratti governativi federali complessi o soggetti a ritardi burocratici",
            "Rallentamento della spesa software aziendale in scenari macroeconomici incerti"
        ],
        "related_tickers": ["$SNOW", "$AI", "$MSFT"], "primary_tags": ["$PLTR"]
    },
    "AVGO": {
        "ticker": "AVGO", "yahoo_ticker": "AVGO", "name": "Broadcom Inc", "emoji": "🔌",
        "asset_class": "Stock", "sector": "Semiconduttori Custom & Networking AI", "geo": "USA", "tier": "Core Growth",
        "is_dividend_paying": True, "dividend_policy": "Dividend Aristocrat con payout target del 50% del Free Cash Flow dell'anno precedente (~1.4% yield)", "annual_yield_pct": 1.4, "frequency": "Trimestrale (Mar/Giu/Set/Dic)",
        "domain": "broadcom.com", "color": (204, 0, 0),
        "desc": "Custom ASIC AI accelerator chips, high-speed data center networking silicon, and VMware enterprise software.",
        "thesis": "Leader mondiale assoluto nel networking per data center AI (switch Tomahawk/Jericho, PCI Express) e nei processori AI custom (XPU/ASIC) per Google e Meta, con eccezionale flusso di cassa ricorrente derivante da VMware.",
        "upside_catalysts": [
            "Boom della domanda di switch Ethernet 800G e 1.6T per cluster di calcolo AI massivi",
            "Espansione del business dei chip custom AI co-progettati con i principali cloud provider",
            "Monetizzazione rapida delle licenze in abbonamento VMware Cloud Foundation"
        ],
        "downside_risks": [
            "Concentrazione dei ricavi su pochi grandi hyperscaler clienti",
            "Integrazione e costi di ristrutturazione post-acquisizione VMware",
            "Ciclicità dei segmenti semiconduttori tradizionali (wireless, broadband, storage)"
        ],
        "related_tickers": ["$NVDA", "$QCOM", "$TXN"], "primary_tags": ["$AVGO"]
    },
    "TSM": {
        "ticker": "TSM", "yahoo_ticker": "TSM", "name": "Taiwan Semiconductor Manufacturing Co", "emoji": "🏭",
        "asset_class": "Stock", "sector": "Fonderia di Semiconduttori Avanzati", "geo": "Asia", "tier": "Core Holding",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione trimestrale con dividend yield ~1.3% e payout sostenibile", "annual_yield_pct": 1.3, "frequency": "Trimestrale (Gen/Apr/Lug/Ott)",
        "domain": "tsmc.com", "color": (220, 50, 50),
        "desc": "The world's most advanced semiconductor foundry, sole manufacturing partner for Apple, NVIDIA, and AMD.",
        "thesis": "Monopolio globale nella produzione dei chip più avanzati al mondo (>90% della capacità a 3nm e 2nm), fornitore indispensabile ed esclusivo per Apple, NVIDIA, AMD e Qualcomm.",
        "upside_catalysts": [
            "Utilizzo al 100% della capacità produttiva sui nodi avanzati N3/N2 guidata dalla domanda AI",
            "Aumento del potere di prezzo (pricing power) e espansione dei margini lordi oltre il 53%",
            "Diversificazione geografica delle fab con impianti in Arizona, Giappone (Kumamoto) e Germania"
        ],
        "downside_risks": [
            "Rischio geopolitico legato alle tensioni nello Stretto di Taiwan",
            "Costi di capitale e capex elevatissimi per mantenere la leadership litografica EUV",
            "Eventuali colli di bottiglia nel packaging avanzato CoWoS"
        ],
        "related_tickers": ["$NVDA", "$AVGO", "$INTC"], "primary_tags": ["$TSM"]
    },
    "MRVL": {
        "ticker": "MRVL", "yahoo_ticker": "MRVL", "name": "Marvell Technology Inc", "emoji": "📊",
        "asset_class": "Stock", "sector": "Semiconduttori Custom & Ottica Data Center", "geo": "USA", "tier": "Growth",
        "is_dividend_paying": True, "dividend_policy": "Dividendo trimestrale costante (~0.3% yield)", "annual_yield_pct": 0.3, "frequency": "Trimestrale (Gen/Apr/Lug/Ott)",
        "domain": "marvell.com", "color": (0, 90, 180),
        "desc": "Custom AI processors for cloud hyperscalers and electro-optics interconnects enabling high-bandwidth clusters.",
        "thesis": "Attore cardine nelle interconnessioni elettro-ottiche ad altissima velocità (PAM4 DSP, Optical TIA) e nel silicio custom per accelerare la comunicazione tra rack di calcolo nei data center AI.",
        "upside_catalysts": [
            "Transizione dei data center alle interconnessioni ottiche 800G e 1.6T",
            "Incremento della produzione di chip custom ASIC per i maggiori operatori cloud",
            "Ripresa ciclica dei segmenti enterprise networking e infrastrutture carrier 5G"
        ],
        "downside_risks": [
            "Volatilità della domanda trimestrale da parte degli hyperscaler",
            "Concorrenza tecnologica di Broadcom e soluzioni proprietarie in-house",
            "Tempi di qualificazione e collaudo per nuove generazioni di DSP ottici"
        ],
        "related_tickers": ["$NVDA", "$AVGO", "$AMD"], "primary_tags": ["$MRVL"]
    },

    # ── Healthcare & GLP-1 Megatrend ──────────────────────────────────────────
    "LLY": {
        "ticker": "LLY", "yahoo_ticker": "LLY", "name": "Eli Lilly and Co", "emoji": "💊",
        "asset_class": "Stock", "sector": "Farmaceutica & Trattamenti GLP-1", "geo": "USA", "tier": "Core Growth",
        "is_dividend_paying": True, "dividend_policy": "Dividendo trimestrale in crescita ininterrotta da decenni (~0.6% yield)", "annual_yield_pct": 0.6, "frequency": "Trimestrale (Mar/Giu/Set/Dic)",
        "domain": "lilly.com", "color": (230, 40, 40),
        "desc": "Global pioneer in revolutionary GLP-1/GIP treatments (Mounjaro, Zepbound) for diabetes, obesity, and oncology.",
        "thesis": "Leader mondiale indiscusso nel megatrend secolare dei farmaci contro diabete, obesità e malattie cardiovascolari (Mounjaro, Zepbound, Tirzepatide) con pipeline blockbuster in espansione.",
        "upside_catalysts": [
            "Aumento massiccio della capacità produttiva globale per soddisfare una domanda senza precedenti",
            "Espansione delle indicazioni terapeutiche per apnea notturna, insufficienza cardiaca e MASH",
            "Sviluppo di trattamenti orali di nuova generazione (Orforglipron)"
        ],
        "downside_risks": [
            "Pressione sui rimborsi assicurativi e negoziati sui prezzi con i governi",
            "Vincoli di capacità produttiva a breve termine negli stabilimenti",
            "Concorrenza diretta con Novo Nordisk e nuovi entranti"
        ],
        "related_tickers": ["$NOVO-B.CO", "$NVO", "$PFE"], "primary_tags": ["$LLY"]
    },
    "NOVO-B.CO": {
        "ticker": "NOVO-B.CO", "yahoo_ticker": "NOVO-B.CO", "name": "Novo Nordisk A/S", "emoji": "💉",
        "asset_class": "Stock", "sector": "Farmaceutica & Cura del Diabete e Obesità", "geo": "Europe", "tier": "Core Growth",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione semestrale con solido dividend yield (~1.4%) e crescita a doppia cifra", "annual_yield_pct": 1.4, "frequency": "Semestrale (Marzo / Agosto)",
        "domain": "novonordisk.com", "color": (0, 110, 200),
        "desc": "Danish healthcare giant leading worldwide metabolic healthcare and obesity solutions (Ozempic, Wegovy).",
        "thesis": "Pioniere danese e colosso globale nella cura del diabete e dell'obesità (Ozempic, Wegovy, Semaglutide), dotato di un fossato competitivo straordinario e leadership scientifica centenaria.",
        "upside_catalysts": [
            "Approvazioni internazionali estese per la riduzione degli eventi cardiovascolari",
            "Integrazione dei siti produttivi acquisiti da Catalent per triplicare l'output di penne iniettabili",
            "Avanzamento clinico promettente della molecola CagriSema per la perdita di peso superiore"
        ],
        "downside_risks": [
            "Pressioni politiche e audizioni parlamentari USA sui prezzi di listino",
            "Fenomeno del compounding e delle preparazioni galeniche non autorizzate",
            "Fluttuazioni valutarie corona danese ed euro rispetto al dollaro"
        ],
        "related_tickers": ["$LLY", "$NVO", "$PFE"], "primary_tags": ["$NOVO-B.CO", "$NVO"]
    },
    "ABBV": {
        "ticker": "ABBV", "yahoo_ticker": "ABBV", "name": "AbbVie Inc", "emoji": "💉",
        "asset_class": "Stock", "sector": "Biopharma & Immunologia", "geo": "USA", "tier": "Dividend Aristocrat",
        "is_dividend_paying": True, "dividend_policy": "Dividend King con oltre 50 anni di aumenti annuali consecutivi (~3.7% yield)", "annual_yield_pct": 3.7, "frequency": "Trimestrale (Feb/Mag/Ago/Nov)",
        "domain": "abbvie.com", "color": (0, 100, 200),
        "desc": "High-yield dividend champion with next-gen blockbuster immunology drugs (Skyrizi, Rinvoq) and robust oncology pipeline.",
        "thesis": "Transizione post-Humira completata con straordinario successo grazie ai nuovi blockbuster immunologici Skyrizi e Rinvoq, combinati con la divisione estetica (Botox) e una cedola ultra-affidabile da Dividend King.",
        "upside_catalysts": [
            "Skyrizi e Rinvoq che superano insieme i picchi storici di vendite generati da Humira",
            "Espansione della pipeline oncologica e neuroscientifica (acquisizioni ImmunoGen e Cerevel)",
            "Crescita ininterrotta del dividendo e forte generazione di cassa operativa"
        ],
        "downside_risks": [
            "Erosione della quota di mercato di Humira a favore dei biosimilari",
            "Complessità nell'integrazione di pipeline biotecnologiche acquisite",
            "Scadenze brevettuali future su trattamenti oncologici storici (Imbruvica)"
        ],
        "related_tickers": ["$LLY", "$AZN.L", "$JNJ"], "primary_tags": ["$ABBV"]
    },
    "ABT.US": {
        "ticker": "ABT.US", "yahoo_ticker": "ABT", "name": "Abbott Laboratories", "emoji": "🏥",
        "asset_class": "Stock", "sector": "Dispositivi Medici & Diagnostica", "geo": "USA", "tier": "Core Defensive",
        "is_dividend_paying": True, "dividend_policy": "Dividend King con oltre 52 anni consecutivi di crescita del dividendo (~2.1% yield)", "annual_yield_pct": 2.1, "frequency": "Trimestrale (Feb/Mag/Ago/Nov)",
        "domain": "abbott.com", "color": (0, 150, 220),
        "desc": "Essential medical technologies leader (FreeStyle Libre continuous glucose monitoring) and adult clinical nutrition.",
        "thesis": "Modello di business ultra-diversificato e difensivo (dispositivi cardiovascolari, diagnostica, nutrizione clinica e farmaci generici) trainato dal sensore continuo per il monitoraggio del glucosio FreeStyle Libre.",
        "upside_catalysts": [
            "Adozione globale inarrestabile di FreeStyle Libre sia tra diabetici che per il benessere metabolico",
            "Crescita a doppia cifra dei dispositivi cardiovascolari strutturali d'avanguardia (TriClip, MitraClip)",
            "Bilancio forte e incremento costante della remunerazione degli azionisti"
        ],
        "downside_risks": [
            "Contenziosi legali su formule nutrizionali neonatali specialistiche",
            "Normalizzazione definitiva dei volumi di test diagnostici post-pandemici",
            "Riforme tariffarie sui rimborsi dei dispositivi medici nei mercati internazionali"
        ],
        "related_tickers": ["$MDT", "$BSX", "$SYK"], "primary_tags": ["$ABT.US", "$ABT"]
    },
    "HUM": {
        "ticker": "HUM", "yahoo_ticker": "HUM", "name": "Humana Inc", "emoji": "🏥",
        "asset_class": "Stock", "sector": "Assicurazione Sanitaria Senior & Medicare", "geo": "USA", "tier": "Value / Healthcare",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione trimestrale con dividend yield moderato (~0.9%) e focus sul recupero dei margini", "annual_yield_pct": 0.9, "frequency": "Trimestrale (Gen/Apr/Lug/Ott)",
        "domain": "humana.com", "color": (120, 190, 32),
        "desc": "Leading US healthcare provider specialized in Medicare Advantage programs for the aging baby-boomer demographic.",
        "thesis": "Posizione di vertice nei piani assicurativi Medicare Advantage dedicati alla popolazione senior USA, beneficiando dell'invecchiamento demografico (oltre 10.000 pensionati/giorno) e della rete integrata di cliniche CenterWell.",
        "upside_catalysts": [
            "Ribilanciamento delle tariffe dei premi e miglioramento del Medical Loss Ratio (MLR)",
            "Recupero delle valutazioni Star Rating da parte dell'ente federale CMS",
            "Espansione delle cliniche primarie CenterWell a margine superiore"
        ],
        "downside_risks": [
            "Aumento della frequenza dei ricoveri e delle procedure chirurgiche tra i pazienti anziani",
            "Modifiche normative o tagli nei tassi di rimborso federali Medicare",
            "Pressioni inflazionistiche sui costi delle prestazioni sanitarie"
        ],
        "related_tickers": ["$UNH", "$CVS", "$CI"], "primary_tags": ["$HUM"]
    },
    "AZN.L": {
        "ticker": "AZN.L", "yahoo_ticker": "AZN.L", "name": "AstraZeneca PLC", "emoji": "🧬",
        "asset_class": "Stock", "sector": "Oncologia & Biotecnologie", "geo": "Europe", "tier": "Core Growth",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione semestrale con solido dividend yield (~2.8%)", "annual_yield_pct": 2.8, "frequency": "Semestrale (Febbraio / Agosto)",
        "domain": "astrazeneca.com", "color": (150, 0, 150),
        "desc": "Anglo-Swedish global pharma powerhouse with industry-leading targeted oncology and cardiovascular therapies.",
        "thesis": "Seconda major farmaceutica europea per capitalizzazione, dotata di una delle pipeline oncologiche più trasformative al mondo (Tagrisso, Imfinzi, Enhertu), leadership nelle malattie rare (Alexion) e piano per $80B di ricavi al 2030.",
        "upside_catalysts": [
            "Lancio programmato di 20 nuovi farmaci entro il 2030 in oncologia e cardiometabolismo",
            "Leadership assoluta per fatturato tra le case farmaceutiche occidentali in Cina e mercati emergenti",
            "Brevetti blindati e assenza di concorrenza generica sulle terapie per malattie rare"
        ],
        "downside_risks": [
            "Rischi intrinseci di insuccesso clinico negli studi registrativi di Fase 3",
            "Pressioni negoziali sui prezzi dei medicinali negli USA (Inflation Reduction Act)",
            "Incertezza regolatoria e investigativa sul mercato farmaceutico cinese"
        ],
        "related_tickers": ["$LLY", "$NOVO-B.CO", "$PFE"], "primary_tags": ["$AZN.L", "$AZN"]
    },

    # ── Energy, Utilities, Commodities & Nuclear ──────────────────────────────
    "CCJ": {
        "ticker": "CCJ", "yahoo_ticker": "CCJ", "name": "Cameco Corp.", "emoji": "⚡",
        "asset_class": "Stock", "sector": "Uranio & Energia Nucleare Pulita", "geo": "USA / Canada", "tier": "Nuclear Megatrend",
        "is_dividend_paying": True, "dividend_policy": "Dividendo annuale simbolico (~0.2% yield); focus su contratti di fornitura pluriennali e rinascimento nucleare", "annual_yield_pct": 0.2, "frequency": "Annuale",
        "domain": "cameco.com", "color": (255, 180, 0),
        "desc": "The Western world's largest uranium miner, strategically powering zero-carbon nuclear renaissance and AI data centers.",
        "thesis": "Maggior produttore di uranio del mondo occidentale (miniere Tier-1 a bassissimo costo in Canada) e proprietario di Westinghouse: pilastro insostituibile per alimentare con energia nucleare 'baseload 24/7' i data center AI e la transizione net-zero.",
        "upside_catalysts": [
            "Deficit strutturale di offerta globale di uranio e rialzo dei prezzi spot e contratti a lungo termine",
            "Accordi diretti tra operatori nucleari e i colossi tech (Microsoft, Amazon, Google) per alimentare i cluster AI",
            "Flussi di cassa in forte espansione dalla divisione servizi e ingegneria nucleare Westinghouse"
        ],
        "downside_risks": [
            "Volatilità dei prezzi spot delle materie prime energetiche",
            "Rischi operativi o ritardi nelle riattivazioni delle miniere sotterranee (McArthur River, Cigar Lake)",
            "Cambiamenti politici o contraccolpi sul sentiment dell'opinione pubblica verso il nucleare"
        ],
        "related_tickers": ["$URA", "$LEU", "$NXE"], "primary_tags": ["$CCJ"]
    },
    "ENEL.MI": {
        "ticker": "ENEL.MI", "yahoo_ticker": "ENEL.MI", "name": "Enel S.p.A.", "emoji": "🔋",
        "asset_class": "Stock", "sector": "Utility & Reti Elettriche Smart", "geo": "Europe", "tier": "High Dividend",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione semestrale con generoso dividend yield (~6.2%) e politica di payout in crescita costante", "annual_yield_pct": 6.2, "frequency": "Semestrale (Gennaio / Luglio)",
        "domain": "enel.com", "color": (0, 200, 80),
        "desc": "European smart grid and clean energy distribution leader with a dependable and generous dividend yield.",
        "thesis": "Monopolio naturale delle reti elettriche in Europa e America Latina con ricavi regolati protetti dall'inflazione, oltre 60 GW di capacità rinnovabile e dividendo generoso supportato dalla riduzione del debito.",
        "upside_catalysts": [
            "Ricavi tariffari regolati e stabili derivanti dall'elettrificazione e modernizzazione delle smart grid",
            "Completamento del piano di dismissioni che riduce il debito netto e libera cassa per gli azionisti",
            "Efficienza operativa e crescita della redditività del capitale investito nelle rinnovabili"
        ],
        "downside_risks": [
            "Sensibilità del costo del debito a tassi d'interesse bancari prolungatamente elevati",
            "Interventi governativi straordinari o tetti sui prezzi energetici nei mercati chiave",
            "Volatilità meteorologica su produzione idroelettrica ed eolica"
        ],
        "related_tickers": ["$IBE.MC", "$EDP.LS", "$RWE.DE"], "primary_tags": ["$ENEL.MI", "$ENLAY"]
    },
    "ENI.MI": {
        "ticker": "ENI.MI", "yahoo_ticker": "ENI.MI", "name": "Eni S.p.A.", "emoji": "⛽",
        "asset_class": "Stock", "sector": "Major Energetica, Gas & Bioraffinazione", "geo": "Europe", "tier": "High Dividend",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione trimestrale (4 tranche/anno) con dividend yield tra i più ricchi d'Europa (~6.8%) e buyback", "annual_yield_pct": 6.8, "frequency": "Trimestrale (Mar/Mag/Set/Nov)",
        "domain": "eni.com", "color": (255, 200, 0),
        "desc": "Integrated energy major generating resilient free cash flow, scaling bio-refining (Enilive) and renewables (Plenitude).",
        "thesis": "Major integrata dell'energia con straordinaria generazione di cassa, leadership nell'esplorazione rapida (fast-time-to-market), modello satellitare che valorizza asset strategici (Plenitude, Enilive) e ricchi dividendi.",
        "upside_catalysts": [
            "Valorizzazione e quotazione/partnership strategiche dei veicoli satellitari Enilive (bioraffinazione) e Plenitude",
            "Nuove scoperte ed entrate in produzione di giacimenti a basso costo di estrazione (Costa d'Avorio, Mozambico, Indonesia)",
            "Ritorno di capitale agli azionisti con combinazione di dividendo crescente e buyback massicci"
        ],
        "downside_risks": [
            "Forte calo prolungato delle quotazioni internazionali del greggio Brent e del gas naturale",
            "Rischi geopolitici e complessità operativa in paesi emergenti o aree africane",
            "Transizione normativa europea verso standard emissivi sempre più restrittivi"
        ],
        "related_tickers": ["$SHEL", "$TTE", "$BP"], "primary_tags": ["$ENI.MI", "$E"]
    },
    "PRY.MI": {
        "ticker": "PRY.MI", "yahoo_ticker": "PRY.MI", "name": "Prysmian S.p.A.", "emoji": "🔌",
        "asset_class": "Stock", "sector": "Cavi & Infrastrutture di Rete Elettrica", "geo": "Europe", "tier": "Industrial Leader",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione annuale con dividend yield moderato (~1.5%) e focus su reinvestimento industriale", "annual_yield_pct": 1.5, "frequency": "Annuale (Maggio)",
        "domain": "prysmiangroup.com", "color": (0, 70, 160),
        "desc": "Worldwide number one in subsea and underground power cables critical for global electrification and offshore wind.",
        "thesis": "Leader mondiale indiscusso nei sistemi in cavo per l'energia, le interconnessioni sottomarine HVDC dei parchi eolici offshore e il cablaggio in fibra per i data center AI, con un portafoglio ordini record superiore a 18 miliardi di euro.",
        "upside_catalysts": [
            "Portafoglio ordini blindato e pluriennale nei collegamenti ad altissima tensione (HVDC)",
            "Integrazione strategica di Encore Wire che consolida la leadership nel mercato nordamericano",
            "Espansione della flotta di navi posacavi proprietarie ad altissima tecnologia"
        ],
        "downside_risks": [
            "Fluttuazioni nei costi di acquisto di materie prime industriali (rame e alluminio)",
            "Complessità esecutiva e rischi meteorologici nelle pose sottomarine oceaniche",
            "Possibili ritardi nelle autorizzazioni per grandi progetti infrastrutturali di rete"
        ],
        "related_tickers": ["$NEX.PA", "$NKT.CO", "$ENEL.MI"], "primary_tags": ["$PRY.MI", "$PRY"]
    },
    "GLEN.L": {
        "ticker": "GLEN.L", "yahoo_ticker": "GLEN.L", "name": "Glencore PLC", "emoji": "⛏️",
        "asset_class": "Stock", "sector": "Metalli di Transizione (Rame) & Trading", "geo": "Europe", "tier": "Commodities",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione semestrale con elevato dividend yield (~4.8%) e ritorni di capitale ciclici", "annual_yield_pct": 4.8, "frequency": "Semestrale (Maggio / Settembre)",
        "domain": "glencore.com", "color": (100, 100, 100),
        "desc": "Global mining and marketing leader in copper, cobalt, and nickel essential for electric vehicles and power grids.",
        "thesis": "Esposizione strategica ai metalli critici indispensabili per l'elettrificazione mondiale e l'AI (rame, cobalto, nichel), supportata da una divisione marketing e trading globale unica che genera miliardi di cassa in ogni scenario di volatilità.",
        "upside_catalysts": [
            "Deficit secolare di rame fisico globale che spinge al rialzo le quotazioni del metallo rosso",
            "Profitti stabili e anticiclici generati dalle attività di trading e arbitraggio globale delle materie prime",
            "Completamento dell'integrazione degli asset di carbone siderurgico di Teck Resources con forte generazione di cassa"
        ],
        "downside_risks": [
            "Rallentamento prolungato dell'attività manifatturiera ed edilizia in Cina",
            "Rischi geopolitici e minerari in giurisdizioni africane o sudamericane",
            "Volatilità dei costi energetici ed estrattivi"
        ],
        "related_tickers": ["$RIO.L", "$BHP.L", "$AAL.L"], "primary_tags": ["$GLEN.L"]
    },
    "TRIG.L": {
        "ticker": "TRIG.L", "yahoo_ticker": "TRIG.L", "name": "The Renewables Infrastructure Group Ltd", "emoji": "🌬️",
        "asset_class": "Stock", "sector": "Infrastrutture Rinnovabili Eoliche/Solari UK/EU", "geo": "Europe", "tier": "High Yield Green",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione trimestrale con dividend yield molto elevato (~7.4%) supportato da contratti PPA indicizzati", "annual_yield_pct": 7.4, "frequency": "Trimestrale (Mar/Giu/Set/Dic)",
        "domain": "trig-ltd.com", "color": (0, 180, 160),
        "desc": "UK clean energy infrastructure investment trust holding an operational portfolio of European wind and solar assets.",
        "thesis": "Trust infrastrutturale quotato a Londra con oltre 85 impianti di energia pulita operativi (eolico onshore/offshore, parchi solari e batterie) in UK ed Europa, contratti a lungo termine indicizzati all'inflazione e dividendo trimestrale affidabile.",
        "upside_catalysts": [
            "Rendimento cedolare reale protetto dall'inflazione tramite sussidi statali e contratti a tariffa garantita (CfD/PPA)",
            "Espansione nello storage a batteria per monetizzare i picchi di prezzo dell'elettricità",
            "Potenziale re-rating del NAV con la normalizzazione della curva dei tassi d'interesse"
        ],
        "downside_risks": [
            "Sensibilità del valore contabile delle quote all'andamento dei rendimenti obbligazionari sovrani (Gilt/Bund)",
            "Calo prolungato dei prezzi dell'elettricità all'ingrosso per la quota non coperta da contratti fissi",
            "Variabilità climatica e ventosità stagionale inferiore alle medie storiche"
        ],
        "related_tickers": ["$UKW.L", "$FSFL.L", "$ENEL.MI"], "primary_tags": ["$TRIG.L"]
    },
    "MAU.PA": {
        "ticker": "MAU.PA", "yahoo_ticker": "MAU.PA", "name": "Etablissements Maurel & Prom SA", "emoji": "🛢️",
        "asset_class": "Stock", "sector": "Esplorazione & Produzione Idrocarburi", "geo": "Europe", "tier": "Tactical Energy",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione annuale con dividend yield generoso (~4.5%) e politica di remunerazione legata al free cash flow", "annual_yield_pct": 4.5, "frequency": "Annuale (Luglio)",
        "domain": "maureletprom.fr", "color": (180, 140, 50),
        "desc": "Cash-rich oil and gas producer with strong balance sheet discipline and high dividend payouts.",
        "thesis": "Produttore petrolifero indipendente caratterizzato da cassa netta positiva, costi di estrazione contenuti, asset strategici in Gabon, Angola e Tanzania, e una politica di remunerazione degli azionisti generosa.",
        "upside_catalysts": [
            "Monetizzazione della produzione di gas in Tanzania e asset petroliferi consolidati in Gabon",
            "Crescita dei dividendi supportata dalla solida posizione di cassa netta",
            "Opportunità di M&A e incremento delle riserve certe 2P"
        ],
        "downside_risks": [
            "Sensibilità al prezzo del barile di greggio sui mercati internazionali",
            "Rischio paese legato al quadro politico e regolatorio in Africa centrale",
            "Tempi di approvazione per il rimpatrio dei flussi di cassa operativi"
        ],
        "related_tickers": ["$TTE", "$ENI.MI", "$SHEL"], "primary_tags": ["$MAU.PA"]
    },

    # ── Consumer, Retail & Luxury ─────────────────────────────────────────────
    "WMT": {
        "ticker": "WMT", "yahoo_ticker": "WMT", "name": "Walmart Inc.", "emoji": "🛒",
        "asset_class": "Stock", "sector": "Retail Globale & Logistica Omnicanale", "geo": "USA", "tier": "Core Defensive",
        "is_dividend_paying": True, "dividend_policy": "Dividend Aristocrat con oltre 50 anni consecutivi di aumenti (~1.3% yield)", "annual_yield_pct": 1.3, "frequency": "Trimestrale (Mar/Mag/Ago/Dic)",
        "domain": "walmart.com", "color": (0, 113, 206),
        "desc": "World's largest retailer by revenue, accelerating automated fulfillment, e-commerce scale, and retail media network.",
        "thesis": "La più grande azienda retail al mondo per fatturato, trasformata in un gigante omnicanale ad alta tecnologia con automazione avanzata della logistica, crescita fulminea dell'e-commerce e margini elevati dalla pubblicità retail (Walmart Connect).",
        "upside_catalysts": [
            "Guadagno di quote di mercato anche tra i consumatori ad alto reddito attratti da convenienza e convenienza digitale",
            "Espansione ad altissimo margine della piattaforma pubblicitaria e dei servizi marketplace a terzi",
            "Automazione completa della catena di distribuzione con riduzione strutturale dei costi operativi"
        ],
        "downside_risks": [
            "Pressione sui margini derivante da rincari salariali o costi di trasporto",
            "Forte concorrenza di Amazon nel commercio digitale e nella consegna rapida",
            "Sensibilità ai dazi commerciali sulle merci importate"
        ],
        "related_tickers": ["$AMZN", "$COST", "$TGT"], "primary_tags": ["$WMT"]
    },
    "MELI": {
        "ticker": "MELI", "yahoo_ticker": "MELI", "name": "MercadoLibre Inc", "emoji": "🛒",
        "asset_class": "Stock", "sector": "E-Commerce & Fintech America Latina", "geo": "Emerging", "tier": "High Growth",
        "is_dividend_paying": False, "dividend_policy": "Nessun dividendo distribuito; reinvestimento al 100% dell'enorme flusso di cassa per espandere il monopolio in America Latina", "annual_yield_pct": 0.0, "frequency": "Nessuna",
        "domain": "mercadolibre.com", "color": (255, 220, 0),
        "desc": "The 'Amazon + PayPal' of Latin America, delivering exponential growth in digital commerce, credit, and logistics.",
        "thesis": "L'indiscusso 'Amazon + PayPal' dell'America Latina (Brasile, Messico, Argentina): barriera all'entrata insormontabile grazie alla rete logistica proprietaria Mercado Envíos e all'ecosistema finanziario Mercado Pago.",
        "upside_catalysts": [
            "Crescita a doppia cifra dei volumi venduti (GMV) e leadership consolidata nel commercio elettronico",
            "Espansione esponenziale dei servizi bancari digitali, carte di credito e prestiti con Mercado Pago",
            "Monetizzazione rapida del business pubblicitario retail media (Mercado Ads)"
        ],
        "downside_risks": [
            "Volatilità macroeconomica e svalutazioni valutarie nei paesi latinoamericani (Real, Peso)",
            "Incremento del tasso di insolvenza nel portafoglio prestiti consumer credit",
            "Concorrenza di marketplace asiatici su determinate categorie di prodotto"
        ],
        "related_tickers": ["$AMZN", "$BABA", "$SE"], "primary_tags": ["$MELI"]
    },
    "RACE": {
        "ticker": "RACE", "yahoo_ticker": "RACE", "name": "Ferrari N.V.", "emoji": "🏎️",
        "asset_class": "Stock", "sector": "Automotive Ultra-Luxury & Motorsport", "geo": "Europe", "tier": "Ultra-Luxury Moat",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione annuale con dividendo in costante aumento (~0.7% yield) e forte politica di buyback", "annual_yield_pct": 0.7, "frequency": "Annuale (Maggio)",
        "domain": "ferrari.com", "color": (255, 40, 0),
        "desc": "Peerless luxury pricing power, industry-leading operating margins, and multi-year waitlists across all models.",
        "thesis": "Marchio del lusso assoluto con potere di prezzo totale, margini operativi EBITDA leader nel settore automobilistico (>38%), liste d'attesa pluriennali su ogni modello e lancio della prima supercar 100% elettrica.",
        "upside_catalysts": [
            "Portafoglio ordini completamente esaurito per oltre 2 anni con personalizzazioni 'Tailor Made' ad altissimo margine",
            "Successo commerciale continuo di modelli esclusivi a tiratura limitata (serie Icona e supercar speciali)",
            "Debutto e accoglienza trionfale della prima Ferrari completamente elettrica"
        ],
        "downside_risks": [
            "Rallentamento generale della spesa tra i clienti ultra-high-net-worth (UHNW)",
            "Complessità nello sviluppo e percezione del sound/DNA emozionale sui modelli a batteria",
            "Impatti valutari sul cambio euro/dollaro"
        ],
        "related_tickers": ["$VOW3.DE", "$MBG.DE", "$P911.DE"], "primary_tags": ["$RACE"]
    },
    "VOW3.DE": {
        "ticker": "VOW3.DE", "yahoo_ticker": "VOW3.DE", "name": "Volkswagen AG", "emoji": "🚗",
        "asset_class": "Stock", "sector": "Automotive Conglomerate & Piattaforme EV", "geo": "Europe", "tier": "Deep Value",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione annuale con dividend yield molto elevato (~7.5%)", "annual_yield_pct": 7.5, "frequency": "Annuale (Maggio/Giugno)",
        "domain": "volkswagen.com", "color": (0, 70, 150),
        "desc": "Global automotive conglomerate (Porsche, Audi, VW) with massive industrial manufacturing scale in transition.",
        "thesis": "Colosso industriale globale (marchi Porsche, Audi, Lamborghini, Volkswagen) scambiato a multipli di profondo sconto (deep value), forte liquidità industriale netta e dividendo ricco.",
        "upside_catalysts": [
            "Piano di ristrutturazione e taglio dei costi fissi per incrementare la competitività europea",
            "Sinergie di piattaforma elettrica e partnership strategiche software (Rivian, Xpeng)",
            "Generoso flusso cedolare annuale per gli azionisti ordinari e privilegiati"
        ],
        "downside_risks": [
            "Concorrenza spietata sui prezzi dei veicoli elettrici da parte dei produttori cinesi in Cina ed Europa",
            "Costi elevati di transizione energetica, sviluppo software e vincoli sindacali in Germania",
            "Normative europee stringenti sulle emissioni medie di flotta"
        ],
        "related_tickers": ["$RACE", "$MBG.DE", "$BMW.DE"], "primary_tags": ["$VOW3.DE"]
    },
    "ULVR.L": {
        "ticker": "ULVR.L", "yahoo_ticker": "ULVR.L", "name": "Unilever PLC", "emoji": "🧼",
        "asset_class": "Stock", "sector": "Beni di Largo Consumo (Consumer Staples)", "geo": "Europe", "tier": "Core Defensive",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione trimestrale costante con dividend yield difensivo (~3.6%)", "annual_yield_pct": 3.6, "frequency": "Trimestrale (Mar/Giu/Set/Dic)",
        "domain": "unilever.com", "color": (0, 90, 180),
        "desc": "Portfolio of 400+ household consumer staple brands used daily by over 3.4 billion people worldwide.",
        "thesis": "Roccia difensiva nei beni di largo consumo con oltre 400 marchi iconici (Dove, Knorr, Rexona, Hellmann's), forte pricing power, 60% dei ricavi nei mercati emergenti e dividendi ininterrotti da decenni.",
        "upside_catalysts": [
            "Piano strategico 'Growth Action Plan' focalizzato sui 30 Power Brands ad alta redditività",
            "Espansione dei margini operativi lordi grazie al rallentamento dei costi delle materie prime",
            "Crescita demografica ed economica nei mercati emergenti in Asia e America Latina"
        ],
        "downside_risks": [
            "Pressione concorrenziale dei marchi commerciali private-label discount nei periodi di inflazione",
            "Fluttuazioni valutarie tra valute emergenti e sterlina/euro",
            "Costi di ristrutturazione e scorporo della divisione gelati (Ice Cream)"
        ],
        "related_tickers": ["$PG", "$NESN.SW", "$KO"], "primary_tags": ["$ULVR.L", "$UL"]
    },

    # ── Asia & Emerging Markets ───────────────────────────────────────────────
    "1211.HK": {
        "ticker": "1211.HK", "yahoo_ticker": "1211.HK", "name": "BYD Co Ltd", "emoji": "🔋",
        "asset_class": "Stock", "sector": "Veicoli Elettrici & Batterie Blade", "geo": "Asia", "tier": "Global EV Leader",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione annuale con dividend yield moderato (~1.1%) e priorità su espansione globale", "annual_yield_pct": 1.1, "frequency": "Annuale (Giugno)",
        "domain": "byd.com", "color": (30, 144, 255),
        "desc": "Worldwide leader in EV production and vertical integration, proprietary Blade Battery safety architecture.",
        "thesis": "Leader mondiale assoluto per volumi di produzione di veicoli elettrici e ibridi plug-in (NEV), dotato di un'integrazione verticale totale (batterie proprietarie Blade, semiconduttori, motori) e forte espansione nei mercati internazionali.",
        "upside_catalysts": [
            "Espansione delle esportazioni e impianti produttivi locali in Europa (Ungheria), Sud-est asiatico e Brasile",
            "Lancio di modelli premium (Yangwang, Denza, Fangchengbao) ad altissima marginalità",
            "Leadership tecnologica nella chimica delle batterie LFP ad altissima sicurezza e densità energetica"
        ],
        "downside_risks": [
            "Dazi doganali e barriere commerciali imposte da Unione Europea e USA sui veicoli cinesi",
            "Guerra dei prezzi feroce nel mercato automobilistico domestico cinese",
            "Fluttuazioni nei costi delle materie prime per accumulatori (litio, cobalto)"
        ],
        "related_tickers": ["$TSLA", "$NIO", "$XPEV"], "primary_tags": ["$1211.HK", "$BYDDF"]
    },
    "1919.HK": {
        "ticker": "1919.HK", "yahoo_ticker": "1919.HK", "name": "COSCO SHIPPING Holdings Co Ltd", "emoji": "🚢",
        "asset_class": "Stock", "sector": "Logistica Marittima Globale & Terminal Portuali", "geo": "Asia", "tier": "Cyclical / High Yield",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione semestrale (interim + final) con dividend yield molto elevato (~6.2%) e buyback", "annual_yield_pct": 6.2, "frequency": "Semestrale (Giugno / Ottobre)",
        "domain": "lines.coscoshipping.com", "color": (0, 80, 160),
        "desc": "Global maritime shipping conglomerate operating premier container vessel fleets and critical terminal ports.",
        "thesis": "Spina dorsale del commercio marittimo mondiale (3° vettore container al mondo con oltre 3.1 milioni di TEU), solida rete proprietaria di terminal portuali, riserve di liquidità nette massicce e dividendi straordinari.",
        "upside_catalysts": [
            "Tenuta dei tassi di nolo marittimo sostenuti da rotte circumnaviganti e domanda resiliente",
            "Fortezza di cassa industriale che alimenta payout generosi e riacquisti di azioni",
            "Rinnovamento della flotta con navi a doppio combustibile a metanolo verde e GNL"
        ],
        "downside_risks": [
            "Volatilità ciclica dei tassi spot di trasporto container marittimo",
            "Incremento dell'offerta globale di nuove navi in consegna dai cantieri",
            "Tensioni geopolitiche sulle rotte commerciali globali e guerre tariffarie"
        ],
        "related_tickers": ["$ZIM", "$MATX", "$1138.HK"], "primary_tags": ["$1919.HK", "$CICOY"]
    },
    "2318.HK": {
        "ticker": "2318.HK", "yahoo_ticker": "2318.HK", "name": "Ping An Insurance Group", "emoji": "🏦",
        "asset_class": "Stock", "sector": "Assicurazioni, Finanza Digitale & Insurtech", "geo": "Asia", "tier": "Asia Value",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione semestrale con ricco dividend yield (~6.5%) e payout solido", "annual_yield_pct": 6.5, "frequency": "Semestrale (Giugno / Ottobre)",
        "domain": "pingan.com", "color": (230, 80, 0),
        "desc": "China's leading tech-driven financial services and insurance conglomerate with deep value fundamentals.",
        "thesis": "Colosso assicurativo e finanziario leader in Asia con oltre 235 milioni di clienti retail, pioniere nell'insurtech e nell'ecosistema 'Finanza + Sanità Privata', scambiato a multipli storicamente a forte sconto.",
        "upside_catalysts": [
            "Crescita del New Business Value (NBV) guidata dalla qualità e produttività della rete di agenti",
            "Integrazione dei servizi sanitari e telemedicina proprietaria (Ping An Good Doctor)",
            "Potenziale re-rating delle valutazioni azionarie cinesi e dividendo attraente"
        ],
        "downside_risks": [
            "Esposizione del portafoglio investimenti al ciclo immobiliare residenziale cinese",
            "Volatilità dei mercati azionari domestici cinesi che incide sui rendimenti finanziari",
            "Interventi regolatori sulle polizze vita e prodotti previdenziali"
        ],
        "related_tickers": ["$2628.HK", "$3968.HK", "$939.HK"], "primary_tags": ["$2318.HK", "$PNGAY"]
    },
    "VOF.L": {
        "ticker": "VOF.L", "yahoo_ticker": "VOF.L", "name": "VinaCapital Vietnam Opportunity Fund", "emoji": "🇻🇳",
        "asset_class": "Fund / Closed-End", "sector": "Azionario Frontier Market Vietnam", "geo": "Asia / Frontier", "tier": "High Growth Explorer",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione semestrale con dividend yield moderato (~1.5%) e buyback per ridurre lo sconto sul NAV", "annual_yield_pct": 1.5, "frequency": "Semestrale (Marzo / Ottobre)",
        "domain": "vinacapital.com", "color": (218, 37, 29),
        "desc": "Specialist fund capturing the secular industrialization and consumption boom in Vietnam's high-growth economy.",
        "thesis": "Fondo chiuso quotato a Londra specializzato nella crescita secolare del Vietnam come nuovo polo manifatturiero mondiale alternativo alla Cina (strategia 'China+1') ed espansione dei consumi della classe media.",
        "upside_catalysts": [
            "Forte afflusso di investimenti diretti esteri (FDI) da giganti tech globali in Vietnam",
            "Crescita del PIL reale tra il 6% e il 7% annuo con demografia giovane",
            "Potenziale upgrade del mercato vietnamita da status di Frontiera a Mercato Emergente nei principali indici globali"
        ],
        "downside_risks": [
            "Volatilità dei mercati di frontiera e liquidità contenuta delle borse locali",
            "Oscillazioni valutarie del Dong vietnamita rispetto alle valute occidentali",
            "Eventuali riforme regolatorie sul settore bancario o immobiliare domestico"
        ],
        "related_tickers": ["$VNM", "$VEIL.L", "$VOF.L"], "primary_tags": ["$VOF.L"]
    },
    "INDO.PA": {
        "ticker": "INDO.PA", "yahoo_ticker": "INDO.PA", "name": "Amundi MSCI Indonesia UCITS ETF Acc", "emoji": "🇮🇩",
        "asset_class": "ETF", "sector": "Azionario Mercati Emergenti Indonesia", "geo": "Asia / Emerging", "tier": "Emerging Market",
        "is_dividend_paying": False, "dividend_policy": "Accumulazione (Acc) - Nessun dividendo distribuito, tutti i proventi e dividendi sono automaticamente capitalizzati e reinvestiti nel NAV", "annual_yield_pct": 0.0, "frequency": "Nessuna (Accumulazione)",
        "domain": "amundi.com", "color": (255, 0, 0),
        "desc": "Targeted exposure to Indonesia's booming economy, backed by vast nickel reserves and demographic expansion.",
        "thesis": "Esposizione mirata alla crescita demografica del sud-est asiatico e al ruolo insostituibile dell'Indonesia come primo detentore mondiale di riserve di nickel e materie prime per la filiera delle batterie EV.",
        "upside_catalysts": [
            "Posizione monopolistica nella fornitura di nickel lavorato e attrazione di investimenti industriali esteri",
            "Forte espansione del PIL reale e stabilità macroeconomica",
            "Crescita della bancarizzazione e dei consumi interni di oltre 275 milioni di abitanti"
        ],
        "downside_risks": [
            "Volatilità delle quotazioni internazionali dei metalli industriali e del nickel",
            "Rischio di cambio della Rupia indonesiana rispetto all'euro",
            "Cambiamenti nelle politiche di esportazione di minerali grezzi da parte del governo indonesiano"
        ],
        "related_tickers": ["$EIDO", "$INDO.PA", "$IEMG"], "primary_tags": ["$INDO.PA"]
    },

    # ── Strategic ETFs, Defence, Metals & Cash Reserves ────────────────────────
    "WDEF.L": {
        "ticker": "WDEF.L", "yahoo_ticker": "WDEF.L", "name": "WisdomTree Europe Defence UCITS ETF", "emoji": "🛡️",
        "asset_class": "ETF", "sector": "Difesa Europea & Aerospazio", "geo": "Europe", "tier": "Strategic Defence ETF",
        "is_dividend_paying": False, "dividend_policy": "Accumulazione (Acc) - Nessun dividendo distribuito, tutti i proventi e dividendi delle società sottostanti sono automaticamente capitalizzati e reinvestiti nel valore della quota (NAV)", "annual_yield_pct": 0.0, "frequency": "Nessuna (Accumulazione)",
        "domain": "wisdomtree.com", "color": (0, 120, 215),
        "desc": "Targeted exposure to leading European aerospace and defence companies benefiting from structural NATO rearmament.",
        "thesis": "Esposizione diretta e mirata ai campioni europei dell'aerospazio, sicurezza e difesa (Rheinmetall, BAE Systems, Leonardo, Saab, Thales, Airbus) per catturare il megatrend decennale di riarmo strategico e aumento strutturale dei budget NATO oltre il 2% del PIL.",
        "upside_catalysts": [
            "Aumento vincolante dei budget di spesa militare nei paesi europei e NATO verso il 2.5-3% del PIL",
            "Portafogli ordini record pluriennali per le aziende della difesa che garantiscono visibilità sui ricavi per il prossimo decennio",
            "Piani europei di difesa aerea congiunta, modernizzazione delle flotte e ricostituzione degli arsenali strategici"
        ],
        "downside_risks": [
            "Colli di bottiglia nelle catene di fornitura aerospaziali e reperibilità di componenti critici",
            "Possibili ritardi burocratici o rinegoziazioni nelle tempistiche dei contratti di approvvigionamento governativi",
            "Volatilità del sentiment legata a sviluppi geopolitici o distensione diplomatica"
        ],
        "related_tickers": ["$RHM.DE", "$BA.L", "$LMT"], "primary_tags": ["$WDEF.L"]
    },
    "PPFB.DE": {
        "ticker": "PPFB.DE", "yahoo_ticker": "PPFB.DE", "name": "iShares Physical Gold ETC", "emoji": "🥇",
        "asset_class": "Commodities", "sector": "Oro Fisico Safe Haven", "geo": "Global", "tier": "Safe Haven Hedge",
        "is_dividend_paying": False, "dividend_policy": "Nessun dividendo (ETC su metallo fisico); copertura patrimoniale 100% garantita da lingotti d'oro custoditi nei caveau di Londra", "annual_yield_pct": 0.0, "frequency": "Nessuna",
        "domain": "ishares.com", "color": (255, 215, 0),
        "desc": "Direct structural hedge against currency debasement and geopolitical turmoil, 100% physically backed in London vaults.",
        "thesis": "Copertura strutturale e difensiva contro la svalutazione monetaria, l'inflazione secolare e le tensioni geopolitiche, garantita al 100% da lingotti d'oro fisico allocati nei caveau di Londra.",
        "upside_catalysts": [
            "Acquisti record continui di oro fisico da parte delle banche centrali mondiali per de-dollarizzare le riserve",
            "Taglio dei tassi d'interesse reali globali che riduce il costo opportunità di detenere metallo prezioso",
            "Flussi difensivi verso asset rifugio durante crisi geopolitiche o bancarie"
        ],
        "downside_risks": [
            "Fasi di forte rialzo dei rendimenti obbligazionari reali privi di rischio",
            "Rafforzamento prolungato del dollaro statunitense",
            "Prese di profitto dopo rally storici delle quotazioni spot dell'oro"
        ],
        "related_tickers": ["$GLD", "$IAU", "$SLV"], "primary_tags": ["$PPFB.DE"]
    },
    "SX7PEX.DE": {
        "ticker": "SX7PEX.DE", "yahoo_ticker": "EXV1.DE", "name": "iShares STOXX Europe 600 Banks UCITS ETF", "emoji": "🏛️",
        "asset_class": "ETF", "sector": "Banche Europee ad Alto Rendimento", "geo": "Europe", "tier": "Value & High Yield",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione semestrale con generoso dividend yield (~7.2%) derivante dagli stacchi dei primari istituti bancari europei", "annual_yield_pct": 7.2, "frequency": "Semestrale (Giugno / Dicembre)",
        "domain": "ishares.com", "color": (70, 130, 240),
        "desc": "Basket of top European financial institutions benefiting from sustained net interest margins and share buybacks.",
        "thesis": "Paniere dei maggiori istituti bancari europei (BNP Paribas, Santander, Intesa Sanpaolo, BBVA, ING) caratterizzati da bilanci solidi, coefficienti patrimoniali CET1 ai massimi storici (>15.5%), tassi d'interesse favorevoli e ricchi dividendi.",
        "upside_catalysts": [
            "Margini di interesse netti (NIM) elevati e stabili nel nuovo contesto di tassi normalizzati",
            "Ritorno di capitale agli azionisti con combinazione di generosi dividendi semestrali e buyback",
            "Basso livello di crediti deteriorati (NPL) e rigore patrimoniale imposto dalla vigilanza BCE"
        ],
        "downside_risks": [
            "Eventuali shock recessivi nell'Eurozona che aumentano gli accantonamenti su crediti",
            "Tagli dei tassi d'interesse più rapidi del previsto da parte della BCE",
            "Imposte straordinarie sugli extraprofitti bancari introdotte dai governi europei"
        ],
        "related_tickers": ["$BAC", "$JPM", "$HSBA.L"], "primary_tags": ["$SX7PEX.DE", "$EXV1.DE"]
    },
    "IEUR": {
        "ticker": "IEUR", "yahoo_ticker": "IEUR", "name": "iShares Core MSCI Europe ETF", "emoji": "🇪🇺",
        "asset_class": "ETF", "sector": "Azionario Europeo Broad Market", "geo": "Europe", "tier": "Core Diversifier",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione semestrale con dividend yield diversificato (~2.5%)", "annual_yield_pct": 2.5, "frequency": "Semestrale (Giugno / Dicembre)",
        "domain": "ishares.com", "color": (0, 51, 153),
        "desc": "Low-cost broad market exposure to 400+ leading multinational corporations across developed Europe.",
        "thesis": "Esposizione completa, diversificata e a bassissimo costo alle migliori multinazionali europee su tutti i settori economici, a multipli storicamente a sconto rispetto a Wall Street.",
        "upside_catalysts": [
            "Valutazioni a sconto del mercato azionario europeo rispetto all'S&P 500 che favoriscono rotazioni value",
            "Dividendi solidi e programmi di riacquisto azioni diffuse tra le blue chip europee",
            "Crescita dei ricavi globali generati dalle multinazionali europee esposte a mercati internazionali"
        ],
        "downside_risks": [
            "Rallentamento della crescita economica e produttività dell'Eurozona",
            "Pressioni sui costi energetici e regolamentari per le industrie del continente",
            "Impatto di eventuali barriere doganali USA sulle esportazioni europee"
        ],
        "related_tickers": ["$VGK", "$EZU", "$FEZ"], "primary_tags": ["$IEUR"]
    },
    "IQQL.DE": {
        "ticker": "IQQL.DE", "yahoo_ticker": "IQQL.DE", "name": "iShares Listed Private Equity UCITS ETF", "emoji": "🔥",
        "asset_class": "ETF", "sector": "Private Equity Quotato & Gestori Alternativi", "geo": "Global", "tier": "Alternative Asset",
        "is_dividend_paying": True, "dividend_policy": "Distribuzione semestrale con dividend yield attraente (~3.5%)", "annual_yield_pct": 3.5, "frequency": "Semestrale (Maggio / Novembre)",
        "domain": "ishares.com", "color": (255, 69, 0),
        "desc": "Liquid access to the world's premier alternative asset managers and buyout leaders (Blackstone, KKR, Carlyle).",
        "thesis": "Accesso liquido e trasparente ai giganti mondiali del private equity e della gestione di asset alternativi (Blackstone, KKR, Carlyle, EQT), capaci di generare extra-rendimento (alpha) e commissioni di performance nel lungo periodo.",
        "upside_catalysts": [
            "Riapertura del mercato delle IPO e delle uscite societarie (M&A) che sblocca commissioni di performance",
            "Crescita record degli asset alternativi in gestione (AUM) e del private credit globale",
            "Flussi cedolari stabili derivanti dalle commissioni di gestione ricorrenti"
        ],
        "downside_risks": [
            "Sensibilità delle valutazioni delle società in portafoglio ai tassi d'interesse a lungo termine",
            "Rallentamento delle raccolte fondi tra gli investitori istituzionali in periodi di incertezza",
            "Volatilità delle quotazioni azionarie dei gestori quotati"
        ],
        "related_tickers": ["$QUAL", "$IWDA.L", "$VWCE.L"], "primary_tags": ["$IQQL.DE"]
    },
    "IB01.L": {
        "ticker": "IB01.L", "yahoo_ticker": "IB01.L", "name": "iShares $ Treasury Bond 0-1yr UCITS ETF", "emoji": "💵",
        "asset_class": "Fixed Income", "sector": "Titoli di Stato USA Ultra-Breve Termine (Cash Yield)", "geo": "USA", "tier": "Cash Yield & Dry Powder",
        "is_dividend_paying": False, "dividend_policy": "Accumulazione (Acc) - Nessun dividendo distribuito, gli interessi sui Treasury USA 0-1yr vengono automaticamente capitalizzati e reinvestiti nel NAV", "annual_yield_pct": 0.0, "frequency": "Nessuna (Accumulazione)",
        "domain": "ishares.com", "color": (34, 139, 34),
        "desc": "Ultra-short US government paper yielding risk-free USD interest while preserving dry powder for market corrections.",
        "thesis": "Riserva strategica di liquidità in dollari (T-Bills a brevissima scadenza) che genera un rendimento privo di rischio di credito e duration quasi nulla, preservando 'polvere da sparo' per comprare i ribassi di mercato.",
        "upside_catalysts": [
            "Tassi risk-free sui titoli di stato USA a breve termine che remunerano la liquidità senza rischio di volatilità",
            "Capitale immediatamente disponibile per cogliere opportunità straordinarie su titoli growth a sconto",
            "Copertura patrimoniale e decorrelazione totale dai mercati azionari"
        ],
        "downside_risks": [
            "Discesa dei rendimenti monetari con il ciclo di allentamento della Federal Reserve",
            "Rischio di cambio per investitori la cui valuta di base non è il dollaro USA"
        ],
        "related_tickers": ["$SHY", "$BIL", "$XEON.DE"], "primary_tags": ["$IB01.L"]
    },
    "XEON.DE": {
        "ticker": "XEON.DE", "yahoo_ticker": "XEON.DE", "name": "Xtrackers II EUR Overnight Rate Swap UCITS ETF", "emoji": "💤",
        "asset_class": "Fixed Income", "sector": "Liquidità Remunerata Tasso BCE (Overnight €STR)", "geo": "Europe", "tier": "Cash Yield & Dry Powder",
        "is_dividend_paying": False, "dividend_policy": "Accumulazione (Acc) - Nessun dividendo distribuito, il rendimento overnight (€STR swap) viene capitalizzato giornalmente nel NAV della quota", "annual_yield_pct": 0.0, "frequency": "Nessuna (Accumulazione)",
        "domain": "dws.com", "color": (0, 40, 100),
        "desc": "Euro money market ETF tracking the €STR interbank rate with daily compounding, zero duration risk, and capital preservation.",
        "thesis": "Cassa remunerata in Euro al tasso ufficiale overnight interbancario (€STR) con capitalizzazione quotidiana dei rendimenti, zero rischio duration e massima protezione del capitale.",
        "upside_catalysts": [
            "Remunerazione priva di rischio della liquidità denominata in Euro",
            "Crescita giornaliera lineare del NAV senza alcuna oscillazione di mercato",
            "Riserva di liquidità sicura per il ribilanciamento tempestivo del portafoglio"
        ],
        "downside_risks": [
            "Rendimento legato all'evoluzione dei tassi sui depositi stabiliti dalla BCE",
            "Rendimento reale negativo in scenari di inflazione superiore al tasso overnight"
        ],
        "related_tickers": ["$CSH2.PA", "$XEON.DE", "$IB01.L"], "primary_tags": ["$XEON.DE"]
    },

    # ── Private / Space & Crypto Assets ───────────────────────────────────────
    "SPCX.RTH": {
        "ticker": "SPCX.RTH", "yahoo_ticker": "SPCX.RTH", "name": "Space Exploration Technologies Corp. (SpaceX)", "emoji": "🚀",
        "asset_class": "Private Equity", "sector": "Aerospazio, Razzi Orbitali & Starlink", "geo": "USA", "tier": "Pre-IPO Moat",
        "is_dividend_paying": False, "dividend_policy": "Nessun dividendo distribuito (Società privata pre-IPO); reinvestimento totale nei vettori Starship e costellazione Starlink", "annual_yield_pct": 0.0, "frequency": "Nessuna",
        "domain": "spacex.com", "color": (0, 80, 180),
        "desc": "Dominant global orbital rocket launch provider and operator of the Starlink broadband satellite constellation.",
        "thesis": "Monopolio assoluto mondiale nei lanci spaziali orbitali riutilizzabili (Falcon 9, Falcon Heavy, Starship), fornitore strategico della NASA e del Pentagono, e proprietario dell'infrastruttura internet satellitare Starlink.",
        "upside_catalysts": [
            "Crescita esplosiva degli abbonati e dei flussi di cassa operativi di Starlink in tutto il mondo",
            "Successo dei test e piena operatività commerciale del vettore pesante riutilizzabile Starship",
            "Potenziale quotazione IPO o spin-off di Starlink con creazione di enorme valore per gli investitori"
        ],
        "downside_risks": [
            "Società non quotata su mercati regolamentati, con liquidità limitata e valutazioni basate su round secondari",
            "Rischi tecnologici e complessità ingegneristica nei voli di collaudo orbitali",
            "Regolamentazione sulle frequenze satellitari e autorizzazioni di lancio FAA"
        ],
        "related_tickers": ["$RKLB", "$LMT", "$BA"], "primary_tags": ["$SPCX.RTH", "$SPACE"]
    },
    "ETOR": {
        "ticker": "ETOR", "yahoo_ticker": "ETOR", "name": "eToro Group Ltd", "emoji": "🏛️",
        "asset_class": "Stock", "sector": "Piattaforma Social Investing & Finanza Digitale", "geo": "Global", "tier": "Fintech Ecosystem",
        "is_dividend_paying": False, "dividend_policy": "Nessun dividendo distribuito; focus sulla crescita della piattaforma e scalabilità globale", "annual_yield_pct": 0.0, "frequency": "Nessuna",
        "domain": "etoro.com", "color": (19, 198, 54),
        "desc": "Pioneering global social investing and multi-asset trading platform with millions of active global users.",
        "thesis": "Piattaforma pioniera e leader globale del social trading e del copy investing, con milioni di utenti attivi, diversificazione multi-asset (azioni, ETF, crypto, materie prime) e forte scalabilità dei ricavi.",
        "upside_catalysts": [
            "Crescita dei volumi di trading e dell'adozione globale dei programmi Popular Investor e Copy Trading",
            "Espansione dei servizi finanziari digitali e diversificazione delle fonti di ricavo (interessi su cassa, carte di debito)",
            "Opportunità di sbarco sui mercati regolamentati tramite IPO pubblica"
        ],
        "downside_risks": [
            "Ciclicità dei volumi di trading retail legata alla volatilità generale dei mercati",
            "Evoluzione del quadro normativo e requisiti di compliance finanziaria nei mercati internazionali",
            "Concorrenza di piattaforme di trading e broker a zero commissioni"
        ],
        "related_tickers": ["$HOOD", "$COIN", "$IBKR"], "primary_tags": ["$ETOR"]
    },
    "TRX": {
        "ticker": "TRX", "yahoo_ticker": "TRX-USD", "name": "TRON Network", "emoji": "🪙",
        "asset_class": "Crypto", "sector": "Rete Blockchain & Regolamento Stablecoin USDT", "geo": "Global", "tier": "Digital Assets",
        "is_dividend_paying": False, "dividend_policy": "Nessun dividendo; rendimento derivante da staking on-chain e bruciatura di token deflazionistica", "annual_yield_pct": 0.0, "frequency": "Nessuna",
        "domain": "tron.network", "color": (255, 0, 0),
        "desc": "World's leading high-throughput blockchain network processing the highest volume of USDT stablecoin transfers.",
        "thesis": "Infrastruttura blockchain primaria al mondo per volume e numero di transazioni di stablecoin USDT (Tether), caratterizzata da commissioni bassissime, altissima velocità di regolamento e meccanismo di burn deflazionistico.",
        "upside_catalysts": [
            "Dominio incontrastato nei trasferimenti quotidiani di USDT nei mercati emergenti e nell'e-commerce",
            "Deflazione dell'offerta circolante di TRX guidata dall'elevata attività di rete e consumo di energia",
            "Integrazione crescente con servizi di pagamento digitali e piattaforme DeFi"
        ],
        "downside_risks": [
            "Volatilità intrinseca del mercato delle criptovalute e dell'ecosistema digitale",
            "Scrutinio normativo globale sugli emittenti e sui binari di trasferimento delle stablecoin",
            "Concorrenza di reti blockchain Layer-1 e Layer-2 rivali (Solana, Base, Arbitrum)"
        ],
        "related_tickers": ["$BTC", "$ETH", "$SOL"], "primary_tags": ["$TRX"]
    },
}


def get_asset_metadata(ticker: str) -> dict:
    """
    Return the verified, authoritative metadata for a given ticker from the master catalog.
    Falls back to basic structure if ticker is not explicitly cataloged.
    """
    clean = ticker.replace("$", "").strip().upper()
    if clean in PORTFOLIO_ASSETS_METADATA:
        return PORTFOLIO_ASSETS_METADATA[clean]
    
    # Check config for basic fallback
    config = load_config()
    tickers = config.get("tickers", {})
    if clean in tickers:
        yahoo_sym, name = tickers[clean]
        return {
            "ticker": clean,
            "yahoo_ticker": yahoo_sym,
            "name": name,
            "emoji": config.get("emojis", {}).get(clean, "📊"),
            "asset_class": "Stock",
            "sector": "Azienda in Portafoglio",
            "geo": "Global",
            "tier": "Core Holding",
            "is_dividend_paying": False,
            "dividend_policy": "Informazioni non disponibili",
            "annual_yield_pct": 0.0,
            "frequency": "Nessuna",
            "domain": f"{clean.lower()}.com",
            "color": (0, 200, 255),
            "desc": f"{name} in Andrea Ravalli's diversified eToro portfolio.",
            "thesis": f"Posizione strategica selezionata per fondamentali solidi e disciplina di capitale.",
            "upside_catalysts": ["Crescita operativa fondamentale", "Espansione delle quote di mercato"],
            "downside_risks": ["Volatilità del settore di appartenenza", "Rischi macroeconomici generali"],
            "related_tickers": get_related_tickers(clean),
            "primary_tags": get_ticker_all_tags(clean),
        }

    return {
        "ticker": clean,
        "yahoo_ticker": clean,
        "name": clean,
        "emoji": "📊",
        "asset_class": "Asset",
        "sector": "Mercato",
        "geo": "Global",
        "tier": "Holding",
        "is_dividend_paying": False,
        "dividend_policy": "N/A",
        "annual_yield_pct": 0.0,
        "frequency": "N/A",
        "domain": f"{clean.lower()}.com",
        "color": (0, 200, 255),
        "desc": clean,
        "thesis": clean,
        "upside_catalysts": [],
        "downside_risks": [],
        "related_tickers": ["$S&P500"],
        "primary_tags": [f"${clean}"],
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


