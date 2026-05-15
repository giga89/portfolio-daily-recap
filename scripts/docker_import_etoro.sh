#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# docker_import_etoro.sh
#
# Runs the eToro history import inside the portfolio-recap Docker container.
# Usage:
#   ./scripts/docker_import_etoro.sh [path/to/etoro-account-statement.xlsx]
#
# Required environment variables (export them before running, or edit below):
#   GIST_ACCESS_TOKEN  — GitHub personal access token with 'gist' scope
#   GIST_ID            — ID of your portfolio Gist (e.g. abc123def456...)
#
# Optional (Telegram confirmation after import):
#   TELEGRAM_BOT_TOKEN
#   TELEGRAM_CHAT_ID
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ── 1. Determine xlsx file ────────────────────────────────────────────────────
if [[ $# -ge 1 ]]; then
    XLSX_PATH="$1"
else
    # Auto-detect the most recent statement in the project root
    XLSX_PATH=$(ls -t "$PROJECT_DIR"/etoro-account-statement*.xlsx 2>/dev/null | head -1)
    if [[ -z "$XLSX_PATH" ]]; then
        echo "❌ No eToro xlsx file found."
        echo "   Place the file in $PROJECT_DIR or pass the path as an argument."
        exit 1
    fi
fi

XLSX_ABS=$(realpath "$XLSX_PATH")
XLSX_BASENAME=$(basename "$XLSX_ABS")

echo "📂 Using: $XLSX_ABS"

# ── 2. Check required env vars ───────────────────────────────────────────────
if [[ -z "${GIST_ACCESS_TOKEN:-}" && -z "${GITHUB_GIST_TOKEN:-}" ]]; then
    echo ""
    echo "❌ Missing GIST_ACCESS_TOKEN (or GITHUB_GIST_TOKEN)."
    echo ""
    echo "   Export it before running:"
    echo "     export GIST_ACCESS_TOKEN=ghp_your_token_here"
    echo "     export GIST_ID=your_gist_id_here"
    echo "     ./scripts/docker_import_etoro.sh"
    echo ""
    exit 1
fi

# ── 3. Build env flags for docker run ────────────────────────────────────────
ENV_FLAGS=()
for VAR in \
    GIST_ACCESS_TOKEN GITHUB_GIST_TOKEN GITHUB_TOKEN \
    GIST_ID \
    TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID; do
    if [[ -n "${!VAR:-}" ]]; then
        ENV_FLAGS+=("-e" "${VAR}=${!VAR}")
    fi
done

# ── 4. Ensure image is built ──────────────────────────────────────────────────
echo "🐳 Checking Docker image..."
if ! docker image inspect portfolio-recap > /dev/null 2>&1; then
    echo "   Building portfolio-recap image..."
    docker build -t portfolio-recap "$PROJECT_DIR" > /tmp/portfolio_build.log 2>&1
    echo "   ✅ Build complete."
fi

# ── 5. Run import inside container ───────────────────────────────────────────
echo "🚀 Running import inside Docker..."
echo ""

docker run --rm \
    "${ENV_FLAGS[@]}" \
    -v "$PROJECT_DIR/output:/app/output" \
    -v "${XLSX_ABS}:/app/${XLSX_BASENAME}:ro" \
    portfolio-recap \
    python scripts/import_etoro_history.py "${XLSX_BASENAME}"

echo ""
echo "✅ Done."
