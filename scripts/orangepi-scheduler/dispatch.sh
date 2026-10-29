#!/bin/bash
# ============================================================================
# Portfolio Daily Recap — GitHub Workflow Dispatcher
# Runs on Orange Pi 5 as a local cron scheduler
# Triggers GitHub Actions workflow via repository_dispatch API
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
ENV_FILE="$SCRIPT_DIR/.env"

# Create log directory
mkdir -p "$LOG_DIR"

# Load configuration
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Create it with GITHUB_TOKEN and GITHUB_REPO." >&2
    exit 1
fi
source "$ENV_FILE"

# Validate required vars
: "${GITHUB_TOKEN:?ERROR: GITHUB_TOKEN not set in .env}"
: "${GITHUB_REPO:?ERROR: GITHUB_REPO not set in .env}"

# Session name from argument
SESSION="${1:-}"
FORCE_FLAG="${2:-}"
if [ -z "$SESSION" ]; then
    echo "Usage: $0 <eu_open|community_poll|stock_focus|us_open|stock_news|crypto_recap|us_close|weekly_sat|weekly_sun|monthly> [--force]" >&2
    exit 1
fi

FORCE="false"
if [ "$FORCE_FLAG" = "--force" ]; then
    FORCE="true"
fi

# Map session argument to workflow session name
case "$SESSION" in
    eu_open)               SESSION_NAME="European market open" ;;
    community_poll)        SESSION_NAME="Community Poll" ;;
    stock_focus)           SESSION_NAME="Stock focus" ;;
    us_open)               SESSION_NAME="U.S. market open" ;;
    stock_news)            SESSION_NAME="Stock News Monitor" ;;
    crypto_recap)          SESSION_NAME="Daily crypto recap" ;;
    us_close)              SESSION_NAME="U.S. market close" ;;
    weekly_sat)            SESSION_NAME="Weekly recap (Sat)" ;;
    weekly_sun)            SESSION_NAME="Weekly recap (Sun)" ;;
    monthly)               SESSION_NAME="Monthly recap" ;;
    copy_trading)          SESSION_NAME="Copy trading post" ;;
    dividend_post)         SESSION_NAME="Dividend Announcement" ;;
    dashboard_sync)        SESSION_NAME="Daily Dashboard Sync" ;;
    event_monitor)         SESSION_NAME="Event Monitor (Earnings & Dividends)" ;;
    *)

        echo "ERROR: Unknown session '$SESSION'" >&2
        exit 1
        ;;
esac

# Check if today is a weekday (for market sessions)
DOW=$(date -u +%u)  # 1=Mon, 7=Sun
if [[ "$SESSION" =~ ^(eu_open|community_poll|stock_focus|us_open|stock_news|us_close)$ ]] && [ "$DOW" -gt 5 ]; then
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') SKIP $SESSION — weekend (day $DOW)" >> "$LOG_DIR/dispatch.log"
    exit 0
fi

# On the last day of the month, us_close is skipped because monthly recap handles the close
if [ "$SESSION" = "us_close" ]; then
    TOMORROW=$(date -u -d "+1 day" +%d)
    if [ "$TOMORROW" = "01" ]; then
        echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') SKIP us_close — last day of the month (handled by monthly recap)" >> "$LOG_DIR/dispatch.log"
        exit 0
    fi
fi

