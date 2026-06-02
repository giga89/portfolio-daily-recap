# 🍊 Orange Pi 5 — Local Market Scheduler

Local cron scheduler that triggers GitHub Actions workflows at **precise market times**, bypassing the unreliable GitHub Actions cron queue (which can delay jobs 5–40+ minutes).

## How It Works

```
Orange Pi 5 crontab (precise to the second)
  → dispatch.sh calls GitHub API (repository_dispatch)
    → GitHub Actions workflow starts immediately (no cron queue)
      → Recap generated and sent within ~5–8 min of market event
```

## Schedule (UTC)

Each session has **two cron entries** (summer/winter) to handle the EU/US DST mismatch (~3 weeks/year). The dispatch script deduplicates automatically.

| Session | Trigger (UTC) | Market Time | Italian Time |
|---|---|---|---|
| **EU Open** | 07:02 / 08:02 | 08:02 London | ~09:02 |
| **US Open** | 13:32 / 14:32 | 09:32 New York | ~15:32 |
| **US Close** | 20:02 / 21:02 | 16:02 New York | ~22:02 |
| **Weekly (Sat)** | 08:00 / 09:00 | — | ~10:00 |
| **Weekly (Sun)** | 20:00 / 21:00 | — | ~22:00 |

## Setup

### 1. Copy files to the Orange Pi

```bash
sudo mkdir -p /opt/portfolio-dispatch
sudo chown $USER:$USER /opt/portfolio-dispatch
cp dispatch.sh /opt/portfolio-dispatch/
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

### 3. Set timezone to UTC

```bash
sudo timedatectl set-timezone UTC
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
