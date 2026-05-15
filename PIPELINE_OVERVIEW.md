# Pipeline Overview — Portfolio Daily Recap

Quick reference for when you lose the thread.
Last reviewed: May 2026.

---

## What runs and when

| Trigger (GitHub Actions cron) | Session name | What it does |
|---|---|---|
| Mon–Fri 06:45 UTC (summer) / 07:45 UTC (winter) | `European market open` | Recap + Telegram |
| Mon–Fri 13:15 UTC (summer) / 14:15 UTC (winter) | `U.S. market open` | Recap + Telegram |
| Mon–Fri 19:45 UTC (summer) / 20:45 UTC (winter) | `U.S. market close` | Recap + Telegram + Twitter + Bluesky |
| Saturday 09:00 UTC | `Weekly recap (Sat)` | Weekly recap + Telegram + LinkedIn |
| Sunday 21:00 UTC | `Weekly recap (Sun)` | Weekly recap + Telegram + LinkedIn |
| Last day of month 20:00 UTC | `Monthly recap` | Monthly recap + Telegram |
| Manual dispatch only | `Monday decision post` | AI decision + empathy posts → Telegram only |

**Important:** EU open and US open/close each have two crons (summer/winter). The workflow sleeps ~20 min
after firing to hit the exact target time. Deduplication via Gist prevents the two crons from sending twice.

---

## Data flow (one normal session)

```
[GitHub Actions cron fires]
        ↓
[Detect session name from cron or force_session input]
        ↓
[Dedup check via Gist — skip if already ran this session today]
        ↓
[data_collector.py — main entry point]
    1. Fetch stock prices → yfinance
    2. Fetch portfolio weights → BullAware (Selenium scrape)
    3. Weighted daily performance = sum(weight * daily_change)
    4. YTD performance → eToro public API (userstats + rankings)
    5. Cumulative 5-year return → eToro history seeded from Gist
    6. Benchmark comparison → yfinance (SP500, NDX, MSCI, EuroStoxx)
    7. Weekly / monthly perf → yfinance (if session requires it)
    8. Performance chart → chart_generator.py (matplotlib, portfolio vs benchmarks)
    9. Pie chart → pie_chart_generator.py (rotates: allocation / sector / geo / PnL)
   10. AI market news → ai_news_generator.py (Gemini API)
   11. Format recap → formatter.py → output/recap.txt
        ↓
[social_publisher.py — route to platforms based on session]
    → Telegram: every session (recap.txt + chart + pie chart as separate photo)
    → Twitter/X: US close only (2-tweet thread)
    → Bluesky:   US close only (2-post thread)
    → LinkedIn:  Weekly only (professional format)
    → Threads / Facebook / Instagram: US close (PENDING Meta restriction fix)
        ↓
[gist_storage.py — persist state]
    → Performance history snapshot
    → ATH (All-Time High) tracking
    → Tag rotation state (used_tags, avoids repeating same tickers)
    → Session dedup flags
    → Recap history (for dedup + context)
```

---

## Monday decision post (separate flow)

Triggered manually: `gh workflow run daily-recap.yml -f force_session="Monday decision post"`

```
[_publish_monday_posts() in social_publisher.py]
    1. Load eToro history from Gist → etoro_history.get_history_from_gist()
       ⚠ Empty if no Excel import done (see "eToro history import" below)
    2. Generate decision post → ai_news_generator.generate_decision_post()
       Input: recent closed positions (last 30 days) + stats summary
       Output: Italian text, max 1400 chars, "DECISIONE DELLA SETTIMANA"
    3. Generate empathy post → ai_news_generator.generate_empathy_post()
       Input: portfolio_perf (cumulative %) + weekly_perf + stats summary
       Output: Italian text, max 1200 chars, "UN PENSIERO PER VOI"
    4. Send both via Telegram (header + text + ETORO_FOOTER_LONG)
    5. Send current pie chart as photo
```

**Known bug:** `portfolio_weights` are available in `publish_all()` but NOT forwarded
to `_publish_monday_posts()` → Gemini has no "Current top holdings" context for the decision post.
See fix below.

---

## Source files at a glance