# ---------------------------------------------------------------------------
# Market Hour Protection Guards:
# Ensure market sessions only trigger when the respective exchanges are
# actually open/closed, preventing premature triggers during DST transitions
# or timezone mismatches.
# ---------------------------------------------------------------------------
if [ "$FORCE" != "true" ]; then
    if [ "$SESSION" = "eu_open" ]; then
        EU_TIME=$(TZ=Europe/Rome date +%H%M)
        if [[ "$EU_TIME" < "0900" || "$EU_TIME" > "1030" ]]; then
            echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') SKIP eu_open — Rome time is $EU_TIME, market not open (waiting for 09:00 CET/CEST)" >> "$LOG_DIR/dispatch.log"
            exit 0
        fi
    elif [ "$SESSION" = "us_open" ]; then
        NY_TIME=$(TZ=America/New_York date +%H%M)
        if [[ "$NY_TIME" < "0930" || "$NY_TIME" > "1100" ]]; then
            echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') SKIP us_open — New York time is $NY_TIME, market not open (waiting for 09:30 ET)" >> "$LOG_DIR/dispatch.log"
            exit 0
        fi
    elif [ "$SESSION" = "us_close" ] || [ "$SESSION" = "monthly" ]; then
        NY_TIME=$(TZ=America/New_York date +%H%M)
        if [[ "$NY_TIME" < "1600" || "$NY_TIME" > "1800" ]]; then
            echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') SKIP $SESSION — New York time is $NY_TIME, market not closed (waiting for 16:00 ET)" >> "$LOG_DIR/dispatch.log"
            exit 0
        fi
    elif [ "$SESSION" = "event_monitor" ]; then
        # If triggered in the afternoon window (>= 14:00 ITA), ensure US market has been open for at least 30 mins (NY time >= 10:00 ET)
        CURRENT_ITA_HOUR=$(TZ=Europe/Rome date +%H)
        if [ "$CURRENT_ITA_HOUR" -ge 14 ]; then
            NY_TIME=$(TZ=America/New_York date +%H%M)
            if [[ "$NY_TIME" < "1000" || "$NY_TIME" > "1200" ]]; then
                echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') SKIP event_monitor (US Window) — New York time is $NY_TIME, waiting for >= 10:00 ET" >> "$LOG_DIR/dispatch.log"
                exit 0
            fi
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Dedup: prevent duplicate dispatches for the same session on the same day.
# - stock_news runs 3x daily (morning, afternoon, evening); deduplicates by hour bucket.
# - event_monitor runs 2x daily (European morning & post-US-open); deduplicates by window bucket.
# - all other sessions run once daily; deduplicates strictly once per day.
# ---------------------------------------------------------------------------
TODAY=$(date -u +%Y-%m-%d)
CURRENT_HOUR=$(date -u +%H)
if [ "$SESSION" = "stock_news" ]; then
    DEDUP_KEY="stock_news:${CURRENT_HOUR}"
elif [ "$SESSION" = "event_monitor" ]; then
    CURRENT_ITA_HOUR=$(TZ=Europe/Rome date +%H)
    if [ "$CURRENT_ITA_HOUR" -ge 14 ]; then
        DEDUP_KEY="event_monitor:us_open_window"
    else
        DEDUP_KEY="event_monitor:eu_morning_window"
    fi
else
    DEDUP_KEY="${SESSION}"
fi
DEDUP_FILE="$LOG_DIR/dispatched_${TODAY}.txt"

if [ "$FORCE" != "true" ] && grep -qF "$DEDUP_KEY" "$DEDUP_FILE" 2>/dev/null; then
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') DEDUP $SESSION — already dispatched today" >> "$LOG_DIR/dispatch.log"
    exit 0
fi

# Dispatch to GitHub
echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') DISPATCH $SESSION ($SESSION_NAME)..." >> "$LOG_DIR/dispatch.log"

HTTP_CODE=$(curl -s -o /tmp/dispatch_response.json -w "%{http_code}" \
    -X POST \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/$GITHUB_REPO/dispatches" \
    -d "{\"event_type\":\"$SESSION\",\"client_payload\":{\"session\":\"$SESSION_NAME\",\"triggered_by\":\"orangepi5\",\"timestamp\":\"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\"}}")

if [ "$HTTP_CODE" = "204" ]; then
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') SUCCESS $SESSION — HTTP $HTTP_CODE" >> "$LOG_DIR/dispatch.log"
    echo "$DEDUP_KEY" >> "$DEDUP_FILE"
else
    RESPONSE=$(cat /tmp/dispatch_response.json 2>/dev/null || echo "no response body")
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') FAIL $SESSION — HTTP $HTTP_CODE — $RESPONSE" >> "$LOG_DIR/dispatch.log"
    exit 1
fi

# Cleanup old dedup files (keep last 7 days)
find "$LOG_DIR" -name "dispatched_*.txt" -mtime +7 -delete 2>/dev/null || true

# Rotate main log (keep last 1000 lines)
if [ -f "$LOG_DIR/dispatch.log" ]; then
    tail -n 1000 "$LOG_DIR/dispatch.log" > "$LOG_DIR/dispatch.log.tmp" && mv "$LOG_DIR/dispatch.log.tmp" "$LOG_DIR/dispatch.log"
fi
