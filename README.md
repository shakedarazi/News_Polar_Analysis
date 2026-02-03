📘 RFC – News Analysis Pipeline

Deterministic, Research-Grade, Batch-Oriented (Up to BigQuery)

1️⃣ System Goal

Build a deterministic, stable system that does not depend on the behavior of news websites, which performs:

Collection of news articles from major Israeli news outlets

Collection of audience comments for each article

Lexicon-based textual analysis

Extraction of quantitative metrics over article windows (sentences) and comments

Clean loading into BigQuery for future analytical queries

❗️The system is not streaming and not real-time.
The objective is accuracy, stability, and research validity, not low latency.

2️⃣ Data Sources

The system supports major Israeli news outlets, including:

Haaretz

ynet

mako / Keshet 12

News 12

Reshet 13 (formerly Channel 10)

Channel 14

Additional major news centers with the same structure

❗️Assumption:
There is no reliable way to fetch “all articles of the day” directly from the sites
(feeds are limited, ordering is unstable, content is dynamic).

3️⃣ Design Principles
3.1 Determinism

Same input ⇒ same output

No non-deterministic algorithms in the critical path

Any change to lexicons or algorithms ⇒ new version

3.2 Idempotency

Repeated runs never create duplicates

All BigQuery writes go through staging → MERGE

Every entity is identified by a unique key

3.3 Separation of Concerns

Ingestion is separated from processing

Comments are separated from article text

LLM logic is isolated as optional enrichment

3.4 Batch-Oriented

No streaming is required

Comments are analyzed only after accumulation (24 hours)

4️⃣ High-Level Architecture

The system is built using two Airflow DAGs:

DAG 1 – Ingestion (Every 6 Hours)

Purpose:

“Freeze” articles before the website modifies or removes them.

DAG 2 – Daily Snapshot + Processing (Daily)

Purpose:

Collect accumulated comments and compute stable metrics.

5️⃣ Entity Identification (IDs & Keys)
5.1 canonical_url

URL normalization (remove tracking params, normalize scheme, trailing slash)

5.2 article_id
article_id = sha256(canonical_url)

5.3 Article Windows

Window = sentence

sentence_idx = index after deterministic sentence splitting

Primary key: (article_id, sentence_idx)

5.4 Comments

If a stable comment_id exists from the source — use it

Otherwise:

comment_id = sha256(article_id + text + local_index)


Primary key: (article_id, comment_id)

6️⃣ Text Normalization (Text Processing Spec)
6.1 Normalization (Articles + Comments)

Remove URLs

Remove diacritics

Normalize quotation marks and hyphens

Lowercasing

Remove non-linguistic characters

Whitespace normalization

❗️No semantic modification of the text is performed.

7️⃣ Article Windowing Strategy
Locked Decision

Window = sentence

Sentence splitter is rule-based and deterministic

Split on . ! ? … with heuristics for common abbreviations

Exception

If a sentence contains more than 60 tokens:

It is split into sub-windows of 60 tokens

sentence_idx continues sequentially

Research Rationale

A sentence is a natural rhetorical unit

Enables meaningful category richness and dominance metrics

Chunking prevents statistical outliers

8️⃣ Lexicon Strategy (Locked)
Official Choice – Approach A: Expanded Lexicon
Principle

Tokens are never modified at runtime

Matching is done via an expanded lexicon built offline

lexicon_expanded Contains

Base word

Variants with common Hebrew prefixes:

ה, ו, ב, ל, מ, כ, ש

(Conservative) very common two-prefix combination (e.g., וה)

No variants generated for words shorter than length 3

Versioning

lexicon_base.json

lexicon_expanded.json

lexicon_version = sha256(lexicon_expanded.json)

Same logic applies to comments:

comment_lexicon_expanded

comment_lexicon_version

Future Option (Not Baseline)

Approach B: Conservative prefix stripping

Mentioned only as Future Work

Not enabled in the current pipeline

9️⃣ Article Analysis Algorithm (7 Categories)
Precomputation

Build word2category dictionary

Per Window

counts[7]

active = number of distinct categories

window_len

cat_words = sum(counts)

Dominance
dominance = max(counts) / cat_words


If cat_words == 0 → NULL

Complexity

O(total_tokens_in_article)

🔟 Comment Analysis (Audience Signal)
Comment = Window
Per Comment

polar_count

comment_len

polar_ratio = polar_count / max(1, comment_len)

like_weight = 1 + ln(1 + like_count)

comment_score = polar_ratio

Per-Article Aggregation

num_comments

audience_mean (weighted mean)

audience_p85 (weighted quantile)

❗️No author identity, no timestamp — intentionally (simplicity and cleanliness).

1️⃣1️⃣ GCS Storage
Raw Articles (DAG 1)
gs://bucket/raw/articles/source=.../dt=YYYY-MM-DD/article_id=.../article.json

Snapshot With Comments (DAG 2)
gs://bucket/snapshot/articles_with_comments/source=.../dt=YYYY-MM-DD/article_id=.../article_with_comments.json


Comments are sorted by comment_id → determinism.

1️⃣2️⃣ Staging Format
Locked Decision

Parquet

Rationale

Strong schema enforcement

