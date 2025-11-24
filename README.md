# 📊 Portfolio Daily Recap

Automated daily portfolio performance recap generator with GitHub Actions. Collects data from eToro, BullAware, and Google Sheets to generate a comprehensive daily summary.

## ✨ Features

- 🤖 **Fully Automated**: Runs daily at 16:00 UTC (17:00 CET) via GitHub Actions
- 🚀 **Multiple Data Sources**:
  - **eToro**: Today's performance + Top 5 daily performers
  - **BullAware**: Monthly and yearly performance data
  - **Google Sheets**: 5-year cumulative performance
- 🎯 **Smart Formatting**: Emoji indicators for each asset
- 📈 **Performance Calculations**: Average yearly return & "double your money" timeline

## 📝 Sample Output

```
📊 RECAP PORTFOLIO GIORNALIERO

🍀🍀🍀 Oggi: +1.53%
🚧 Questo Mese: -5.05%
🔧 Quest'Anno: +23.2%
🌳 Ultimi 5 Anni (2020-2025): 156%

📊 Performance Media Annua: 31.2%
⏳ Tempo per Raddoppiare: 2.3 anni

TOP 5 OGGI:
🎮 NVDA: +5.2%
💻 MSFT: +3.1%
🔍 GOOG: +2.8%
💊 LLY: +2.1%
🖥️ TSM: +1.9%
```

## 🚀 Setup Instructions

### 1. Fork or Clone this Repository

```bash
git clone https://github.com/giga89/portfolio-daily-recap.git
cd portfolio-daily-recap
```

### 2. Configure GitHub Secrets

Go to **Settings** → **Secrets and variables** → **Actions** and add:

#### Required Secrets:

- `ETORO_USERNAME`: Your eToro username (e.g., "AndreaRavalli")
- `SPREADSHEET_ID`: Your Google Sheets spreadsheet ID
- `GOOGLE_SHEETS_CREDENTIALS`: Google Service Account JSON credentials

#### How to Get Google Sheets Credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google Sheets API**
4. Create **Service Account** credentials
5. Download JSON key file
6. Copy entire JSON content and paste as secret
7. Share your Google Sheet with the service account email

### 3. Enable GitHub Actions

- Go to **Actions** tab
- Enable workflows if prompted
- The workflow will run automatically every day at 16:00 UTC

### 4. Manual Trigger (Optional)

- Go to **Actions** tab
- Select **Daily Portfolio Recap** workflow
- Click **Run workflow** → **Run workflow**

## 📦 Repository Structure

```
portfolio-daily-recap/
├── .github/
│   └── workflows/
│       └── daily-recap.yml    # GitHub Actions workflow
├── src/
│   └── data_collector.py   # Main script with EMOJI_MAP
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔧 Customization

### Update EMOJI_MAP

Edit `src/data_collector.py` to add/modify emoji mappings for your assets:

```python
EMOJI_MAP = {
    'NVDA': '🎮',
    'MSFT': '💻',
    'GOOG': '🔍',
    # Add your assets here...
}
```

### Change Schedule

Edit `.github/workflows/daily-recap.yml`:

```yaml
on:
  schedule:
    - cron: '0 16 * * *'  # Change time here (UTC)
```

## 📊 Current Portfolio Holdings

The system includes emoji mappings for:

**ETFs**: SX7PEX.DE, WDEF.L, IEMG, IQQL.DE, IEUR

**Healthcare**: AZN.L, ABT, ABBV, LLY, NOVO-B, HUM

**Technology**: AVGO, NVDA, TSM, MSFT, SNPS, GOOG

**Energy**: CCJ, PRY.MI, ENEL.MI

**Crypto**: TRX, NET

**Finance**: TRIG.L, DB1.DE, 2318.HK

**Consumer**: RACE, MELI, AMZN, PYPL

**Industrial**: GLEN.L, VOW3.DE, BHP.L

**Transportation**: 1919.HK

**Other**: ETOR, PLTR

## 🔍 How It Works

1. **GitHub Actions** triggers daily at scheduled time
2. **Playwright** scrapes eToro for today's data
3. **Playwright** scrapes BullAware for monthly/yearly data  
4. **Google Sheets API** fetches 5-year performance
5. **Script** generates formatted recap with emojis
6. **Output** saved as artifact (`output/recap.txt`)

## 📝 License

MIT License - feel free to use and modify!

## 🚀 Contributing

Feel free to open issues or submit pull requests!

---

**Made with ❤️ by Andrea Ravalli**
