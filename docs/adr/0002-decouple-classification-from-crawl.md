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
`classify_articles.py` as its own step in `scripts/run_ingestion.sh`. The `--limit` cap exists so that
a backlog built up during downtime doesn't turn a single run into an unbounded burst of OpenAI
calls — any remainder is picked up by the next run 6 hours later.

Later we moved that step to *after* polarity analysis and made it best-effort, because classify
sitting before comments/analyze could starve the product path. See
[[0003-protect-analyze-from-classify-and-comment-backlog]].