Columnar format

Efficient BigQuery loading

Reduced data corruption risk

1️⃣3️⃣ BigQuery Target Tables

articles

windows_features

comments_features

article_comments_agg

article_llm_enrichment (optional)

All loads:

staging → MERGE

Based on unique keys

1️⃣4️⃣ Airflow DAGs
DAG 1 – crawl_latest_to_gcs

Schedule: every 6 hours

Role: article ingestion and freezing

DAG 2 – daily_snapshot_process_to_bq

Schedule: daily

Selects articles where now - first_seen_at >= 24h

Fetches comments

Computes features

Loads into BigQuery

Concurrency:

Article-level only (worker pool)

1️⃣5️⃣ Data Quality Rules (DQ)

window_len > 0

sum(c1..c7) ≤ window_len

dominance ∈ [0,1] OR NULL

polar_ratio ∈ [0,1]

num_comments ≤ 200 (warning)

1️⃣6️⃣ LLM – Optional Only

Not in the critical path

Separate enrichment

Full versioning

Does not affect the 7 deterministic metrics

📕 Appendix A – Concurrency, Staging & Algorithmic Specification

(Mandatory extension to the main RFC)

A️⃣ Concurrency Model
Core Principle

Concurrency is strictly limited to the article level.

There is:

No concurrency within an article

No concurrency within a window

No concurrency within comments

Why This Is Critical

Guarantees full determinism

Prevents race conditions

Prevents order-dependent computation effects

Enables formal algorithmic reasoning

Execution Model
Atomic Unit
ArticleJob(article_id)


Each ArticleJob performs:

Article processing → windows

Comment processing → comment scores

Per-article aggregation

Write to GCS staging

Worker Pool

Airflow manages a worker pool

Each worker:

Receives one article_id

Processes it end-to-end

Shares no state with other workers

Big-O with Concurrency

Algorithmic:

O(sum(tokens_articles) + sum(tokens_comments))


Concurrency:

Constant wall-clock speedup only

No asymptotic complexity change

Academic note:

“Parallelism improves wall-clock time but not asymptotic complexity.”

B️⃣ Pipeline Split (Two Logical Paths)
Why Split Is Mandatory

Because:

Articles are structured text

Comments are audience signals

Their lifecycles differ

Their algorithms differ

Thus, there are two logical pipelines, converging only at the article level.

C️⃣ Staging – Full Specification by Pipeline
C1️⃣ Article Staging (Article → Windows)
Input

article_with_comments.json
(only the text field is used here)

Algorithm (Formal)
Data Structures
counts: int[7]
active_categories: int
present_mask: int (bitmask)

Pseudocode
for sentence in split_to_sentences(article_text):
    tokens = tokenize(sentence)

    if len(tokens) > 60:
        chunks = chunk(tokens, size=60)
    else:
        chunks = [tokens]

    for chunk in chunks:
        counts = [0,0,0,0,0,0,0]
        active = 0
        present_mask = 0

        for token in chunk:
            if token in word2category:
                c = word2category[token]
                if counts[c] == 0:
                    active += 1
                    present_mask |= (1 << c)
                counts[c] += 1

        cat_words = sum(counts)

        if cat_words > 0:
            dominance = max(counts) / cat_words
        else:
            dominance = NULL

        emit window_row

Staging Output (Parquet)

Logical table: windows_features_staging

Fields:

article_id

sentence_idx

window_len

c1 … c7

active

present_mask

dominance

lexicon_version

pipeline_version

run_id

C2️⃣ Comment Staging (Comments → Scores)
Input

article_with_comments.json
(only the comments array)

Algorithm
for comment in comments:
    tokens = tokenize(comment.text)

    polar_count = count(tokens in comment_lexicon)
    comment_len = len(tokens)

    polar_ratio = polar_count / max(1, comment_len)
    like_weight = 1 + ln(1 + like_count)

    emit comment_row

Staging Output (Parquet)

Logical table: comments_features_staging

Fields:

article_id

comment_id

comment_len

polar_count

polar_ratio

like_count

like_weight

comment_score

comment_lexicon_version

pipeline_version

run_id

C3️⃣ Comment Aggregation Staging (Per Article)
Pseudocode
scores = []
weights = []

for comment in article_comments:
    scores.append(comment_score)
    weights.append(like_weight)

audience_mean = weighted_mean(scores, weights)
audience_p85  = weighted_quantile(scores, weights, 0.85)

Staging Output

Logical table: article_comments_agg_staging

Fields:

article_id

num_comments

audience_mean

audience_p85

sum_like_weight

pipeline_version

run_id

D️⃣ Merge Point

The three staging tables:

windows_features_staging

comments_features_staging

article_comments_agg_staging

are loaded into BigQuery and merged (MERGE) into final tables.

❗️No joins occur inside the pipeline.
❗️Linking is performed only via article_id in BigQuery.

E️⃣ Why This Structure Is Research-Sound
1. Signal Separation

Article text = textual signal

Comments = audience signal

Combined only at query time

2. Simple Algorithms → Strong Metrics

No heavy models

No hidden state

Every number is explainable

3. Extensible

Categories can be added

LLMs can be added

Without breaking the contract