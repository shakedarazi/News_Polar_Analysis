# 🚀 Processing DAG – Snapshot, Analysis, and Staging

This document defines the second Airflow DAG responsible for snapshotting articles with comments, running deterministic analysis, and writing results to staging storage.

---

## Table of Contents

- [1. Purpose of the Processing DAG](#1-purpose-of-the-processing-dag)
- [2. Schedule](#2-schedule)
- [3. Input Selection Criteria](#3-input-selection-criteria)
- [4. Snapshot Creation](#4-snapshot-creation)
- [5. Parallel Execution Model](#5-parallel-execution-model)
- [6. Article Text Processing](#6-article-text-processing)
- [7. Comment Processing](#7-comment-processing)
- [8. Article-Level Aggregation](#8-article-level-aggregation)
- [9. Staging Outputs](#9-staging-outputs)
- [10. Versioning and Metadata](#10-versioning-and-metadata)
- [11. Idempotency and Retries](#11-idempotency-and-retries)
- [12. Explicit Non-Responsibilities](#12-explicit-non-responsibilities)

---

## 1. Purpose of the Processing DAG

The processing DAG exists to:

- Create a stable snapshot of articles and their comments
- Perform deterministic text analysis
- Compute all window-level and comment-level features
- Write results to staging for downstream merging

This DAG is the analytical core of the system.

---

## 2. Schedule

- Runs once per day
- Operates only on mature articles
- Independent of ingestion timing

---

## 3. Input Selection Criteria

An article is eligible for processing if:

- It exists in raw storage
- Current time minus first_seen_at is at least 24 hours
- It has not yet been processed for the current pipeline_version

This ensures stable and comparable results.

---

## 4. Snapshot Creation

For each eligible article:

1. Load raw article snapshot from GCS
2. Fetch all available comments
3. Normalize comment text
4. Capture like counts
5. Capture dislike counts (if source provides it; otherwise set to 0)
6. Generate deterministic comment identifiers
7. Sort comments by comment_id

The result is a complete, immutable snapshot.

> 📝 If the source does not expose dislike_count, store dislike_count = 0 to preserve backward compatibility.

---

## 5. Parallel Execution Model

Articles are processed in parallel.

**Rules:**

- One worker processes one article
- No shared state between workers
- No concurrency inside an article

This guarantees determinism and fault isolation.

---

## 6. Article Text Processing

For each article:

1. Normalize article text
2. Split text into sentence windows
3. Chunk long sentences if needed
4. Tokenize each window
5. Match tokens against the article lexicon
6. Compute window-level features

All operations are deterministic and order-preserving.

---

## 7. Comment Processing

For each comment:

1. Tokenize comment text
2. Count polarity lexicon matches
3. Compute polarity ratio
4. Compute engagement weight (from likes + dislikes)
5. Compute controversy (divisiveness from like/dislike split)
6. Produce comment-level feature record

Comments are treated as independent units.

---

## 8. Article-Level Aggregation

After processing all comments:

- Compute weighted mean of comment scores (audience_mean)
- Compute weighted p85 of comment scores (audience_p85)
- Compute weighted mean of controversy (controversy_mean)
- Compute weighted p85 of controversy (controversy_p85)
- Count total number of comments

Aggregations depend only on comment-level features and use engagement_weight.

---

## 9. Staging Outputs

The processing DAG produces three staging outputs:

- Window-level features
- Comment-level features
- Article-level comment aggregates

Each output is written as Parquet files to GCS staging.

---

## 10. Versioning and Metadata

Every staging record must include:

- article_id
- run_id
- pipeline_version
- lexicon_version or comment_lexicon_version

This ensures full traceability.

---

## 11. Idempotency and Retries

The processing DAG guarantees:

- Safe retries on failure
- No duplicate outputs
- Deterministic recomputation

Failures affect only the current article.

---

## 12. Explicit Non-Responsibilities

The processing DAG must never:

- Modify raw article data
- Perform BigQuery merges
- Apply ad-hoc analysis logic
- Depend on execution order
