---
status: accepted
---

# Protect polarity analysis from classification and comment-fetch backlog

Scheduled ingestion was failing or hitting the GitHub Actions 45-minute timeout because two
non-critical steps sat on the critical path:

- `classify_articles.py` ran immediately after crawl, so OpenRouter latency could consume the
  time budget before comments and analyze ran.
- `fetch_comments.py` had no batch cap. Haaretz launches Chromium per article; a missing comments
  button raised, left `comments_fetched_at` unset, and the same articles were retried forever.

Polarity analysis (`analyze_articles.py`) is the product. Category labels are display-only bonus.

We decided:

1. Reorder `scripts/run_ingestion.sh` to crawl → windows backfill → comments → lexicon → analyze,
   then classify last.
2. Run classify via `run_bonus_step` so its exit code never fails the ingestion run, and cap it
   (`--limit 80 --max-minutes 10`).
3. Cap comment fetch (`--limit 80 --max-minutes 25 --haaretz-limit 10`), round-robin across
   sources, and treat permanent per-article failures (HTTP 4xx, extraction `ValueError`, Haaretz
   page loaded with no comments UI) as fetched-with-zero-comments so analyze can proceed.
4. Raise the workflow `timeout-minutes` to 60 as a safety margin, not as the primary bound.

Per-article failures in comments/analyze no longer fail the step when any work progressed (same
rule crawl already used). Transient failures still leave `comments_fetched_at` unset and retry
next run.

This extends [[0002-decouple-classification-from-crawl]] (classify stays out of the crawl loop)
and [[0001-parallel-source-crawl-with-retry-and-run-observability]] (step isolation + partial
success). It does not change the lexicon formulas or article identity.
