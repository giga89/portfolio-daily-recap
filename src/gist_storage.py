#!/usr/bin/env python3
"""
GitHub Gist Storage Module
Handles reading and writing data to GitHub Gist for persistent storage outside the repo.
"""

import os
import json
import requests
from datetime import datetime

# Gist configuration
GIST_ID = os.environ.get('GIST_ID', '')  # Will be set after first run
GIST_FILENAME = 'portfolio_recap_data.json'

# Legacy data to migrate if Gist is empty
LEGACY_HISTORY = [
  {
    "timestamp": "2025-12-31T15:12:13.884067",
    "content": "\ud83c\udf0d MARKET NEWS RECAP\n\nGlobal markets traded with a modest year-end pullback amid extremely thin holiday volumes, with US $S&P 500 and $Nasdaq 100 futures signaling a soft open, down 0.2% and 0.3% respectively. European bourses were similarly muted, as the Stoxx Europe 600 fell 0.1% and France's CAC 40 declined 0.4% in early trading. In Asia, the $Shanghai Composite managed a marginal gain of 0.1%, contrasting with a 0.9% drop in the Hang Seng index, as investors booked profits on the final trading day of the year.\n\n\ud83d\udcbc PORTFOLIO FOCUS\n\nThe AI and chip sector, which includes $NVDA, $AVGO, $TSM, $MSFT, and $SNPS, saw a major catalyst with news of $NVDA's potential $20 billion acquisition of Groq's AI inferencing technology, positioning it for the next growth phase in AI adoption. In the GLP-1 space, $NOVO-B.CO submitted a New Drug Application (NDA) to the FDA for its once-weekly CagriSema combination for weight management, intensifying competition with $LLY. Separately, a new FDA-approved m"
  },
  {
    "timestamp": "2025-12-31T22:17:45.867978",
    "content": "\ud83c\udf0d MARKET NEWS RECAP\n\nGlobal markets closed out the final trading day of the year on a soft note amid extremely thin holiday volumes. US indices declined, with the $S&P 500 falling 0.33% and the $Nasdaq 100 down 0.34%, primarily driven by weakness in chip and data storage stocks. European stocks were also slightly lower, with the Euro Stoxx 50 easing 0.08%, while China's Shanghai Composite showed resilience, climbing 0.1% following stronger-than-expected December Manufacturing and Non-Manufacturing PMI data. The unexpected drop in US weekly jobless claims to a one-month low was a hawkish factor contributing to higher bond yields and pressure on equities.\n\n\ud83d\udcbc PORTFOLIO FOCUS\n\nThe AI and Semiconductor cohort, including $NVDA, $TSM, $AVGO, $MSFT, $SNPS, $AMZN, and $GOOG, faced selling pressure, as chip stocks led the broader $Nasdaq decline. The Healthcare sector, featuring $LLY and $NOVO-B.CO, continued to be driven by the prevailing narrative of $LLY's dominance in the GLP-1 weight-loss d"
  },
  {
    "timestamp": "2026-01-01T10:15:19.384074",
    "content": "\ud83c\udf0d MARKET NEWS RECAP\n\nGlobal financial markets were universally closed today for the New Year's Day holiday, resulting in no trading activity for major indices including the $S&P 500, $Nasdaq, and the $Euro Stoxx. The focus has entirely shifted to policy announcements and economic forecasts for the year ahead, with all eyes now on the first trading session of 2026 tomorrow. Asian markets, including the Shanghai Composite, also observed the holiday, leaving volume at negligible levels worldwide. The lack of trading volume has led analysts to issue numerous sector outlooks, setting the stage for tomorrow\u2019s open.\n\n\ud83d\udcbc PORTFOLIO FOCUS\n\nWith markets closed, attention is on the 2026 outlook for key sectors. The Healthcare cohort, including $AZN.L, $ABT, $ABBV, $LLY, and $NOVO-B.CO, is poised for continued growth based on new product pipelines and a strong M&A environment, with particular momentum expected in obesity and immunology treatments. AI and Semiconductor names like $NVDA, $TSM, $MSFT, "
  },
  {
    "timestamp": "2026-01-01T15:12:11.179788",
    "content": "\ud83c\udf0d MARKET NEWS RECAP\n\nGlobal financial markets, including the $S&P 500, $Nasdaq, and $Euro Stoxx, were universally closed today for the New Year's Day holiday, resulting in extremely limited trading activity. A key European policy event saw Bulgaria officially adopt the euro, becoming the 21st country to join the single currency. In trade news, China announced it will impose additional 55% tariffs on beef imports from key global suppliers, including the US and Australia, effective today.\n\n\ud83d\udcbc PORTFOLIO FOCUS\n\nWith no major company-specific news during the holiday, the focus remains on macro drivers for the portfolio's core holdings. The AI/Cloud infrastructure sector, including $NVDA, $AVGO, $MSFT, and $GOOG, enters the new year with strong momentum following $GOOG's best year since 2009 due to strengthening AI sentiment. Healthcare and Pharma holdings ($LLY, $NOVO-B.CO, $ABBV) are centered on upcoming Q4 earnings and continued legislative uncertainty regarding drug pricing. China's new t"
  },
  {
    "timestamp": "2026-01-01T22:17:10.839813",
    "content": "\ud83c\udf0d MARKET NEWS RECAP\n\nGlobal financial markets were largely closed for the New Year's Day holiday, severely limiting major index trading in the US and Europe. The $S&P 500 and $Euro Stoxx saw no activity, with attention shifting to overnight commodity moves. The $Shanghai Composite, however, provided a final data point, managing a slight gain, closing up 0.1% at 3,968.84. Gold prices remain a macro focus after recording an astonishing annual gain of approximately 64% in 2025, while oil prices ended the year down nearly 20%.\n\n\ud83d\udcbc PORTFOLIO FOCUS\n\nThe AI/Semiconductor complex, including $NVDA and $TSM, is poised for a strong start to 2026 following reports that $NVDA is ramping up production for its H200 AI chips in a dramatic push to meet Chinese orders exceeding 2 million units for the year. Broader AI-driven demand for high-bandwidth memory chips is expected to accelerate a supply crunch, potentially driving consumer electronics prices up by 5% to 20% in 2026. In Healthcare, $ABT, $ABBV,"
  }
]

