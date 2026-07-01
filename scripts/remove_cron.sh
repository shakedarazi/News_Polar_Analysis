#!/usr/bin/env bash
# Remove the scheduled ingestion cron job.
set -euo pipefail

MARKER="# news-polar-ingestion"

if crontab -l 2>/dev/null | grep -q "$MARKER"; then
  crontab -l 2>/dev/null | grep -v "$MARKER" | crontab -
  echo "Cron job removed."
else
  echo "No news-polar ingestion cron job found."
fi
