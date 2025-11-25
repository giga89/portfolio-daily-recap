# 📊 Portfolio Daily Recap

Automated daily portfolio performance recap generator with GitHub Actions. Collects financial data from **eToro**, **Yahoo Finance**, and **Google Sheets**, generates formatted performance reports, and sends them via **Telegram bot** twice daily.

## 🌟 Features

- 📈 **Multi-source data collection**: Yahoo Finance (via yfinance), BullAware, Google Sheets
- ⏰ **Automated scheduling**: Runs twice daily at 16:00 and 22:00 CET via GitHub Actions
- 🤖 **Telegram notifications**: Sends formatted reports with emoji indicators to your Telegram
- 📊 **Performance metrics**: Daily, monthly, and YTD (Year-to-Date) changes for each holding
- 🎨 **Emoji mapping**: Visual indicators for each stock/ETF
- 🌍 **US market handling**: Smart session detection for US stocks (only reports daily changes after market close)
- 📁 **Google Sheets integration**: Syncs 5-year portfolio returns data
- 🚀 **Fast and reliable**: Uses yfinance API for accurate, real-time YTD calculations

## 📋 How It Works

### Data Collection

1. **Yahoo Finance (yfinance)**
   - Fetches daily, monthly, and **true YTD** data (calculated from January 1st of current year)
   - Automatic fallback to 252-trading-day calculation if YTD data unavailable
   - Smart handling of US vs non-US stocks for daily performance

2. **BullAware (optional)**
   - Can fetch portfolio-level aggregate YTD via simple HTTP requests (no Selenium)
   - Used for Google Sheets synchronization

3. **Google Sheets**
   - Reads 5-year portfolio returns
   - Updates with latest performance data

### Schedule

The workflow runs automatically via GitHub Actions:
- **16:00 CET**: First daily recap (US markets still open)
- **22:00 CET**: Second daily recap (all markets closed)

US stock daily performance is **only reported at 22:00** to ensure accurate end-of-day data.

### Output

