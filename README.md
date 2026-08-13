# 📊 Portfolio Daily Recap & Social Syndication Engine

[![Daily Portfolio Recap](https://github.com/giga89/portfolio-daily-recap/actions/workflows/daily-recap.yml/badge.svg)](https://github.com/giga89/portfolio-daily-recap/actions/workflows/daily-recap.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![eToro Popular Investor](https://img.shields.io/badge/eToro-AndreaRavalli-00C853.svg?logo=etoro&logoColor=white)](https://www.etoro.com/people/andrearavalli)
[![Orange Pi 5](https://img.shields.io/badge/Scheduler-Orange_Pi_5-FF6F00.svg?logo=linux&logoColor=white)](scripts/orangepi-scheduler/README.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An institutional-grade, fully automated portfolio analytics, AI financial journalism, visual infographic generation, and multi-platform social syndication engine.

Built specifically for **Andrea Ravalli**'s Popular Investor portfolio on **eToro**, it tracks live holdings, benchmark comparisons, stock deep-dives, and cryptocurrency sentiment across 7 daily/weekly market sessions.

---

## 🌟 Key Capabilities

* 📈 **Live Portfolio Intelligence**: Real-time position weighting, daily/weekly/monthly/YTD performance, and 5-year cumulative historical track record vs. 4 major benchmarks (**S&P 500**, **Nasdaq 100**, **MSCI World**, **Euro Stoxx 50**).
* 🐂 **Native eToro Social Feed Integration**: Formats and automatically posts updates directly to Andrea's official eToro Social Feed with cashtag resolution, image uploads, and automated 3-comment cross-linking sequences.
* 🪙 **Daily Crypto Pulse & Sentiment**: Live 16:9 card generator featuring the **Crypto Fear & Greed Index**, spot prices, 24h volumes, $TRX portfolio highlight, and a dynamic 4th altcoin selected from **30 pre-cached official crypto logos**.
* 🔍 **Stock Focus Deep-Dive**: 1:1 high-resolution visual infographics with bull/bear catalysts, investment theses, valuation multiples, and sector comparisons.
* 🤖 **AI Financial Journalism (Google Gemini)**: Natural, engaging financial commentary tailored for European and US markets with automatic multi-model quota fallback (`gemini-2.5-flash` → `gemini-2.5-pro` → `gemini-2.0-flash`).
* 🎨 **Visual Graphics Engine**: Automated high-res visual assets:
  * **16:9 Crypto Daily Card** (`crypto_card_generator.py`)
  * **1:1 Stock Focus Infographics** (`stock_focus_infographic.py`)
  * **Top & Flop / Winners & Losers Card** (`winners_losers_card.py`)
  * **Cumulative Performance vs Benchmarks Line Chart** (`chart_generator.py`)
  * **Rotating 4-Theme Allocation Pie Charts** (`pie_chart_generator.py`)
* 🍊 **Orange Pi 5 Local Precision Scheduler**: Dual-slot cron triggers on local hardware with hour-bucket deduplication to guarantee on-the-minute execution regardless of daylight saving time (DST) shifts.
* 🌐 **Multi-Platform Syndication**: Automated routing to **eToro Feed**, **Telegram**, **LinkedIn**, **Twitter/X**, **Bluesky**, and **Meta Threads/Facebook/Instagram**.
* 📊 **Analytics Dashboard**: Continuous tracking of post engagement and API usage published to GitHub Pages.

---

## ⏰ Daily & Weekly Market Sessions

| Session Name | Trigger (ITA Local Time) | Content & Generated Visuals | Target Platforms |
| :--- | :--- | :--- | :--- |
| **`European market open`** | 🕘 **09:02** (Mon–Fri) | European market catalysts, Top 5 daily, ATH distance + 3 automatic cross-linking comments | Telegram, eToro Feed |
| **`Stock focus`** | 🕑 **14:00** (Mon–Fri) | Single stock deep-dive with **1:1 HD Infographic**, bull/bear thesis & competitor check | Telegram, eToro Feed |
| **`U.S. market open`** | 🕞 **15:32 / 16:32** (Mon–Fri) | Wall Street opening moves, tech catalysts + 3 automatic cross-linking comments | Telegram, eToro Feed |
| **`Daily crypto recap`** | 🕕 **18:00** (Every Day) | **16:9 Crypto Card**, Fear & Greed Index, $BTC, $ETH, $TRX (in portfolio) + dynamic altcoin | Telegram, eToro Feed |
| **`U.S. market close`** | 🕙 **22:02 / 23:02** (Mon–Fri) | Full daily wrap-up, benchmark comparisons, performance chart, pie chart, top/flop card + 3 comments | Telegram, eToro Feed, Twitter, Bluesky, Threads, FB, IG |
| **`Weekly recap (Sat)`** | 🕙 **10:00** (Saturday) | Weekly portfolio outlook, macro recap, sector performance, **Winners & Losers Card** | Telegram, eToro Feed, LinkedIn |
| **`Weekly recap (Sun)`** | 🕙 **22:00** (Sunday) | Upcoming catalysts, earnings preview, central bank schedule for the week ahead | Telegram, eToro Feed, LinkedIn |

---

## 📁 Repository Architecture

```
portfolio-daily-recap/
├── .github/workflows/
│   └── daily-recap.yml               # GitHub Actions CI/CD orchestration
├── assets/
│   ├── logos/                        # 70+ high-res local logos (30 crypto + 40+ stocks/ETFs)
│   └── profile_photo.jpg             # Andrea Ravalli branding photo
├── docs/
│   └── index.html                    # Live analytics dashboard (GitHub Pages)
├── scripts/
│   ├── orangepi-scheduler/           # 🍊 Local precision cron dispatcher
│   │   ├── dispatch.sh               # Repository dispatch script with dedup
│   │   ├── crontab.txt               # DST-resilient crontab configuration
│   │   └── README.md                 # Orange Pi setup instructions
│   ├── download_crypto_logos.py      # Download & optimize 30 eToro crypto logos
│   ├── download_logos.py             # Download & optimize stock/ETF logos
│   └── import_etoro_history.py       # eToro portfolio history importer
├── src/
│   ├── ai_news_generator.py          # Gemini AI financial commentary & crypto posts
│   ├── analytics_tracker.py          # Post tracking & GitHub Pages dashboard builder
│   ├── chart_generator.py            # Dark-mode performance vs. benchmark chart
│   ├── config.py                     # Asset definitions, tickers, and emoji mappings
│   ├── cross_link_scheduler.py       # 3-comment automated cross-linking sequence on eToro
│   ├── crypto_card_generator.py      # 16:9 Dark Neon Crypto Daily Recap card generator
│   ├── crypto_fetcher.py             # Live crypto prices, 24h volume & Fear & Greed fetcher
│   ├── data_collector.py             # Main data orchestrator
│   ├── etoro_client.py               # Official eToro API client (feeds, media, instruments)
│   ├── etoro_sender.py               # eToro Social Feed formatting & dispatch
│   ├── finance_fetcher.py            # Yahoo Finance real-time price & volume engine
│   ├── formatter.py                  # Multi-tier recap text formatting
│   ├── gist_storage.py               # Cloud state persistence (ATH, rotation, dedup)
│   ├── pie_chart_generator.py        # 4-theme rotating allocation pie charts
│   ├── social_publisher.py           # Multi-platform routing & publishing coordinator
│   ├── stock_focus_card.py           # 1:1 stock focus square card generator
│   ├── stock_focus_infographic.py    # 1:1 high-res stock deep-dive infographic generator
│   ├── telegram_sender.py            # Telegram Bot API integration
│   ├── twitter_sender.py             # Twitter / X API integration
│   ├── bluesky_sender.py             # Bluesky AT Protocol integration
│   ├── linkedin_sender.py            # LinkedIn API integration
│   └── winners_losers_card.py        # Top & Flop visual engagement card generator
├── test_all_sessions.py              # Test suite for all market sessions
├── requirements.txt                  # Python dependencies
└── README.md                         # This documentation
```

---

## 🛠️ Setup & Configuration

### Prerequisites
* Python 3.11+
* GitHub Account with standard repository secrets
* *(Optional)* Orange Pi / Raspberry Pi running the local cron dispatcher

### Required Secrets (`Settings > Secrets and variables > Actions`)

| Secret Name | Purpose |
| :--- | :--- |
| `ETORO_USER_KEY` | eToro API User Key for Social Feed publishing |
| `ETORO_USER_NAME` | eToro account username (`andrearavalli`) |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token from [@BotFather](https://t.me/botfather) |
| `TELEGRAM_CHAT_ID` | Telegram Channel or Chat ID |
| `GEMINI_API_KEY` | Google AI Studio API Key ([Google AI Studio](https://aistudio.google.com/)) |
| `GIST_TOKEN` | GitHub Personal Access Token (PAT) for Gist state persistence |
| `LINKEDIN_ACCESS_TOKEN` | *(Optional)* LinkedIn OAuth2 token for weekly posts |
| `TWITTER_API_KEY` / `_SECRET` | *(Optional)* Twitter / X API credentials |
| `BLUESKY_HANDLE` / `_PASSWORD` | *(Optional)* Bluesky login credentials |

---

## 🧪 Local Testing & Verification

Run the comprehensive test suite to preview recaps and generate test cards locally:

```bash
# 1. Test all sessions simulation
python3 test_all_sessions.py

# 2. Test Crypto Daily Recap card generation & live data
python3 src/crypto_card_generator.py

# 3. Test Stock Focus Infographic generation
python3 -c "import sys; sys.path.insert(0, 'src'); import stock_focus_infographic as s; s.generate_infographic('NVDA', 'output/infographic_NVDA.png')"

# 4. Check syntax of Orange Pi dispatcher
bash -n scripts/orangepi-scheduler/dispatch.sh
```

---

## 👤 Author & Profile

* **Popular Investor**: [Andrea Ravalli on eToro](https://www.etoro.com/people/andrearavalli)
* **Hub & Links**: [bio.mega89.uk](https://bio.mega89.uk/)

---
*Maintained with ❤️ for the eToro CopyTrading Community.*
