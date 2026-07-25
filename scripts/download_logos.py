#!/usr/bin/env python3
"""
Download all stock logos for the portfolio and save them to assets/logos/.

Usage:
    python3 scripts/download_logos.py              # all tickers in portfolio_config.json
    python3 scripts/download_logos.py NVDA LLY    # specific tickers only
    python3 scripts/download_logos.py --missing    # only tickers without a cached logo

The script uses cdn.tickerlogos.com (no API key, no auth).
Rate limit: 30 requests / 10 seconds — handled automatically with small delays.

Output directory: assets/logos/{ticker}.png
  (committed to the repo so CI never needs to fetch at runtime)
"""

import io
import os
import sys
import json
import time

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: Pillow not installed — logos will be saved as raw PNG bytes without resize.")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    print("ERROR: 'requests' library not installed. Run: pip install requests")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_DIR     = os.path.join(ROOT, "assets", "logos")
CONFIG_FILE  = os.path.join(ROOT, "portfolio_config.json")

# Desired logo size (px). Square, transparent background where possible.
LOGO_SIZE = 120

# Hardcoded domain map: ticker → primary company domain
# Priority over CDN search (faster + more accurate for ambiguous tickers)
DOMAIN_MAP = {
    # ── USA stocks ──────────────────────────────────────────────────────────
    "NVDA":       "nvidia.com",
    "MSFT":       "microsoft.com",
    "AMZN":       "amazon.com",
    "GOOG":       "google.com",
    "LLY":        "lilly.com",
    "PLTR":       "palantir.com",
    "AVGO":       "broadcom.com",
    "TSM":        "tsmc.com",
    "ABBV":       "abbvie.com",
    "ABT.US":     "abbott.com",
    "HUM":        "humana.com",
    "MELI":       "mercadolibre.com",
    "CCJ":        "cameco.com",
    "NET":        "cloudflare.com",
    "PYPL":       "paypal.com",
    # ── European stocks ──────────────────────────────────────────────────────
    "AZN.L":      "astrazeneca.com",
    "NOVO-B.CO":  "novonordisk.com",
    "ENEL.MI":    "enel.com",
    "ENI.MI":     "eni.com",
    "PRY.MI":     "prysmiangroup.com",
    "RACE":       "ferrari.com",
    "VOW3.DE":    "volkswagenag.com",
    "GLEN.L":     "glencore.com",
    "TRIG.L":     "trig-ltd.com",
    "MAU.PA":     "maureletprom.fr",
    "ULVR.L":     "unilever.com",
    "MNODL.L":    "mondigroup.com",
    "NVTKL.L":    "novatek.ru",
    # ── Asia ────────────────────────────────────────────────────────────────
    "1211.HK":    "byd.com",
    "1919.HK":    "coscoshipping.com",
    "2318.HK":    "pingan.com",
    # ── ETFs (providers) ─────────────────────────────────────────────────────
    "SX7PEX.DE":  "ishares.com",
    "IEUR":       "ishares.com",
    "IQQL.DE":    "ishares.com",
    "IEMG":       "ishares.com",
    "IB01.L":     "ishares.com",
    "WDEF.L":     "wisdomtree.com",
    "INDO.PA":    "amundi.com",
    "PPFB.DE":    "ishares.com",
    "XEON.DE":    "dws.com",
    "VOF.L":      "vinacapital.com",
    # ── Other ────────────────────────────────────────────────────────────────
    "ETOR":       "etoro.com",
    "TRX":        "tron.network",
}

# CDN base URL
CDN_BASE    = "https://cdn.tickerlogos.com"
SEARCH_URL  = f"{CDN_BASE}/api/logo-search/"
RATE_SLEEP  = 0.4   # seconds between requests to stay under burst limit


def _logo_path(ticker: str) -> str:
    safe = ticker.replace("/", "_").replace("\\", "_")
    return os.path.join(LOGO_DIR, f"{safe}.png")


def _logo_exists(ticker: str) -> bool:
    return os.path.exists(_logo_path(ticker)) and os.path.getsize(_logo_path(ticker)) > 500


