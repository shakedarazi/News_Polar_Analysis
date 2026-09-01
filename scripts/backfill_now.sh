#!/usr/bin/env bash
# Manual, uncapped backfill — the same pipeline steps as run_ingestion.sh, run
# on demand from a developer machine instead of on the 6-hourly GitHub Actions
# schedule.
#
# Why this exists separately rather than as flags on run_ingestion.sh: the
# scheduled job is deliberately conservative. It caps comment fetching (--limit
# 80, --max-minutes 25) and classification (--limit 80, --max-minutes 10) so a
# backlog can never eat the runner's time budget before polarity analysis gets
# to run, and it gates comments at 24h so a comment thread has time to fill up.
# Those caps are right for an unattended timer and wrong for "I need the corpus
# as complete as it can be, now". Keeping them in two files means loosening one
# cannot silently loosen the other.
#
# Safe to re-run and safe to interrupt. Every write commits per article
# (src/db/connection.py opens a connection, commits and closes per call), so a
# Ctrl-C loses at most the article in flight. Comment inserts are
# ON CONFLICT (comment_id) DO NOTHING, so re-fetching an article adds only the
# comments that appeared since — it never duplicates and never removes.
#
# That last property is what makes an early fetch cheap: fetching comments
# before a thread has filled up is not a decision you are stuck with. Re-run
# later with --force to top the same articles up.
#
# Usage:
#   scripts/backfill_now.sh                    # age gate 2h, no caps
#   scripts/backfill_now.sh --min-age-hours 24 # only mature articles
#   scripts/backfill_now.sh --force            # re-fetch comments already fetched
#   scripts/backfill_now.sh --skip-crawl       # DB work only, no network crawl

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MIN_AGE_HOURS=2
FORCE_COMMENTS=0
SKIP_CRAWL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --min-age-hours) MIN_AGE_HOURS="$2"; shift 2 ;;
    --force) FORCE_COMMENTS=1; shift ;;
    --skip-crawl) SKIP_CRAWL=1; shift ;;
    -h|--help) sed -n '1,30p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

LOG_DIR="$ROOT/logs/ingestion"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/backfill_$(date +%Y%m%d_%H%M%S).log"

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

# Same contract as run_ingestion.sh: a failing step is recorded but does not
# abort the remaining steps, so one dead source cannot cost you the analysis.
STEP_FAILED=0
run_step() {
  if ! "$@"; then
    echo "STEP FAILED: $*"
    STEP_FAILED=1
  fi
}

# Sources whose comment IDs come from the site's own API (item["id"]), so the
# same comment keeps the same comment_id across fetches. For these,
# ON CONFLICT (comment_id) DO NOTHING makes a re-fetch a clean top-up: new
# comments are added, existing ones untouched.
STABLE_ID_SOURCES=(ynet mako channel14)

# Haaretz is deliberately not in that list. src/crawling/comments/haaretz.py
# derives source_comment_id from the comment's *rank* on the page, because the
# rendered DOM exposes no stable id. Rank shifts as new comments arrive, so a
# second fetch would map old ids onto different comments: DO NOTHING would skip
# ranks it has already seen while inserting shifted copies of the rest. That is
# corruption, not enrichment.
#
# So Haaretz gets exactly one fetch, at full maturity, and never --force. The
# only cost is that its comments arrive on the normal 24h schedule.
HAARETZ_MIN_AGE_HOURS=24

{
  echo "=== Manual backfill started: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo "    min article age: ${MIN_AGE_HOURS}h | force re-fetch: ${FORCE_COMMENTS} | skip crawl: ${SKIP_CRAWL}"
  echo ""

  if [[ "$SKIP_CRAWL" -eq 0 ]]; then
    run_step python "$ROOT/pipeline/crawl.py" --source all --delay 2.0
    echo "=== Crawl finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
    echo ""
  fi

  # Article-text (dominance) analysis has no comment dependency, so it can run
  # for everything regardless of age. New crawls already get this inline; this
  # catches anything that slipped through.
  run_step python "$ROOT/pipeline/analyze_articles.py" --windows-only
  echo "=== Window backfill finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""

  # No --limit and no --max-minutes: unlike the scheduled job there is no
  # runner clock to protect, and a partial fetch just means running this again.
  for src in "${STABLE_ID_SOURCES[@]}"; do
    args=(--source "$src" --min-age-hours "$MIN_AGE_HOURS" --delay 1.5)
    if [[ "$FORCE_COMMENTS" -eq 1 ]]; then
      args+=(--force)
    fi
    run_step python "$ROOT/pipeline/fetch_comments.py" "${args[@]}"
  done

  # Never early, never forced — see the STABLE_ID_SOURCES comment above.
  run_step python "$ROOT/pipeline/fetch_comments.py" \
    --source haaretz --min-age-hours "$HAARETZ_MIN_AGE_HOURS" --delay 1.5

  echo "=== Comment fetch finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""

  run_step python "$ROOT/pipeline/build_lexicon.py"
  # --include-stale is what makes a top-up fetch actually show up in the
  # results: it re-analyzes any article whose comments arrived after its last
  # analysis. Without it, a --force re-fetch would write comments that no
  # aggregate ever reads.
  run_step python "$ROOT/pipeline/analyze_articles.py" \
    --min-age-hours "$MIN_AGE_HOURS" --include-stale --require-comments-fetched
  echo "=== Polarity analysis finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""

  # Classification needs the OpenRouter key, which normally only exists as a
  # GitHub secret — src/nlp/openai_config.py deliberately has no fallback to
  # the user-facing OPENAI_API_KEY, so that ingestion volume can never be
  # billed to the key serving summary/bias/Q&A. Skip rather than fail when the
  # key is absent; the scheduled run will pick these articles up.
  if [[ -n "${OPENAI_INGESTION_API_KEY:-}" ]]; then
    run_step python "$ROOT/pipeline/classify_articles.py" --delay 1.0
    echo "=== Classification finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  else
    echo "=== Classification skipped: OPENAI_INGESTION_API_KEY not set locally ==="
    echo "    The 6-hourly GitHub Actions run has the key and will classify these."
  fi

  echo ""
  echo "=== Manual backfill finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) (step failures: $STEP_FAILED) ==="
  exit "$STEP_FAILED"
} 2>&1 | tee -a "$LOG_FILE"
