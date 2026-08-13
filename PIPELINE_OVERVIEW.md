# Pipeline Overview — Portfolio Daily Recap

Quick reference for when you lose the thread.
Last reviewed: May 2026.

---

## What runs and when

| Trigger (Orange Pi 5 / Fallback GitHub Cron) | Session name | What it does | Targets |
|---|---|---|---|
| Mon–Fri 07:02 UTC (09:02 ITA) | `European market open` | Recap + Top 5 + ATH distance + 3 automatic cross-linking comments | Telegram, eToro Feed |
| Mon–Fri 12:00 UTC (14:00 ITA) | `Stock focus` | Single stock deep-dive with 1:1 HD Infographic, bull/bear thesis & valuation | Telegram, eToro Feed |
| Mon–Fri 13:32 / 14:32 UTC (15:32 / 16:32 ITA) | `U.S. market open` | Opening moves, AI/Tech catalysts + 3 automatic cross-linking comments | Telegram, eToro Feed |
| Daily 16:00 UTC (18:00 ITA) | `Daily crypto recap` | 16:9 Crypto Card, Fear & Greed Index, $BTC, $ETH, $TRX, and dynamic altcoin | Telegram, eToro Feed |
| Mon–Fri 20:02 / 21:02 UTC (22:02 / 23:02 ITA) | `U.S. market close` | Full daily wrap-up, benchmark charts, pie chart, Top & Flop card + 3 comments | Telegram, eToro, Twitter, Bluesky, Threads, FB, IG |
| Saturday 08:00 / 09:00 UTC (10:00 ITA) | `Weekly recap (Sat)` | Weekly portfolio & macro recap with Top & Flop card | Telegram, eToro Feed, LinkedIn |
| Sunday 20:00 / 21:00 UTC (22:00 ITA) | `Weekly recap (Sun)` | Upcoming catalysts, earnings & central banks schedule | Telegram, eToro Feed, LinkedIn |

**Important:** Triggered primarily by the Orange Pi 5 local scheduler (`dispatch.sh`) with hour-bucket deduplication to guarantee on-the-minute execution regardless of daylight saving time (DST).

---

## Data flow (one normal session)

```
[Orange Pi 5 crontab fires / GitHub Actions cron fallback]
        ↓
[Detect session name from repository_dispatch or cron schedule]
        ↓
[Dedup check — skip if already ran this session in this hour]
        ↓
[data_collector.py — main entry point]
    1. Fetch stock prices → yfinance
    2. Fetch portfolio weights → live holdings from eToro API
    3. Weighted daily performance = sum(weight * daily_change)
    4. YTD performance → eToro public API (userstats + rankings)
    5. Cumulative 5-year return → eToro history seeded from Gist
    6. Benchmark comparison → yfinance (SP500, NDX, MSCI, EuroStoxx)
    7. Weekly / monthly perf → yfinance (if session requires it)
    8. Performance chart → chart_generator.py (matplotlib, portfolio vs benchmarks)
    9. Pie chart → pie_chart_generator.py (rotates: allocation / sector / geo / PnL)
   10. AI market news → ai_news_generator.py (Gemini 2.5 Flash / Pro API)
   11. Format recap → formatter.py → output/recap.txt
        ↓
[social_publisher.py — route to platforms based on session]
    → eToro Feed: every session (recap text + Top/Flop or Infographic/Crypto card + 3 auto comments)
    → Telegram:   every session (formatted text + HD visual cards)
    → Twitter/X:  US close only (2-tweet thread)
    → Bluesky:    US close only (2-post thread)
    → LinkedIn:   Weekly only (professional format)
    → Threads / Facebook / Instagram: US close (Meta Graph API)
        ↓
[gist_storage.py & analytics_tracker.py — persist state & dashboard]
    → Performance history snapshot & ATH tracking
    → Tag rotation state (avoids repeating same tickers)
    → Post analytics & GitHub Pages dashboard generation
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
