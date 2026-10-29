# 🍊 Orange Pi 5 — Local Market Scheduler

Local cron scheduler that triggers GitHub Actions workflows at **precise market times**, bypassing the unreliable GitHub Actions cron queue (which can delay jobs 5–40+ minutes).

## How It Works

```
Orange Pi 5 crontab (precise to the second)
  → dispatch.sh calls GitHub API (repository_dispatch)
    → GitHub Actions workflow starts immediately (no cron queue)
      → Recap generated and sent within ~5–8 min of market event
```

## Schedule (Italian Local Time — Europe/Rome)

All cron entries are scheduled directly in Italian local time (`Europe/Rome` - CET/CEST), matching real market opening and community hours. Wall Street sessions include dual slots and are guarded in `dispatch.sh` by live New York exchange time to automatically handle daylight saving transitions without manual adjustments.

| Session | Cron Trigger (ITA) | Real Market Time | Description |
|---|---|---|---|
| **EU Open** | Mon–Fri 09:02 | 09:00 Milan/Frankfurt, 08:00 London | European market open recap |
| **Dividend Post** | Mon, Thu 09:45 | — | Dividend announcements check |
| **Event Monitor** | Mon–Fri 10:00 & 15:15/16:15 | — / 10:15 New York | Corporate earnings (prior-day AMC morning & BMO post-US open) + dividend pay days |
| **Weekly (Sat)** | Sat 10:00 | — | Saturday weekly portfolio recap |
| **Stock News** | Daily 11:30, 17:00, 23:30 | — | Catalyst follow-ups (3x daily) |
| **Copy Trading** | Mon–Fri 13:30 / Sat 12:00 | — | Educational copy trading post |
| **Community Poll** | Mon, Wed, Fri 12:30 | — | Interactive community sentiment poll |
| **Stock Focus** | Mon–Fri 14:00 | — | Midday stock deep-dive & infographic |
| **US Open** | Mon–Fri 14:32 / 15:32 | 09:32 New York | Wall Street opening moves (guarded by ET) |
| **Crypto Recap** | Mon–Sat 18:00 / Sun 14:00 | — | Crypto card, fear & greed, altcoins |
| **US Close** | Mon–Fri 21:02 / 22:02 | 16:02 New York | Daily wrap-up & benchmark charts (guarded by ET) |
| **Monthly Recap** | Month end 21:02 / 22:02 | 16:02 New York | Full month recap (replaces US close on final day) |
| **Weekly (Sun)** | Sun 22:00 | — | Sunday macro & week ahead preview |
| **Dashboard Sync** | Daily 02:00 | — | Nightly metrics & track record sync |

## Setup

### 1. Copy files to the Orange Pi

```bash
sudo mkdir -p /opt/portfolio-dispatch
sudo chown $USER:$USER /opt/portfolio-dispatch
cp dispatch.sh /opt/portfolio-dispatch/
cp crontab.txt /opt/portfolio-dispatch/
cp .env.example /opt/portfolio-dispatch/.env
chmod +x /opt/portfolio-dispatch/dispatch.sh
chmod 600 /opt/portfolio-dispatch/.env
```

### 2. Configure the GitHub token

Create a **Personal Access Token** with `repo` scope:
1. Go to https://github.com/settings/tokens/new?scopes=repo
2. Give it a name like `orangepi-portfolio-dispatch`
3. Set expiration (recommended: no expiration or 1 year)
4. Copy the token

Edit `/opt/portfolio-dispatch/.env`:
```bash
GITHUB_TOKEN=ghp_your_actual_token
GITHUB_REPO=giga89/portfolio-daily-recap
```

### 3. Set timezone to Europe/Rome

```bash
sudo timedatectl set-timezone Europe/Rome
```

### 4. Install the crontab

```bash
crontab /opt/portfolio-dispatch/crontab.txt
# Verify:
crontab -l
```

### 5. Test manually

```bash
# Dry run (check if the script works)
/opt/portfolio-dispatch/dispatch.sh eu_open

# Check logs
cat /opt/portfolio-dispatch/logs/dispatch.log
```

## Files

| File | Description |
|---|---|
| `dispatch.sh` | Main script — calls GitHub API to trigger workflows |
| `crontab.txt` | Crontab configuration with all market schedules |
| `.env.example` | Template for environment variables |

## Logs

All logs are in `/opt/portfolio-dispatch/logs/`:
- `dispatch.log` — Main dispatch log (auto-rotated to last 1000 lines)
- `cron.log` — Raw cron output
- `dispatched_YYYY-MM-DD.txt` — Daily dedup tracking (auto-cleaned after 7 days)

## Features

- ✅ **Precise timing** — cron fires at exact UTC times (no GitHub queue delay)
- ✅ **DST handling** — dual entries cover both summer/winter; dedup prevents double sends
- ✅ **Weekend skip** — market sessions auto-skip on Saturday/Sunday
- ✅ **Deduplication** — same session won't dispatch twice in one day
- ✅ **Logging** — full audit trail with auto-rotation
- ✅ **Fallback** — GitHub cron schedules still exist as backup if Orange Pi is offline
