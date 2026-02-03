Processing DAG – Snapshot, Analysis, and Staging

This document defines the second Airflow DAG responsible for snapshotting articles with comments, running deterministic analysis, and writing results to staging storage.

1. Purpose of the Processing DAG

The processing DAG exists to:

Create a stable snapshot of articles and their comments

Perform deterministic text analysis

Compute all window-level and comment-level features

Write results to staging for downstream merging

This DAG is the analytical core of the system.

2. Schedule

Runs once per day

Operates only on mature articles

Independent of ingestion timing

3. Input Selection Criteria

An article is eligible for processing if:

It exists in raw storage

Current time minus first_seen_at is at least 24 hours

It has not yet been processed for the current pipeline_version

This ensures stable and comparable results.

4. Snapshot Creation

For each eligible article:

Load raw article snapshot from GCS

Fetch all available comments

Normalize comment text

Capture like counts

Generate deterministic comment identifiers

Sort comments by comment_id

The result is a complete, immutable snapshot.

5. Parallel Execution Model

Articles are processed in parallel.

Rules:

One worker processes one article

No shared state between workers

No concurrency inside an article

This guarantees determinism and fault isolation.

6. Article Text Processing

For each article:

Normalize article text

Split text into sentence windows

Chunk long sentences if needed

Tokenize each window

Match tokens against the article lexicon

Compute window-level features

All operations are deterministic and order-preserving.

7. Comment Processing

For each comment:

Tokenize comment text

Count polarity lexicon matches

Compute polarity ratio

Compute like-based weight

Produce comment-level feature record

Comments are treated as independent units.

8. Article-Level Aggregation

After processing all comments:

Compute weighted mean of comment scores

Compute weighted p85 of comment scores

Count total number of comments

Aggregations depend only on comment-level features.

9. Staging Outputs

The processing DAG produces three staging outputs:

Window-level features

Comment-level features

Article-level comment aggregates

Each output is written as Parquet files to GCS staging.

10. Versioning and Metadata

Every staging record must include:

article_id

run_id

pipeline_version

lexicon_version or comment_lexicon_version

This ensures full traceability.

11. Idempotency and Retries

The processing DAG guarantees:

Safe retries on failure

No duplicate outputs

Deterministic recomputation

Failures affect only the current article.

12. Explicit Non-Responsibilities

The processing DAG must never:

Modify raw article data

Perform BigQuery merges

Apply ad-hoc analysis logic

Depend on execution order