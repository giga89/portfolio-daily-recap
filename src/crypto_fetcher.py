#!/usr/bin/env python3
"""
Crypto Market Data & Sentiment Fetcher
======================================
Fetches live, verified cryptocurrency market data and sentiment metrics
without requiring paid API keys:
  • Spot prices, 24h percentage change, and 24h volume (Binance / CoinGecko / yfinance)
  • Crypto Fear & Greed Index (Alternative.me)
  • Standardized formatting for eToro-supported cryptocurrencies
"""

import time
import requests
from typing import Dict, Any, List, Optional

# Supported eToro Cryptos Metadata
CRYPTO_METADATA = {
    "BTC": {
        "name": "Bitcoin",
        "emoji": "🪙",
        "binance_symbol": "BTCUSDT",
        "coingecko_id": "bitcoin",
        "yahoo_symbol": "BTC-USD",
        "color": (247, 147, 26),
    },
    "ETH": {
        "name": "Ethereum",
        "emoji": "🔷",
        "binance_symbol": "ETHUSDT",
        "coingecko_id": "ethereum",
        "yahoo_symbol": "ETH-USD",
        "color": (98, 126, 234),
    },
    "SOL": {
        "name": "Solana",
        "emoji": "⚡",
        "binance_symbol": "SOLUSDT",
        "coingecko_id": "solana",
        "yahoo_symbol": "SOL-USD",
        "color": (20, 241, 149),
    },
    "TRX": {
        "name": "TRON",
        "emoji": "💎",
        "binance_symbol": "TRXUSDT",
        "coingecko_id": "tron",
        "yahoo_symbol": "TRX-USD",
        "color": (235, 0, 41),
    },
    "XRP": {
        "name": "Ripple",
        "emoji": "🌊",
        "binance_symbol": "XRPUSDT",
        "coingecko_id": "ripple",
        "yahoo_symbol": "XRP-USD",
        "color": (35, 41, 47),
    },
    "ADA": {
        "name": "Cardano",
        "emoji": "🔵",
        "binance_symbol": "ADAUSDT",
        "coingecko_id": "cardano",
        "yahoo_symbol": "ADA-USD",
        "color": (0, 51, 173),
    },
    "LINK": {
        "name": "Chainlink",
        "emoji": "🔗",
        "binance_symbol": "LINKUSDT",
        "coingecko_id": "chainlink",
        "yahoo_symbol": "LINK-USD",
        "color": (55, 91, 210),
    },
    "AVAX": {
        "name": "Avalanche",
        "emoji": "🔺",
        "binance_symbol": "AVAXUSDT",
        "coingecko_id": "avalanche-2",
        "yahoo_symbol": "AVAX-USD",
        "color": (232, 65, 66),
    },
    "DOGE": {
        "name": "Dogecoin",
        "emoji": "🐕",
        "binance_symbol": "DOGEUSDT",
        "coingecko_id": "dogecoin",
        "yahoo_symbol": "DOGE-USD",
        "color": (194, 166, 51),
    },
}

DEFAULT_CRYPTO_LIST = ["BTC", "ETH", "SOL", "TRX"]

HEADERS = {
    "User-Agent": "PortfolioRecapBot/1.0 (Mozilla/5.0; CryptoAnalytics)"
}