_data_cache = None

def _invalidate_cache():
    global _data_cache
    _data_cache = None

def _get_headers():
    """Get authorization headers for GitHub API"""
    token = os.environ.get('GIST_ACCESS_TOKEN') or os.environ.get('GITHUB_GIST_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        # Debug: print only if we really can't find anything
        # print("Debug: No token found in env vars")
        return None
    
    # Simple check to warn if using potential default token without gist scope
    if not os.environ.get('GIST_ACCESS_TOKEN') and not os.environ.get('GITHUB_GIST_TOKEN'):
        print("ℹ️  Using default GITHUB_TOKEN (might lack gist permissions)")
        
    return {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

def verify_token_permissions(token):
    """Verify if the token has 'gist' scope"""
    try:
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        response = requests.get('https://api.github.com/user', headers=headers, timeout=5)
        if 'X-OAuth-Scopes' in response.headers:
            scopes = response.headers['X-OAuth-Scopes']
            if 'gist' not in scopes.split(', '):
                print(f"⚠️  WARNING: Token scopes are: {scopes}. Missing 'gist' scope!")
                return False
        return True
    except Exception:
        return True # Assume ok if check fails to avoid blocking

def _get_default_data():
    """Return default data structure, migrating local history if available"""
    default_data = {
        'recap_history': [],
        'used_tags': [],
        'last_updated': None
    }
    
    # Use embedded legacy history for migration
    print(f"📦 checking for migration: Using embedded legacy history ({len(LEGACY_HISTORY)} items).")
    default_data['recap_history'] = LEGACY_HISTORY
            
    return default_data

def load_data():
    """
    Load data from GitHub Gist. Results are cached in-memory for the lifetime
    of the process so multiple callers within a single run share one API call.

    Returns:
        dict: Data containing recap_history, used_tags, etc.
    """
    global _data_cache
    if _data_cache is not None:
        return _data_cache

    headers = _get_headers()
    gist_id = os.environ.get('GIST_ID', '')
    
    if not headers:
        print("⚠️ No GitHub token found, using empty data")
        _data_cache = _get_default_data()
        return _data_cache

    if not gist_id:
        print("ℹ️ No GIST_ID set, will create new gist on save")
        _data_cache = _get_default_data()
        return _data_cache
    
    try:
        response = requests.get(
            f'https://api.github.com/gists/{gist_id}',
            headers=headers,
            timeout=10
        )
        
        migrated = False
        data = _get_default_data() # Start with defaults (including legacy history)

        if response.status_code == 200:
            gist_data = response.json()
            if GIST_FILENAME in gist_data.get('files', {}):
                content = gist_data['files'][GIST_FILENAME]['content']
                loaded_data = json.loads(content)
                print(f"✅ Loaded data from Gist (ID: {gist_id[:8]}...)")
                
                # Check if we need to merge legacy history (if Gist history is empty)
                if not loaded_data.get('recap_history') and LEGACY_HISTORY:
                    print("🔄 Gist history is empty. Merging legacy history...")
                    loaded_data['recap_history'] = LEGACY_HISTORY
                    migrated = True
                
                data = loaded_data
            else:
                print(f"⚠️ File {GIST_FILENAME} not found in gist, using defaults (will migrate)")
                migrated = True
        elif response.status_code == 404:
            print(f"⚠️ Gist not found (ID: {gist_id}), using defaults (will migrate)")
            migrated = True
        else:
            print(f"⚠️ Error loading gist: {response.status_code} - {response.text}")
            # Fallback to defaults (with legacy history)
            migrated = True
            
        # If we performed a migration (merge or fresh default), we should ideally save it.
        # But this function is a 'load', so we just return the data.
        # The next 'save_data' call (which happens after generating news) will persist it.
        # If the news generation fails, we might lose the migration for this run, but it will try again next time.
        _data_cache = data
        return _data_cache

    except Exception as e:
        print(f"⚠️ Error loading from Gist: {e}")
        return _get_default_data()

def save_data(data):
    """
    Save data to GitHub Gist and update the in-memory cache.

    Args:
        data: Dict containing recap_history, used_tags, etc.

    Returns:
        bool: True if save was successful
    """
    global _data_cache
    headers = _get_headers()
    gist_id = os.environ.get('GIST_ID', '')
    
    if not headers:
        print("⚠️ No GitHub token found, cannot save to Gist")
        return False
    
    data['last_updated'] = datetime.now().isoformat()
    _data_cache = data  # Keep cache in sync with what we're saving
    content = json.dumps(data, indent=2)
    
    gist_payload = {
        'description': 'Portfolio Daily Recap - Data Storage',
        'files': {
            GIST_FILENAME: {
                'content': content
            }
        }
    }
    
    try:
        if gist_id:
            # Update existing gist
            response = requests.patch(
                f'https://api.github.com/gists/{gist_id}',
                headers=headers,
                json=gist_payload,
                timeout=10
            )
        else:
            # Create new gist (private)
            gist_payload['public'] = False
            response = requests.post(
                'https://api.github.com/gists',
                headers=headers,
                json=gist_payload,
                timeout=10
            )
        
        if response.status_code in [200, 201]:
            result = response.json()
            new_gist_id = result.get('id', '')
            if not gist_id and new_gist_id:
                print(f"🆕 Created new Gist! Add this as secret GIST_ID: {new_gist_id}")
            else:
                print(f"✅ Data saved to Gist (ID: {new_gist_id[:8]}...)")
            return True

        elif response.status_code == 403:
            print(f"❌ Error saving to Gist: 403 - Forbidden.")
            print("   👉 Check that your GIST_ID is correct (if set).")
            print("   👉 If using GITHUB_TOKEN in Actions, it may lack 'gist' permissions.")
            return False
        elif response.status_code == 401:
            print(f"❌ Error saving to Gist: 401 - Unauthorized.")
            print("   👉 The token provided is invalid or expired.")
            print("   👉 If using GIST_ACCESS_TOKEN, check if you copied it correctly.")
            return False
        else:
            print(f"❌ Error saving to Gist: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error saving to Gist: {e}")
        return False

def load_recap_history():
    """Load only recap history for backwards compatibility"""
    data = load_data()
    return data.get('recap_history', [])

def save_to_history(recap_text):
    """Save recap to history"""
    data = load_data()
    history = data.get('recap_history', [])
    
    # Keep only the last 5 recaps
    history.append({
        'timestamp': datetime.now().isoformat(),
        'content': recap_text[:1000]
    })
    history = history[-5:]
    
    data['recap_history'] = history
    save_data(data)

def get_used_tags():
    """Get list of recently used tags"""
    data = load_data()
    return data.get('used_tags', [])

def save_used_tags(tags):
    """Save the list of used tags for rotation"""
    data = load_data()
    data['used_tags'] = tags
    save_data(data)

def get_used_stock_focus_tickers():
    """Get list of recently used stock focus tickers for rotation"""
    data = load_data()
    return data.get('used_stock_focus_tickers', [])

def save_used_stock_focus_ticker(ticker):
    """Save ticker to stock focus rotation history"""
    data = load_data()
    used = data.get('used_stock_focus_tickers', [])
    if ticker not in used:
        used.append(ticker)
    data['used_stock_focus_tickers'] = used[-25:]
    save_data(data)

def get_portfolio_config():
    """Get portfolio items (tickers) from Gist"""
    data = load_data()
    return data.get('portfolio_config', {}), data.get('portfolio_emojis', {})

def save_portfolio_config(tickers, emojis):
    """Save portfolio items (tickers) and emojis to Gist"""
    data = load_data()
    data['portfolio_config'] = tickers
    data['portfolio_emojis'] = emojis
    save_data(data)


# ---------------------------------------------------------------------------
# Performance history (replaces Google Sheets "Storico" sheet)
# Each record: {'date': 'YYYY-MM-DD', 'perf': float, 'ath': float}
# ---------------------------------------------------------------------------

def get_perf_history():
    """Return the full performance history list from Gist."""
    data = load_data()
    return data.get('perf_history', [])


def upsert_perf_record(date_str, perf, ath):
    """Insert or update the performance record for a given date."""
    data = load_data()
    records = data.get('perf_history', [])
    for i, rec in enumerate(records):
        if rec['date'] == date_str:
            records[i] = {'date': date_str, 'perf': perf, 'ath': ath}
            data['perf_history'] = records
            save_data(data)
            print(f"✓ Updated Gist perf record for {date_str}: perf={perf:.2f}%, ath={ath:.2f}%")
            return
    records.append({'date': date_str, 'perf': perf, 'ath': ath})
    data['perf_history'] = records
    save_data(data)
    print(f"✓ Appended Gist perf record for {date_str}: perf={perf:.2f}%, ath={ath:.2f}%")


def seed_perf_history(records):
    """Bulk-seed performance history into Gist only if it is currently empty."""
    data = load_data()
    if data.get('perf_history'):
        print(f"ℹ️ Gist perf_history already has {len(data['perf_history'])} records, skipping seed.")
        return
    data['perf_history'] = records
    save_data(data)
    print(f"✅ Seeded {len(records)} records into Gist perf_history.")


def has_session_run_today(session_name):
    """Return True if the given market session has already completed today (UTC date)."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    data = load_data()
    return f"{today}:{session_name}" in data.get('session_runs', {})


def mark_session_run(session_name):
    """Record that the given market session completed today (UTC date)."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    today = now.strftime('%Y-%m-%d')
    data = load_data()
    runs = data.get('session_runs', {})
    # Discard entries older than the current month to prevent unbounded growth
    month_start = now.strftime('%Y-%m-01')
    runs = {k: v for k, v in runs.items() if k[:10] >= month_start}
    runs[f"{today}:{session_name}"] = now.isoformat()
    data['session_runs'] = runs
    _invalidate_cache()
    save_data(data)


# ---------------------------------------------------------------------------
# eToro history (imported from Excel account statement)
# ---------------------------------------------------------------------------

def get_etoro_history() -> dict:
    """Return the stored eToro history dict (from Excel import)."""
    data = load_data()
    return data.get('etoro_history', {})


def save_etoro_history(history: dict) -> bool:
    """Save parsed eToro history to Gist."""
    data = load_data()
    data['etoro_history'] = history
    return save_data(data)


# ---------------------------------------------------------------------------
# Pie chart image rotation tracking
# Rotates through: allocation → sector → geo → pnl_history → allocation …
# ---------------------------------------------------------------------------

PIE_CHART_TYPES = ['allocation', 'sector', 'geo', 'pnl_history']


def get_next_pie_chart_type() -> str:
    """
    Return the next pie chart type to use (round-robin).
    Advances the internal counter and saves it back to Gist.
    """
    data = load_data()
    idx = data.get('pie_chart_index', 0)
    chart_type = PIE_CHART_TYPES[idx % len(PIE_CHART_TYPES)]
    data['pie_chart_index'] = (idx + 1) % len(PIE_CHART_TYPES)
    save_data(data)
    return chart_type


def get_current_pie_chart_type() -> str:
    """Return the current pie chart type without advancing the counter."""
    data = load_data()
    idx = data.get('pie_chart_index', 0)
    return PIE_CHART_TYPES[idx % len(PIE_CHART_TYPES)]


# ---------------------------------------------------------------------------
# Copy Trading card image rotation tracking
# Rotates through: dashboard → profit → steps → dashboard …
# ---------------------------------------------------------------------------

COPY_CARD_STYLES = ['dashboard', 'profit', 'steps']


def get_next_copy_card_style() -> str:
    """
    Return the next copy trading card style to use (round-robin).
    Advances the internal counter and saves it back to Gist.
    """
    data = load_data()
    idx = data.get('copy_card_index', 0)
    style = COPY_CARD_STYLES[idx % len(COPY_CARD_STYLES)]
    data['copy_card_index'] = (idx + 1) % len(COPY_CARD_STYLES)
    save_data(data)
    return style


def get_current_copy_card_style() -> str:
    """Return the current copy trading card style without advancing the counter."""
    data = load_data()
    idx = data.get('copy_card_index', 0)
    return COPY_CARD_STYLES[idx % len(COPY_CARD_STYLES)]


# ---------------------------------------------------------------------------
# eToro Post & Delayed Engagement Tracking
# ---------------------------------------------------------------------------

def save_last_etoro_post(
    post_id: str,
    session_name: str,
    tickers: list = None,
    market_data_summary: dict = None,
) -> bool:
    """
    Save the most recently published eToro post ID and its metadata for delayed follow-up.
    """
    from datetime import datetime, timezone
    data = load_data()
    data['last_etoro_post'] = {
        'post_id': post_id,
        'session_name': session_name,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'tickers': tickers or [],
        'market_data_summary': market_data_summary or {},
        'followup_done': False,
        'followup_at': None,
    }
    _invalidate_cache()
    return save_data(data)


def get_last_etoro_post() -> dict:
    """Return metadata of the last published eToro post."""
    data = load_data()
    return data.get('last_etoro_post', {})


def mark_last_etoro_post_followup_done(post_id: str = None) -> bool:
    """Mark that the delayed engagement (+1h follow-up) has been completed."""
    from datetime import datetime, timezone
    data = load_data()
    last_post = data.get('last_etoro_post', {})
    if last_post:
        if post_id and last_post.get('post_id') != post_id:
            pass
        last_post['followup_done'] = True
        last_post['followup_at'] = datetime.now(timezone.utc).isoformat()
        data['last_etoro_post'] = last_post
        _invalidate_cache()
        return save_data(data)
    return False


# ---------------------------------------------------------------------------
# Stock Focus Post IDs & Catalyst News Tracking
# ---------------------------------------------------------------------------

def save_stock_focus_post_id(
    ticker: str,
    post_id: str,
    title: str = None,
    company_name: str = None,
) -> bool:
    """
    Save or update the latest eToro post ID for a specific stock focus deep dive.
    This enables targeted follow-up comments when breaking news/catalysts occur.
    """
    from datetime import datetime, timezone
    ticker = ticker.replace('$', '').upper().strip()
    data = load_data()
    posts = data.get('stock_focus_posts', {})
    posts[ticker] = {
        'post_id': str(post_id),
        'title': title or f"Stock Focus: ${ticker}",
        'company_name': company_name or ticker,
        'published_at': datetime.now(timezone.utc).isoformat(),
    }
    data['stock_focus_posts'] = posts
    _invalidate_cache()
    return save_data(data)


def get_stock_focus_post_id(ticker: str) -> dict:
    """Return the stored post metadata for a specific ticker, or empty dict."""
    ticker = ticker.replace('$', '').upper().strip()
    data = load_data()
    return data.get('stock_focus_posts', {}).get(ticker, {})


def get_all_stock_focus_posts() -> dict:
    """Return dictionary of all tracked stock focus posts {ticker: post_data}."""
    data = load_data()
    return data.get('stock_focus_posts', {})


def is_news_commented(news_hash: str) -> bool:
    """Check if a news item (identified by its unique hash) was already commented on."""
    data = load_data()
    commented = data.get('commented_news_hashes', {})
    return str(news_hash) in commented


def mark_news_commented(
    news_hash: str,
    ticker: str,
    post_id: str,
    headline: str = None,
) -> bool:
    """Record that a news item was commented under a stock focus post."""
    from datetime import datetime, timezone
    ticker = ticker.replace('$', '').upper().strip()
    data = load_data()
    commented = data.get('commented_news_hashes', {})
    # Keep last 200 commented news items to prevent unlimited growth
    if len(commented) > 200:
        commented = dict(list(commented.items())[-150:])
    commented[str(news_hash)] = {
        'ticker': ticker,
        'post_id': str(post_id),
        'headline': headline or '',
        'commented_at': datetime.now(timezone.utc).isoformat(),
    }
    data['commented_news_hashes'] = commented
    _invalidate_cache()
    return save_data(data)


