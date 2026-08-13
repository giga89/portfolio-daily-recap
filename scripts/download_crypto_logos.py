#!/usr/bin/env python3
"""
Download cryptocurrency logo assets for all eToro-supported crypto assets
and commit them into assets/logos/.
"""

import os
import io
import time
import requests
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_DIR = os.path.join(ROOT, "assets", "logos")

# Comprehensive list of eToro tradable cryptos
CRYPTO_SYMBOLS = [
    "BTC", "ETH", "TRX", "SOL", "XRP", "ADA", "LINK", "AVAX", "DOGE", "BNB",
    "DOT", "MATIC", "POL", "LTC", "SHIB", "NEAR", "ATOM", "UNI", "SUI", "APT",
    "TON", "ICP", "BCH", "XLM", "ALGO", "FTM", "AAVE", "MKR", "RENDER", "GRT"
]

# High quality CDN URLs for crypto icons
CDN_TEMPLATES = [
    "https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/{sym}.png",
    "https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@1a63539be033d80abb11483dda8be0e77e1c4793/128/color/{sym}.png",
    "https://raw.githubusercontent.com/crypti/cryptocurrencies/master/images/{sym}.png",
    "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/So11111111111111111111111111111111111111112/logo.png" if "{sym}" == "sol" else "",
]

# Specific high-res fallback URLs for newer or renamed tokens
SPECIAL_URLS = {
    "sol": "https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/sol.png",
    "avax": "https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/avax.png",
    "ton": "https://assets.coingecko.com/coins/images/17980/large/ton_symbol.png",
    "sui": "https://assets.coingecko.com/coins/images/26375/large/sui-ocean-square.png",
    "apt": "https://assets.coingecko.com/coins/images/26455/large/aptos_round.png",
    "pol": "https://assets.coingecko.com/coins/images/4713/large/polygon.png",
    "render": "https://assets.coingecko.com/coins/images/11636/large/render.png",
    "shib": "https://assets.coingecko.com/coins/images/11939/large/shiba.png",
    "near": "https://assets.coingecko.com/coins/images/10365/large/near.png",
    "ftm": "https://assets.coingecko.com/coins/images/4001/large/Fantom_round.png",
    "grt": "https://assets.coingecko.com/coins/images/13397/large/Graph_Token.png",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def download_crypto_logo(symbol: str) -> bool:
    clean = symbol.upper()
    sym_lower = clean.lower()
    dest_path = os.path.join(LOGO_DIR, f"{clean}.png")

    # If exists and is a valid image > 500 bytes, skip unless forced
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 500:
        try:
            with Image.open(dest_path) as im:
                im.verify()
            print(f"  ✓ {clean}.png already exists ({os.path.getsize(dest_path)} bytes)")
            return True
        except Exception:
            pass

    # Collect candidate URLs
    candidate_urls = []
    if sym_lower in SPECIAL_URLS:
        candidate_urls.append(SPECIAL_URLS[sym_lower])

    for tmpl in CDN_TEMPLATES:
        if tmpl:
            candidate_urls.append(tmpl.format(sym=sym_lower))

    # Also try CoinGecko search fallback
    candidate_urls.append(f"https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/{sym_lower}.png")

    for url in candidate_urls:
        if not url:
            continue
        try:
            resp = requests.get(url, headers=HEADERS, timeout=6)
            if resp.status_code == 200 and len(resp.content) > 300:
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                # Resize to standard 128x128
                img = img.resize((128, 128), Image.LANCZOS)
                img.save(dest_path, "PNG", optimize=True)
                print(f"  📥 Downloaded {clean}.png ({len(resp.content)} bytes) from {url[:60]}...")
                return True
        except Exception:
            continue

    print(f"  ⚠️ Could not download logo for {clean}")
    return False


def main():
    os.makedirs(LOGO_DIR, exist_ok=True)
    print("=" * 60)
    print(f"🚀 DOWNLOADING CRYPTO LOGO ASSETS ({len(CRYPTO_SYMBOLS)} symbols)...")
    print("=" * 60)

    success_count = 0
    for sym in CRYPTO_SYMBOLS:
        if download_crypto_logo(sym):
            success_count += 1
        time.sleep(0.1)

    print("=" * 60)
    print(f"🎉 COMPLETED: {success_count}/{len(CRYPTO_SYMBOLS)} crypto logos ready in assets/logos/")
    print("=" * 60)


if __name__ == "__main__":
    main()