def fetch_fear_and_greed_index() -> Dict[str, Any]:
    """
    Fetch the Crypto Fear & Greed Index from Alternative.me API.
    Returns:
        dict: {"score": int, "classification": str, "emoji": str, "classification_it": str}
    """
    url = "https://api.alternative.me/fng/?limit=1"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", [])
            if items:
                score = int(items[0].get("value", 50))
                cls_raw = items[0].get("value_classification", "Neutral")
                
                # Sentiment Italian translation & emoji
                if score >= 75:
                    cls_it = "Avidità Estrema (Extreme Greed)"
                    emoji = "🔥"
                elif score >= 55:
                    cls_it = "Avidità (Greed)"
                    emoji = "🟢"
                elif score >= 45:
                    cls_it = "Neutrale (Neutral)"
                    emoji = "⚖️"
                elif score >= 25:
                    cls_it = "Paura (Fear)"
                    emoji = "🟠"
                else:
                    cls_it = "Paura Estrema (Extreme Fear)"
                    emoji = "🩸"

                return {
                    "score": score,
                    "classification": cls_raw,
                    "classification_it": cls_it,
                    "emoji": emoji,
                }
    except Exception as e:
        print(f"⚠️ Fear & Greed fetch failed: {e}")

    return {
        "score": 50,
        "classification": "Neutral",
        "classification_it": "Neutrale (Neutral)",
        "emoji": "⚖️",
    }


def format_volume(volume_usd: float) -> str:
    """Format volume in Billions ($B) or Millions ($M)."""
    if volume_usd >= 1_000_000_000:
        return f"${volume_usd / 1_000_000_000:.2f}B"
    elif volume_usd >= 1_000_000:
        return f"${volume_usd / 1_000_000:.2f}M"
    else:
        return f"${volume_usd:,.0f}"


def format_price(price: float) -> str:
    """Format price nicely based on magnitude."""
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.2f}"
    elif price >= 0.01:
        return f"${price:.4f}"
    else:
        return f"${price:.6f}"


