#!/usr/bin/env bash
# Install cron job: run ingestion every 6 hours.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_SCRIPT="$ROOT/scripts/run_ingestion.sh"
MARKER="# news-polar-ingestion"

chmod +x "$RUN_SCRIPT"

CRON_LINE="0 */6 * * * $RUN_SCRIPT $MARKER"

# Remove old entry if exists, then append new one
(crontab -l 2>/dev/null | grep -v "$MARKER" || true; echo "$CRON_LINE") | crontab -

echo "Cron job installed."
echo "Schedule: every 6 hours (at :00 — 00:00, 06:00, 12:00, 18:00)"
echo "Command:  $RUN_SCRIPT"
echo ""
echo "Verify with:  crontab -l"
echo "Remove with:  bash $ROOT/scripts/remove_cron.sh"
echo "Logs:         $ROOT/logs/ingestion/"
