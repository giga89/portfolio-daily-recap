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
if [ -z "$SESSION" ]; then
    echo "Usage: $0 <eu_open|community_poll|stock_focus|us_open|stock_news|crypto_recap|us_close|weekly_sat|weekly_sun>" >&2
    exit 1
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

# ---------------------------------------------------------------------------
# Dedup: use SESSION + current hour bucket to avoid blocking scheduled runs
# when a manual test runs earlier in the day.
#
# Each cron fires in a specific UTC-hour window. We record
# "SESSION:HH" so that eu_open at 07 does not block eu_open at 08,
# and a manual us_close at 13 does not block the real us_close at 20.
# ---------------------------------------------------------------------------
TODAY=$(date -u +%Y-%m-%d)
CURRENT_HOUR=$(date -u +%H)
DEDUP_KEY="${SESSION}:${CURRENT_HOUR}"
DEDUP_FILE="$LOG_DIR/dispatched_${TODAY}.txt"

if grep -qF "$DEDUP_KEY" "$DEDUP_FILE" 2>/dev/null; then
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') DEDUP $SESSION (hour $CURRENT_HOUR) — already dispatched today" >> "$LOG_DIR/dispatch.log"
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