def _fetch_domain(ticker: str) -> "str | None":
    """Return the best domain for a ticker (hardcoded first, then CDN search)."""
    domain = DOMAIN_MAP.get(ticker)
    if domain:
        return domain

    try:
        r = requests.get(SEARCH_URL, params={"q": ticker}, timeout=6)
        if r.ok:
            results = r.json().get("results", [])
            if results:
                d = results[0].get("website", "")
                if d:
                    print(f"  CDN search: {ticker} → {d}")
                    return d
    except Exception as e:
        print(f"  CDN search error for {ticker}: {e}")

    return None


def _save_logo(ticker: str, raw_bytes: bytes) -> bool:
    """Save raw PNG bytes to assets/logos/, optionally resizing with PIL."""
    path = _logo_path(ticker)
    if PIL_AVAILABLE:
        try:
            img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
            img = img.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
            img.save(path, "PNG", optimize=True)
            return True
        except Exception as e:
            print(f"  PIL resize failed for {ticker}: {e} — saving raw")

    # Fallback: save raw bytes as-is
    with open(path, "wb") as f:
        f.write(raw_bytes)
    return True


def download_logo(ticker: str, force: bool = False) -> bool:
    """
    Download and save the logo for a single ticker.
    Uses multi-provider fallback strategy (tickerlogos -> icon.horse -> parqet -> google favicons).
    Returns True if the logo was successfully saved (or already existed).
    """
    if not force and _logo_exists(ticker):
        print(f"  ✓ {ticker:<20} already cached, skipping.")
        return True

    domain = _fetch_domain(ticker)

    # Build candidate URLs
    candidate_urls = []
    if domain:
        candidate_urls.append(f"{CDN_BASE}/{domain}")
        candidate_urls.append(f"https://icon.horse/icon/{domain}")
    candidate_urls.append(f"https://assets.parqet.com/logos/symbol/{ticker}")
    if domain:
        candidate_urls.append(f"https://www.google.com/s2/favicons?domain={domain}&sz=128")

    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in candidate_urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.ok and len(r.content) > 500:
                # Check if image can be parsed by PIL if available
                if PIL_AVAILABLE:
                    try:
                        img = Image.open(io.BytesIO(r.content))
                        if img.format in ['PNG', 'JPEG', 'WEBP', 'ICO']:
                            _save_logo(ticker, r.content)
                            print(f"  ✓ {ticker:<20} saved ({len(r.content)//1024}KB) from {url}")
                            return True
                    except Exception:
                        continue
                else:
                    _save_logo(ticker, r.content)
                    print(f"  ✓ {ticker:<20} saved ({len(r.content)//1024}KB) from {url}")
                    return True
        except Exception:
            continue

    print(f"  ✗ {ticker:<20} failed across all logo providers")
    return False


def load_all_tickers() -> list[str]:
    """Load all eToro ticker keys from portfolio_config.json."""
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: {CONFIG_FILE} not found. Run from the repo root.")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    tickers = list(cfg.get("tickers", {}).keys())
    return tickers


def main():
    os.makedirs(LOGO_DIR, exist_ok=True)

    args = sys.argv[1:]
    force    = False
    missing  = False
    explicit = []

    for a in args:
        if a == "--force":
            force = True
        elif a == "--missing":
            missing = True
        else:
            explicit.append(a)

    if explicit:
        tickers = explicit
        print(f"Downloading logos for {len(tickers)} explicitly requested ticker(s).")
    else:
        tickers = load_all_tickers()
        print(f"Loaded {len(tickers)} tickers from portfolio_config.json.")
        if missing:
            tickers = [t for t in tickers if not _logo_exists(t)]
            print(f"  → {len(tickers)} missing logos to download.")

    ok_count  = 0
    fail_list = []

    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] {ticker}")
        success = download_logo(ticker, force=force)
        if success:
            ok_count += 1
        else:
            fail_list.append(ticker)
        if i < len(tickers) - 1:
            time.sleep(RATE_SLEEP)   # respect CDN burst limit

    print()
    print(f"Done: {ok_count}/{len(tickers)} logos saved in {LOGO_DIR}")

    if fail_list:
        print(f"Missing logos ({len(fail_list)}): {', '.join(fail_list)}")
        print("→ Add entries to DOMAIN_MAP in this script to fix them.")
    
    print()
    print("To commit:")
    print("  git add assets/logos/ && git commit -m 'chore: update stock logos'")


if __name__ == "__main__":
    main()