| File | Role |
|---|---|
| `data_collector.py` | Main entry point — orchestrates everything |
| `finance_fetcher.py` | yfinance prices, BullAware scrape, eToro public API |
| `formatter.py` | Builds the formatted recap text |
| `ai_news_generator.py` | Gemini API — market news, decision post, empathy post |
| `social_publisher.py` | Routes recap to all platforms based on session |
| `telegram_sender.py` | Telegram Bot API |
| `twitter_sender.py` | Twitter/X API (2-tweet thread) |
| `bluesky_sender.py` | Bluesky API (2-post thread) |
| `linkedin_sender.py` | LinkedIn API (weekly only) |
| `threads_sender.py` | Meta Threads (disabled — pending restriction fix) |
| `facebook_sender.py` | Facebook (disabled — pending restriction fix) |
| `instagram_sender.py` | Instagram Story + carousel (disabled — pending restriction fix) |
| `story_generator.py` | 1080×1920px Instagram Story image |
| `chart_generator.py` | Portfolio vs benchmarks performance chart |
| `pie_chart_generator.py` | Allocation / sector / geo / PnL pie charts |
| `portfolio_manager.py` | Loads tickers + emojis from portfolio_config.json |
| `etoro_history.py` | Parses eToro Excel export — closed trades, dividends, stats |
| `gist_storage.py` | All persistent state stored in a GitHub Gist (performance, dedup, tags) |
| `api_usage_tracker.py` | Tracks Gemini API calls per model |
| `sheets_fetcher.py` | Google Sheets read/write for long-term tracking |

---

## AI (Gemini) usage

Model chain (tries in order, falls back on quota/error):
`gemini-2.0-flash` → `gemini-2.5-flash` → `gemini-flash-latest`

| Endpoint | When | Language | Max length |
|---|---|---|---|
| Daily market news recap | Every session | English | ~800 chars |
| Monthly market recap | Monthly session | English | ~1200 chars |
| Decision post | Monday (manual) | Italian | 1400 chars |
| Empathy post | Monday (manual) | Italian | 1200 chars |

Tag rotation: picks max 4 portfolio tickers per post, avoids repeating the same ones
for several sessions (state stored in Gist under `used_tags`).

---

## Persistent storage (GitHub Gist)

All state lives in a single Gist file (JSON). Key fields:

| Key | Content |
|---|---|
| `performance_history` | Daily snapshots of portfolio % cumulative |
| `ath` | All-time high value and date |
| `used_tags` | Tickers used in recent posts (tag rotation) |
| `recap_history` | Last N recap texts (dedup + Gemini context) |
| `session_runs` | Date of last run per session (dedup) |
| `etoro_history` | Parsed Excel data: closed trades, stats, dividends |
| `pie_chart_counter` | Which pie chart type to show next (0–3) |

---

## eToro history import

The decision post needs real trade data. This comes from an Excel export uploaded manually.

```bash
# 1. Export from eToro → Account → Settings → Account Statement (Excel)
# 2. Upload the file, then run:
python scripts/import_etoro_history.py --file "Account Statement.xlsx"
# This parses trades/dividends and saves them to Gist under etoro_history
```

Without this import, `get_history_from_gist()` returns `{}` and the decision post
is generated with no real trade context → Gemini produces a generic, vague post.

---

## Secrets required (GitHub → Settings → Environments → Etoro)

| Secret | Used by |
|---|---|
| `GEMINI_API_KEY` | AI news, decision post, empathy post |
| `TELEGRAM_BOT_TOKEN` | All Telegram sends |
| `TELEGRAM_CHAT_ID` | All Telegram sends |
| `GIST_ACCESS_TOKEN` | All persistent storage |
| `GIST_ID` | All persistent storage |
| `GOOGLE_SHEETS_CREDENTIALS` | Google Sheets sync |
| `SPREADSHEET_ID` | Google Sheets sync |
| `TWITTER_API_KEY` + `TWITTER_API_SECRET` + `TWITTER_ACCESS_TOKEN` + `TWITTER_ACCESS_SECRET` | Twitter/X |
| `BLUESKY_HANDLE` + `BLUESKY_APP_PASS` | Bluesky |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn |
| `BASE44_API_TOKEN` | getEtoroDataBundle API (test workflow) |

---

## How to trigger manually

```bash
# Normal recap (any session name)
gh workflow run daily-recap.yml -f force_session="U.S. market close"

# Monday posts
gh workflow run daily-recap.yml -f force_session="Monday decision post"

# Weekly
gh workflow run daily-recap.yml -f force_session="Weekly recap (Sat)"

# Test eToro API bundle
gh workflow run test-etoro-bundle.yml -f username=andrearavalli -f trade_history_days=90

# Watch live
gh run watch $(gh run list --workflow=daily-recap.yml --limit 1 --json databaseId -q '.[0].databaseId')
```

---

## Known issues

| Issue | Severity | File | Status |
|---|---|---|---|
| `portfolio_weights` not passed to `_publish_monday_posts` → decision post lacks top holdings context | Medium | `social_publisher.py` line 147 | Open |
| No cron schedule for Monday — must be triggered manually | By design | `daily-recap.yml` | By design |
| Meta (Threads/Facebook/Instagram) disabled | Medium | `threads_sender.py` etc. | Pending |
| BullAware Selenium scrape breaks if layout changes | Medium | `finance_fetcher.py` | Open |
| `etoro_history` empty if no Excel imported → generic decision post | High | `etoro_history.py` | Needs import |
| getEtoroDataBundle API returns `totalTrades: 0` for andrearavalli | Unknown | `test-etoro-bundle.yml` | Investigate |
