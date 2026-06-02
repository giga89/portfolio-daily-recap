# 📊 Portfolio Daily Recap

Automated daily portfolio performance recap generator with GitHub Actions. It collects financial data from **Yahoo Finance**, syncs results with **Google Sheets**, generates AI-powered market news using **Google Gemini**, and sends formatted reports via **Telegram bot** twice daily.

## 🌟 Features

- 📈 **Multi-source data collection**: Yahoo Finance (real-time YTD, monthly, daily), BullAware (weighted positions), Google Sheets (historical performance).
- 🤖 **AI Market News**: AI-generated daily recap of USA, CHINA, and EU markets + specific portfolio focus using **Google Gemini** (with multi-model fallback).
- ⚖️ **Weighted Performance**: Calculates overall portfolio performance based on actual position weights (scraped from BullAware).
- ⏰ **Precise Scheduling**: Market recaps triggered at exact times via **Orange Pi 5 local scheduler** (with GitHub Actions cron as fallback). Three daily sessions: EU open, US open, US close.
- 🤖 **Telegram Notifications**: Sends beautiful, emoji-enriched reports with dynamic headers and performance indicators.
- 📊 **Benchmark Comparison**: Automatically compares your strategy performance since 2020 against S&P 500, Nasdaq 100, MSCI World, and Euro Stoxx 50.
- 💡 **Strategic Insights**: Includes a "Why Copy This Portfolio" section with long-term metrics and strategy highlights.
- 📉 **Performance Chart**: Generates a beautiful "dark mode" line chart comparing cumulative portfolio return vs. benchmarks since 2020.
- 🚀 **Fast and Reliable**: Direct API access via `yfinance` and `google-genai`, with smart session detection for US markets.

## 📋 How It Works

### 1. Data Collection & Synchronization
- **Yahoo Finance**: Fetches true Year-to-Date (YTD) from Jan 1st, 30-day monthly changes, and daily performance.
- **BullAware**: Scrapes current portfolio position weights using Selenium to ensure the overall performance calculation is accurate to your actual allocation.
- **Google Sheets**: Reads and writes long-term performance data (e.g., 5-year returns) to maintain a persistent track record.

### 2. AI Intelligence
- Uses **Google Gemini API** to analyze market trends in the last 24 hours.
- Focuses specifically on news affecting your portfolio holdings.
- Implements a robust fallback system (Gemini 2.0 Flash -> 1.5 Flash -> 1.5 Pro) to handle API quotas.

### 3. Output & Delivery
- Generates a markdown-formatted message.
- Dynamically selects headers and emojis based on market performance (e.g., "TO THE MOON 🚀" vs "ROUGH DAY 💀").
- Posts the final report to your Telegram bot.

## 📁 Project Structure

```
portfolio-daily-recap/
├── .github/workflows/
│   └── daily-recap.yml       # GitHub Actions schedule & logic
├── src/
│   ├── ai_news_generator.py  # Gemini AI news & strategy recap
│   ├── config.py             # Tickers mapping & emoji settings
│   ├── data_collector.py     # Main orchestrator (entry point)
│   ├── chart_generator.py    # Performance chart visualization (matplotlib)
│   ├── finance_fetcher.py    # Yahoo Finance & BullAware logic
│   ├── formatter.py          # Message formatting & logic
│   ├── sheets_fetcher.py     # Google Sheets API integration
│   ├── telegram_sender.py    # Telegram Bot API integration
│   └── update_weights.py     # Utility to sync portfolio weights
├── scripts/
│   ├── orangepi-scheduler/       # 🍊 Local cron scheduler (Orange Pi 5)
│   │   ├── dispatch.sh           # GitHub API dispatch script
│   │   ├── crontab.txt           # Market session cron schedule
│   │   ├── .env.example          # Config template (GitHub token)
│   │   └── README.md             # Setup instructions
│   └── import_etoro_history.py   # eToro data import utility
├── output/
│   └── recap.txt             # Latest generated report
├── requirements.txt          # Python dependencies
└── README.md                 # This documentation
```

## 🛠️ Setup

### Prerequisites
- Python 3.9+
- Telegram Bot Token ([@BotFather](https://t.me/botfather))
- Google Gemini API Key ([Google AI Studio](https://makersuite.google.com/app/apikey))
- Google Cloud Service Account (for Sheets API)

### Configuration
1. **Repository Secrets**: Add the following to your GitHub repo (`Settings > Secrets > Actions`):
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - `GEMINI_API_KEY`
   - `GOOGLE_CREDENTIALS_JSON`, `GOOGLE_SHEET_ID`

2. **Ticker Mapping**: Edit `src/config.py` to define your `PORTFOLIO_TICKERS` (mapping eToro symbols to Yahoo tickers) and `EMOJI_MAP`.

## 🚀 Usage

### Manual Execution (Local)
```bash
# Set session and run
MARKET_SESSION="16:00 Open" python src/data_collector.py
```

### Automatic (GitHub Actions)
Triggered via:
1. **Orange Pi 5 scheduler** (primary) — dispatches at precise market times via `repository_dispatch`
2. **GitHub Actions cron** (fallback) — runs if Orange Pi is offline
3. **Manual trigger** — via `workflow_dispatch` in the GitHub Actions UI

See [`scripts/orangepi-scheduler/README.md`](scripts/orangepi-scheduler/README.md) for scheduler setup.

## 📊 Sample Output
```
🌠 DAILY RECAP 🌙

⚖️ ⚖️ ⚖️ MINOR DIP: -0.22% ⚖️ ⚖️ ⚖️

TOP 5 TODAY PERFORMANCE OF PORTFOLIO 📈
🏦 $2318.HK Ping An Insurance +1.77%
💼 $WDEF.L WisdomTree Europe Eq +1.22%
🌍 $IEMG iShares Core Emerging +1.02%
⛏️ $GLEN Glencore +0.32%
📊 $DB1.DE Xtrackers MSCI World +0.23%

🌍 MARKET NEWS RECAP
The S&P 500 edged higher today as investors digested new inflation data...

💼 PORTFOLIO FOCUS
NVIDIA ($NVDA) saw increased volume following reports of new AI chip orders...

💡 WHY COPY THIS PORTFOLIO?
📈 TRACK RECORD: +161% since 2020 (~32% CAGR)
✅ STRATEGY: AI, Healthcare, and Energy megatrends focus.
📊 DELTA VS BENCHMARKS: +95% vs S&P500, +112% vs MSCI World.
```

## 📝 Recent Improvements (v2.0)
- **Weighted Average**: Accurate portfolio performance reflecting position sizing.
- **True YTD**: Replaced estimation with real start-of-year calculations.
- **Gemini 2.0 Integration**: Uses latest AI models for market analysis.
- **Zero Selenium Dependency for YTD**: Faster runs by using direct ticker history.
- **Flexible Sessions**: Smart handling of European vs US market hours.
- **Visual Charts**: Added automated performance comparison chart sent as an image on Telegram.
- **Robust Benchmarking**: Improved historical data alignment for global indices.

## 🤝 Contributing
Feel free to fork and submit PRs for new features or improvements.

## 📜 License
MIT License. Created with ❤️ by [Andrea Ravalli](https://github.com/giga89).