Formatted Telegram message with:
- 🏆 **Top 5 daily performers** (today's winners)
- 📉 **Top 3 monthly performers** (this month's winners)
- 📈 **Top 3 yearly performers** (YTD leaders)

Each entry includes emoji, ticker, company name, and performance percentage.

## 🛠️ Setup

### Prerequisites

- Python 3.9+
- GitHub repository with Actions enabled
- Telegram Bot (via [@BotFather](https://t.me/botfather))
- Google Cloud Service Account with Sheets API access

### Installation

1. **Clone the repository**
git clone https://github.com/giga89/portfolio-daily-recap.git
cd portfolio-daily-recap

2. **Install dependencies**
pip install -r requirements.txt


3. **Configure secrets**

Add these secrets to your GitHub repository (`Settings > Secrets and variables > Actions`):

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from BotFather
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID (get from [@userinfobot](https://t.me/userinfobot))
- `GOOGLE_CREDENTIALS_JSON`: Your Google Cloud service account credentials (JSON format)
- `GOOGLE_SHEET_ID`: Your Google Sheets document ID

### Configuration

Edit `src/config.py` to customize:

1. **Portfolio tickers** (`PORTFOLIO_TICKERS`)
- Map eToro symbols to Yahoo Finance tickers
- Add company names

2. **Emoji mapping** (`EMOJI_MAP`)
- Assign emojis to each holding for visual representation

## 📁 Project Structure
```
portfolio-daily-recap/
├── .github/
│ └── workflows/
│ └── daily-recap.yml # GitHub Actions workflow
├── src/
│ ├── config.py # Portfolio configuration & emoji mapping
│ ├── finance_fetcher.py # Yahoo Finance data fetcher (YTD from Jan 1st)
│ ├── data_collector.py # Orchestrates data collection
│ ├── sheets_fetcher.py # Google Sheets integration
│ ├── formatter.py # Report formatting
│ └── telegram_sender.py # Telegram bot integration
├── output/
│ └── recap.txt # Generated report (committed to repo)
├── requirements.txt # Python dependencies
└── README.md # This file
```

## 🔧 Key Components

### `finance_fetcher.py`
- **YTD Calculation**: Calculates true Year-to-Date performance from January 1st using `yfinance`
- **Smart fallback**: Uses 252-trading-day method if YTD data unavailable
- **Portfolio YTD function**: Optional `fetch_portfolio_ytd_from_bullaware()` for aggregate portfolio YTD

### `formatter.py`
- Generates markdown-style formatted reports
- Emoji integration for visual appeal
- Smart sorting and filtering of top/bottom performers

### `telegram_sender.py`
- Sends formatted reports via Telegram Bot API
- Markdown formatting support

## 🚀 Usage

### Manual Run (Local)

python -m src.data_collector

Set the session variable:
MARKET_SESSION="16:00" python -m src.data_collector # Midday run
MARKET_SESSION="22:00" python -m src.data_collector # Evening run


### Automated Run (GitHub Actions)

The workflow is triggered automatically by schedule. You can also trigger manually:
1. Go to **Actions** tab in your repository
2. Select **Daily Portfolio Recap**
3. Click **Run workflow**
4. Choose the session time (16:00 or 22:00)

## 📊 Sample Output
```
✨✨✨EUROPEAN MARKET OPEN PORTFOLIO ✨✨✨

    💀 💀 💀 TODAY PERFORMANCE -0.02% 💀 💀 💀
    
161% SINCE CHANGE OF STRATEGY (2020) 🚀🚀🚀
32% PER YEAR (DOUBLE YOUR MONEY IN 2.24 YEARS)

TOP 5 TODAY PERFORMANCE OF PORTFOLIO 📈
🏦 [$2318.HK (Ping An Insurance)] +1.77%
💼 [$WDEF.L (WisdomTree Europe Equity Income UCITS ETF)] +1.22%
🌍 [$IEMG (iShares Core MSCI Emerging Markets ETF)] +1.02%
⛏️ [$GLEN (Glencore)] +0.32%
📊 [$DB1.DE (Xtrackers MSCI World Momentum UCITS ETF)] +0.23%

TOP 3 MONTHLY PERFORMANCE OF PORTFOLIO 📈
💊 [$LLY (Eli Lilly & Co)] +31.93%
🔍 [$GOOG (Alphabet)] +29.79%
🧬 [$AZN.L (AstraZeneca)] +9.92%

TOP 3 HOLDING YEARLY PERFORMANCE OF PORTFOLIO 📈
🛡️ [$PLTR (Palantir Technologies Inc)] +115.79%
☁️ [$NET (Cloudflare)] +72.37%
🔍 [$GOOG (Alphabet)] +68.73%

@AndreaRavalli
...
```

## 🔐 Security

- **Secrets management**: All sensitive data stored in GitHub Secrets
- **No hardcoded credentials**: Service accounts and tokens loaded at runtime
- **Read-only Google Sheets access**: Service account has minimal permissions

## 🛡️ Error Handling

- Graceful fallbacks for missing data
- Comprehensive error logging
- Continues processing even if individual stocks fail
- Automatic retries for API calls

## 📝 Recent Changes (v2.0)

### ✅ Removed Selenium Complexity
- **Before**: Complex Selenium-based scraping for individual stock YTD from BullAware treemap
- **After**: Direct YTD calculation from Yahoo Finance using `datetime` (Jan 1st start)

### ✅ Improved YTD Accuracy
- **True YTD**: Calculated from January 1st of current year, not 252 trading days
- **Fallback**: Uses 252-day method only when YTD data unavailable
- **Faster**: No browser automation overhead

### ✅ Simplified Architecture
- Removed: `selenium`, `webdriver`, `expected_conditions`
- Kept: Simple `requests` + `BeautifulSoup` for optional portfolio-level data
- Result: Faster runs, fewer dependencies, more maintainable

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📜 License

MIT License - feel free to use and modify for your own portfolio tracking!

## 🙏 Acknowledgments

- **yfinance**: Real-time financial data
- **BullAware**: Portfolio analytics (optional)
- **GitHub Actions**: Free CI/CD automation
- **Telegram**: Instant notifications

---

**Made with ❤️ by [Andrea Ravalli](https://github.com/giga89)**

*Track your investments smarter, not harder.* 📈
