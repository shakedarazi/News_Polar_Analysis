#!/usr/bin/env bash
# Scheduled ingestion wrapper — called by cron or Airflow every 6 hours.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs/ingestion"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/ingestion_$(date +%Y%m%d_%H%M%S).log"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
else
  echo "ERROR: .venv not found. Run: python3 -m venv .venv && pip install -r requirements.txt" | tee -a "$LOG_FILE"
  exit 1
fi

# Runs one pipeline step without letting `set -e` abort the script on
# failure — the step's own exit status is captured and folded into the
# script's final exit code, but every other step still gets a chance to run.
run_step() {
  if ! "$@"; then
    echo "STEP FAILED: $*"
    STEP_FAILED=1
  fi
}

# The block below runs in a subshell (it's the left side of a pipe), so its
# own exit status - not any variable it sets - is what reaches the parent
# script; it exits with STEP_FAILED explicitly so that status survives.
INGESTION_STATUS=0
STEP_FAILED=0
{
  echo "=== Ingestion run started: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  run_step python "$ROOT/pipeline/crawl.py" --source all --delay 2.0
  echo "=== Ingestion run finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Article-text analysis backfill (no age/comments gate): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  # Safety net, not the primary path: new crawls already get this immediately
  # (crawl.py -> BaseCrawler.crawl -> maybe_analyze_windows_after_save). This
  # just catches any article that slipped through without it (a per-article
  # failure there is swallowed as a warning so it never fails the crawl itself).
  run_step python "$ROOT/pipeline/analyze_articles.py" --windows-only
  echo "=== Article-text analysis backfill finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Classification started: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  run_step python "$ROOT/pipeline/classify_articles.py" --limit 200
  echo "=== Classification finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Comment fetch started (articles >= 24h old, once per article): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  run_step python "$ROOT/pipeline/fetch_comments.py" --min-age-hours 24 --delay 1.5
  echo "=== Comment fetch finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Polarity analysis started (articles >= 24h, pending/stale): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  run_step python "$ROOT/pipeline/build_lexicon.py"
  run_step python "$ROOT/pipeline/analyze_articles.py" --min-age-hours 24 --include-stale --require-comments-fetched
  echo "=== Polarity analysis finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  exit "$STEP_FAILED"
} 2>&1 | tee -a "$LOG_FILE" || INGESTION_STATUS=1

# Keep last 50 log files (macOS-compatible)
if ls "$LOG_DIR"/ingestion_*.log >/dev/null 2>&1; then
  ls -1t "$LOG_DIR"/ingestion_*.log | tail -n +51 | while read -r old_log; do
    rm -f "$old_log"
  done
fi

exit "$INGESTION_STATUS"
