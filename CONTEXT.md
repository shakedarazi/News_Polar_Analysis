# News Polar Analysis

Batch pipeline that crawls Israeli news sites and analyzes audience comment polarity. This glossary covers vocabulary for the batch ingestion (crawl) layer specifically.

## Language

**Ingestion run**:
One execution of the scheduled batch pipeline (crawl → fetch comments → analyze, then optional classify), identified by a single `run_id`. A run is composed of one sub-execution per source, which may execute in parallel; each sub-execution is tracked as its own row keyed by `(run_id, source)`.
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

**Category lexicon**:
The seven topic word lists in `data/lexicon_base/` (329 lemmas), matched against **article** text to produce per-window category counts and `dominance`. Measures what an article is about, never how heated it is — a window can be fully political and perfectly calm.
_Avoid_: The lexicon, word bank (ambiguous — two other lexicons exist and both score comments)

**Comment polarity lexicon**:
`data/comment_lexicon_base/polar_words.txt` (182 lemmas), single-axis, matched against **comment** text to produce `polar_ratio` and, aggregated, `audience_mean`. The list the pipeline has always scored on.
_Avoid_: Polar words (collides with the research lexicon, which is also polarity and also comments)

**Research polarization lexicon**:
`data/lexicon/polarization.csv` (191 lemmas), the Hebrew adaptation of Simchon, Brady & Van Bavel (2022), matched against **comment** text on two axes — `issue` (what the argument is about) and `affective` (hostility toward the other side). Stored beside the single-axis score, never blended with it: the two share only 15% of their expanded forms. See `docs/adr/0004`.
_Avoid_: The Simchon lexicon (fine in conversation, but the column names say `issue`/`affective`)

**Issue / affective**:
The two axes of the research polarization lexicon, and the only two values its component column takes. `issue` is topic-partisan vocabulary; `affective` is hostility toward the other camp. A comment can score on both, one, or neither.
_Avoid_: Ideological/emotional polarization (the paper's axes are lexical, not psychological states)
