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

**Event**:
A group of articles from one or more outlets covering the same story, detected by
embedding similarity over `"{title}. {lead}"` and stored as `articles.event_id`.
Derived, not allocated: the id is the seed article's id, so the same corpus
reclusters to the same ids. Recomputed whole-corpus on every ingestion run, so an
article can leave an event.
_Avoid_: Story, cluster (both used loosely for the lexical baseline this replaced)

**Passage**:
The exact text that gets embedded: the title, then the first 400 characters of the
body. Never the title alone — the similarity threshold is calibrated on this
string, and titles alone collapse it. One definition, in
`src.analysis.embeddings.passage_text`.

**Lexical grouping**:
The superseded event detection: title-token Jaccard ≥ 0.34 within a category and
a 72-hour window. Retained only as the fallback for a database with no embeddings
yet, chosen per corpus and never per article. See `docs/adr/0005`.

**Framing**:
The structural variables of how a story is told, extracted per article by
`src.nlp.framing`: who is named as the actor, to whom responsibility is
attributed, active or passive voice, whose point of view the lead opens from,
and any evaluative terms in the headline. Structural, not evaluative — two
articles can share a bias label and a sentiment and still differ here.
_Avoid_: Bias, slant (both are `bias_label`, a different column and a different
question)

**Grounding**:
The deterministic string check every extracted framing value passes before it is
stored: the value must occur in the same 500 characters the model was shown.
Extraction and verification share one constant so the two windows cannot drift.
Both errors it makes put less on the screen rather than more.
_Avoid_: Validation, fact-check (it verifies presence in the text, not truth)

**Within-event deviation**:
An outlet's distance from the median of one event on a given metric, and the
only per-outlet comparison that is about coverage rather than story selection.
Each outlet contributes one version per event — its most-commented article — so
a prolific outlet cannot become the median it is measured against.
_Avoid_: Source average, outlet bias score (a raw per-source mean measures which
stories that outlet covers)
