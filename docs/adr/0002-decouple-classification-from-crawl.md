---
status: accepted
---

# Decouple OpenAI classification from the crawl loop

`pipeline/crawl.py` called `maybe_classify_after_save()` synchronously, per article, immediately after each save —
so crawl throughput was bounded by OpenAI response time, and every new article triggered an immediate API call
regardless of how many articles were being processed. `pipeline/classify_articles.py` already existed as an
independent backfill script, but wasn't wired into `scripts/run_ingestion.sh` at all — meaning newly crawled
articles only got categorized if someone ran the backfill manually.

We decided to stop classifying inline during crawl (crawl now only saves articles) and instead run
`classify_articles.py --missing-only --limit 200` as its own step in `run_ingestion.sh`, right after crawl. The
`--limit 200` cap exists so that a backlog built up during downtime (pipeline not running for a while) doesn't
turn a single run into an unbounded burst of OpenAI calls — any remainder is picked up by the next run 6 hours
later. Total classification cost is the same either way; this only changes when the cost is paid and decouples
crawl speed from OpenAI latency.
