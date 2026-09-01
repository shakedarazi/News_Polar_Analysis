#!/usr/bin/env bash
# Scheduled ingestion wrapper — called by GitHub Actions every 6 hours.
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

# Display-only enrichment. Failure is logged and never fails the ingestion run,
# so OpenAI/OpenRouter latency or errors cannot block polarity analysis.
run_bonus_step() {
  if ! "$@"; then
    echo "BONUS STEP FAILED (ignored): $*"
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
  echo "=== Crawl finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Article-text analysis backfill (no age/comments gate): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  # Safety net, not the primary path: new crawls already get this immediately
  # (crawl.py -> BaseCrawler.crawl -> maybe_analyze_windows_after_save). This
  # just catches any article that slipped through without it (a per-article
  # failure there is swallowed as a warning so it never fails the crawl itself).
  run_step python "$ROOT/pipeline/analyze_articles.py" --windows-only
  echo "=== Article-text analysis backfill finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Comment fetch started (articles >= 24h old, once per article): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  # Caps keep Playwright-heavy Haaretz (and a comment backlog) from eating the
  # GitHub Actions time budget before polarity analysis can run.
  run_step python "$ROOT/pipeline/fetch_comments.py" --min-age-hours 24 --delay 1.5 --limit 80 --max-minutes 25 --haaretz-limit 10
  echo "=== Comment fetch finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Polarity analysis started (articles >= 24h, pending/stale): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  run_step python "$ROOT/pipeline/build_lexicon.py"
  run_step python "$ROOT/pipeline/analyze_articles.py" --min-age-hours 24 --include-stale --require-comments-fetched
  echo "=== Polarity analysis finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Research-lexicon rescore (bonus, version drift only): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  # Articles analyzed in the step above already carry both readings - save_analysis
  # writes them together. This exists only for the other case: someone edits
  # data/lexicon/polarization.csv, the lexicon version changes, and the
  # already-scored corpus is now on an older version. The gate is
  # `polarization_lexicon_version IS DISTINCT FROM` the current one, so this is a
  # no-op on every run where the lexicon did not change. The limit caps how much
  # of a rescore any single run absorbs; the remainder is picked up 6 hours later,
  # because the gate does not clear until a row is actually rewritten.
  run_bonus_step python "$ROOT/pipeline/analyze_articles.py" --polarization-only --limit 200
  echo "=== Research-lexicon rescore finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Embeddings and event clustering (bonus): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  # Embeds articles crawled this run, then reclusters the whole corpus into
  # events. A bonus step because it needs sentence-transformers, which only the
  # GitHub Actions job installs (requirements-embed.txt) - run locally without
  # it, this fails on the import and the run carries on. When no embedding has
  # ever succeeded, event detection falls back to the lexical grouping, so the
  # events page degrades rather than emptying.
  #
  # Reclustering is whole-corpus, not incremental: it is a 1.4k-square
  # similarity matrix, under a second, and recomputing avoids having to decide
  # what happens when a new article should have merged two existing events.
  run_bonus_step python "$ROOT/pipeline/embed_articles.py"
  echo "=== Embeddings finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Retrieval chunks for the assistant (bonus): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  # Splits new articles into passages and embeds them, so the assistant can
  # search the text of the corpus rather than substring-match its titles.
  #
  # Deliberately after the event embeddings and separate from them: these are a
  # different model in a different vector space for a different job, and unlike
  # those, they come over HTTP rather than from a local checkpoint - which is
  # what lets the API embed a visitor's question with the same model.
  #
  # A bonus step, and internally split again: the chunking half needs no key
  # and always runs, so a missing OPENAI_EMBEDDING_API_KEY costs the semantic
  # half of retrieval and leaves the lexical half working.
  run_bonus_step python "$ROOT/pipeline/embed_chunks.py"
  echo "=== Retrieval chunks finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo ""
  echo "=== Classification started (bonus, leftover time only): $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  run_bonus_step python "$ROOT/pipeline/classify_articles.py" --limit 80 --max-minutes 10
  echo "=== Classification finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  exit "$STEP_FAILED"
} 2>&1 | tee -a "$LOG_FILE" || INGESTION_STATUS=1

# Keep last 50 log files (macOS-compatible)
if ls "$LOG_DIR"/ingestion_*.log >/dev/null 2>&1; then
  ls -1t "$LOG_DIR"/ingestion_*.log | tail -n +51 | while read -r old_log; do
    rm -f "$old_log"
  done
fi

exit "$INGESTION_STATUS"
