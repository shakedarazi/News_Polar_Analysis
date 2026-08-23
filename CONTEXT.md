# News Polar Analysis

Batch pipeline that crawls Israeli news sites and analyzes audience comment polarity. This glossary covers vocabulary for the batch ingestion (crawl) layer specifically.

## Language

**Ingestion run**:
One execution of the scheduled batch pipeline (crawl → classify → fetch comments → analyze), identified by a single `run_id`. A run is composed of one sub-execution per source, which may execute in parallel; each sub-execution is tracked as its own row keyed by `(run_id, source)`.
_Avoid_: Batch, job (too generic — use "ingestion run" for the whole pipeline execution)

**Source crash**:
An entire source's crawl sub-execution failing outright (e.g., all of a source's RSS feeds unreachable), before any per-article processing could happen. Logged and does not abort the ingestion run — other sources still run.
_Avoid_: Source failure, source error

**Article failure**:
A single article failing to fetch, extract, or save (e.g. HTTP error, or extracted text under the minimum length). Logged and skipped; does not abort its source's crawl.
_Avoid_: Fetch error (too narrow — covers extraction and save failures too)

**Transient failure**:
An article/feed fetch failure classified as likely temporary (timeout, connection error, HTTP 5xx) — eligible for retry with backoff.
_Avoid_: Retryable error

**Permanent failure**:
An article/feed fetch failure classified as not worth retrying (HTTP 4xx, or an article-failure-level extraction problem like too-short text) — recorded immediately as a failure, no retry attempted.
_Avoid_: Non-retryable error, hard failure
