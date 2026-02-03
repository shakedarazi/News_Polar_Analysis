Ingestion DAG – Article Discovery and Freezing

This document defines the first Airflow DAG responsible for discovering news articles and freezing them as immutable raw inputs.

1. Purpose of the Ingestion DAG

The ingestion DAG exists to:

Discover new articles as early as possible

Assign stable identifiers

Store raw article snapshots before the source changes or removes them

This DAG does not perform any analysis.

2. Schedule

Runs every 6 hours

Independent of downstream processing

Can be rerun safely without side effects

3. Inputs

News websites homepages

Section pages

Article listing pages

The exact crawling logic is source-specific but must produce canonical URLs.

4. Core Steps

For each source:

Fetch listing pages

Extract article URLs

Canonicalize URLs

Compute article_id from canonical URL

Check if article_id already exists

If new:

Fetch article content

Store raw snapshot

5. Canonicalization Rules

Canonicalization must ensure:

One logical article maps to one URL

Tracking parameters are removed

URL casing and formatting are normalized

This step is critical for idempotency.

6. Raw Article Snapshot

Each new article is stored as an immutable snapshot.

Stored fields include:

article_id

canonical_url

source

title (if available)

full article text

first_seen_at timestamp

ingestion_run_id

7. Storage Location

Raw articles are stored in GCS.

Logical layout:

Grouped by source

Partitioned by date

One file per article

Once written, raw snapshots must never be modified.

8. Idempotency Guarantees

The ingestion DAG guarantees that:

The same article is never ingested twice

Re-running the DAG does not create duplicates

Partial failures do not corrupt stored data

9. Failure Handling

If ingestion fails for an article:

Other articles continue processing

The failed article can be retried safely

No downstream pipeline is affected

10. Explicit Non-Responsibilities

The ingestion DAG must never:

Fetch comments

Split text into windows

Apply lexicons

Compute metrics

Call LLMs

All analysis belongs strictly to the processing DAG.