def fetch_crypto_from_binance(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetch 24h ticker data directly from Binance public ticker API (high reliability, zero auth).
    """
    results = {}
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            all_tickers = {item["symbol"]: item for item in resp.json()}
            for sym in symbols:
                clean_sym = sym.upper().replace("$", "").replace("-USD", "")
                meta = CRYPTO_METADATA.get(clean_sym, {})
                pair = meta.get("binance_symbol", f"{clean_sym}USDT")
                if pair in all_tickers:
                    t_data = all_tickers[pair]
                    price = float(t_data.get("lastPrice", 0.0))
                    change_24h = float(t_data.get("priceChangePercent", 0.0))
                    vol_usd = float(t_data.get("quoteVolume", 0.0))
                    high_24h = float(t_data.get("highPrice", 0.0))
                    low_24h = float(t_data.get("lowPrice", 0.0))

                    results[clean_sym] = {
                        "symbol": clean_sym,
                        "name": meta.get("name", clean_sym),
                        "emoji": meta.get("emoji", "🪙"),
                        "price_usd": price,
                        "price_formatted": format_price(price),
                        "change_24h": round(change_24h, 2),
                        "volume_24h_usd": vol_usd,
                        "volume_formatted": format_volume(vol_usd),
                        "high_24h": high_24h,
                        "high_formatted": format_price(high_24h),
                        "low_24h": low_24h,
                        "low_formatted": format_price(low_24h),
                        "cashtag": f"${clean_sym}",
                        "color": meta.get("color", (0, 200, 255)),
                    }
    except Exception as e:
        print(f"⚠️ Binance API fetch failed: {e}")
    return results


def fetch_crypto_from_yfinance(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fallback: fetch crypto data using yfinance.
    """
    results = {}
    try:
        import yfinance as yf
        for sym in symbols:
            clean_sym = sym.upper().replace("$", "").replace("-USD", "")
            meta = CRYPTO_METADATA.get(clean_sym, {})
            yf_ticker = meta.get("yahoo_symbol", f"{clean_sym}-USD")
            t = yf.Ticker(yf_ticker)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                cur_price = float(hist["Close"].iloc[-1])
                prev_price = float(hist["Close"].iloc[-2])
                change_24h = ((cur_price - prev_price) / prev_price) * 100
                vol_usd = float(hist["Volume"].iloc[-1] * cur_price)
                high_24h = float(hist["High"].iloc[-1])
                low_24h = float(hist["Low"].iloc[-1])

                results[clean_sym] = {
                    "symbol": clean_sym,
                    "name": meta.get("name", clean_sym),
                    "emoji": meta.get("emoji", "🪙"),
                    "price_usd": cur_price,
                    "price_formatted": format_price(cur_price),
                    "change_24h": round(change_24h, 2),
                    "volume_24h_usd": vol_usd,
                    "volume_formatted": format_volume(vol_usd),
                    "high_24h": high_24h,
                    "high_formatted": format_price(high_24h),
                    "low_24h": low_24h,
                    "low_formatted": format_price(low_24h),
                    "cashtag": f"${clean_sym}",
                    "color": meta.get("color", (0, 200, 255)),
                }
    except Exception as e:
        print(f"⚠️ yfinance crypto fetch failed: {e}")
    return results


CORE_CRYPTOS = ["BTC", "ETH", "TRX"]
ROTATING_ALTCOINS = ["SOL", "XRP", "ADA", "LINK", "AVAX", "DOGE"]


def select_daily_crypto_symbols(target_count: int = 4) -> List[str]:
    """
    Select 4 cryptos for the daily post:
      1. $BTC — Market benchmark
      2. $ETH — Smart contract leader
      3. $TRX — Held in Andrea's eToro portfolio
      4. Dynamic 4th altcoin — rotating or top mover among $SOL, $XRP, $ADA, $LINK, $AVAX, $DOGE
    """
    # Deterministic daily rotation seed
    day_of_year = time.gmtime().tm_yday
    rotating_idx = day_of_year % len(ROTATING_ALTCOINS)
    rotated_alt = ROTATING_ALTCOINS[rotating_idx]

    # Try to find if any altcoin has an extraordinary move (>5%), otherwise use rotated altcoin
    try:
        alt_data = fetch_crypto_from_binance(ROTATING_ALTCOINS)
        if alt_data:
            # Sort by absolute 24h price change to find today's big mover
            sorted_movers = sorted(alt_data.values(), key=lambda x: abs(x.get("change_24h", 0.0)), reverse=True)
            top_mover = sorted_movers[0]["symbol"]
            # If top mover has >3% change, feature it, otherwise use deterministic rotation
            if abs(sorted_movers[0].get("change_24h", 0.0)) >= 3.0:
                selected_4th = top_mover
            else:
                selected_4th = rotated_alt
        else:
            selected_4th = rotated_alt
    except Exception:
        selected_4th = rotated_alt

    return ["BTC", "ETH", "TRX", selected_4th]


def fetch_crypto_daily_data(symbols: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Orchestrator: Fetches sentiment and 4 selected crypto assets with multi-source fallback.
    """
    if not symbols:
        symbols = select_daily_crypto_symbols()

    sentiment = fetch_fear_and_greed_index()
    
    # Try primary: Binance
    cryptos = fetch_crypto_from_binance(symbols)
    
    # Fallback missing symbols via yfinance
    missing = [s for s in symbols if s not in cryptos]
    if missing:
        print(f"ℹ️ Fetching missing crypto data from yfinance: {missing}")
        yf_data = fetch_crypto_from_yfinance(missing)
        cryptos.update(yf_data)

    print(f"✓ Fetched live data for {len(cryptos)} crypto assets ({', '.join(cryptos.keys())}). Fear & Greed: {sentiment['score']}/100 ({sentiment['classification']})")

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "sentiment": sentiment,
        "cryptos": cryptos,
        "symbols": list(cryptos.keys()),
    }


if __name__ == "__main__":
    data = fetch_crypto_daily_data()
    print("\n📊 CRYPTO DATA FETCH TEST:")
    print(f"Sentiment: {data['sentiment']['score']} - {data['sentiment']['classification_it']}")
    for k, v in data["cryptos"].items():
        print(f"  • {v['emoji']} {v['name']} ({v['cashtag']}): {v['price_formatted']} ({v['change_24h']:+.2f}%) | Vol: {v['volume_formatted']}")
