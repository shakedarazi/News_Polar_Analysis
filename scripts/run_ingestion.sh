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

{
  echo "=== Ingestion run started: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  crawl_status=0
  python "$ROOT/pipeline/crawl.py" --source all --delay 2.0 || crawl_status=$?
  echo "=== Ingestion run finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Comment fetch started (articles >= 24h old, once per article): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  # A handful of per-article failures (e.g. a source rate-limiting near the
  # end of the run) is routine and must not skip analysis for every article
  # that DID fetch successfully — so this is intentionally not `set -e`'d
  # like the rest of the script. The partial-failure exit code is still
  # captured and surfaces as an overall run failure below (via `pipefail`),
  # so monitoring still sees it — analysis just isn't held hostage by it.
  fetch_status=0
  python "$ROOT/pipeline/fetch_comments.py" --min-age-hours 24 --delay 1.5 || fetch_status=$?
  echo "=== Comment fetch finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Polarity analysis started (articles >= 24h, pending/stale): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  python "$ROOT/pipeline/build_lexicon.py"
  analyze_status=0
  python "$ROOT/pipeline/analyze_articles.py" --min-age-hours 24 --include-stale --require-comments-fetched || analyze_status=$?
  echo "=== Polarity analysis finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

  if [[ $crawl_status -ne 0 || $fetch_status -ne 0 || $analyze_status -ne 0 ]]; then
    echo "=== Ingestion run completed with partial failures (crawl=$crawl_status fetch=$fetch_status analyze=$analyze_status) — see per-article FAILED lines above ==="
    exit 1
  fi
} 2>&1 | tee -a "$LOG_FILE"

# Keep last 50 log files (macOS-compatible)
if ls "$LOG_DIR"/ingestion_*.log >/dev/null 2>&1; then
  ls -1t "$LOG_DIR"/ingestion_*.log | tail -n +51 | while read -r old_log; do
    rm -f "$old_log"
  done
fi
