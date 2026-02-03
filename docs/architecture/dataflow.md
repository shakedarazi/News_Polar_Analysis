System Dataflow Description

This document describes the end-to-end data flow of the system, from initial article discovery to staging and final merge into BigQuery.
It focuses on the order of operations and the responsibility of each stage.

High-Level Flow Summary

The system processes data in clearly separated stages:

Article discovery and freezing

Snapshot creation with comments

Deterministic feature extraction

Staging of computed results

Merge into analytical tables

Each stage produces immutable outputs that serve as inputs to the next stage.

Entry Point: Article Discovery

The dataflow begins with periodic article discovery.

Input:

News homepages

Section pages

Article listing pages

Process:

Extract article URLs

Canonicalize URLs

Generate article_id using a hash of the canonical URL

Output:

A set of unique article identifiers with canonical URLs

This step ensures that each article is identified exactly once.

Raw Article Fetch and Freeze

For each discovered article:

Process:

Fetch full article text

Extract metadata if available

Record first_seen_at timestamp

Output:

Immutable raw article snapshot stored in GCS

This snapshot is treated as the authoritative source for all future processing.

Selection of Mature Articles

Before processing comments and metrics, articles must mature.

Criteria:

Current time minus first_seen_at is greater than or equal to 24 hours

Purpose:

Allow sufficient accumulation of audience reactions

Avoid premature or biased measurements

Only mature articles proceed to the next stage.

Snapshot Creation With Comments

For each mature article:

Process:

Fetch all available comments

Normalize comment text

Capture like counts

Generate stable comment identifiers

Sort comments deterministically by comment_id

Output:

Article snapshot including full article text and comments

This snapshot represents a consistent view of the article and its audience reaction at a fixed point in time.

Parallel Article Processing (Worker Pool)

Each article snapshot is processed independently.

Process per article:

Normalize article text

Split article into sentence windows

Tokenize each window

Perform lexicon lookup

Compute window-level metrics

Process comments independently

Aggregate comment-level metrics

Parallelism:

Each article is processed by a single worker

No shared state between workers

This ensures scalability without sacrificing determinism.

Feature Extraction Outputs

Processing produces three logical result sets:

Window-level features

One row per article window

Comment-level features

One row per comment

Article-level comment aggregates

One row per article

These outputs are written to staging storage.

Staging Storage

All computed results are written as Parquet files in GCS staging.

Characteristics:

Columnar format

Strong schema enforcement

Versioned outputs

Immutable per run

Staging data is the only input to BigQuery loading.

Load to BigQuery Staging Tables

Parquet files are loaded into temporary staging tables in BigQuery.

Purpose:

Validate schema compatibility

Enable idempotent merges

Isolate partial or failed runs

No business logic is applied at this stage.

Merge Into Final Tables

Final tables are updated using deterministic MERGE operations.

Keys:

article_id

sentence_idx

comment_id

Behavior:

Existing rows are updated

New rows are inserted

No duplicates are created

End-to-End Determinism Guarantee

The full dataflow guarantees that:

Every stage reads immutable inputs

Every stage produces immutable outputs

Re-running the same pipeline produces identical results