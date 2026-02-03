Article Snapshot With Comments Schema (GCS)

This document defines the schema of article snapshots that include both article text and audience comments.

1. Purpose of Snapshot Storage

Snapshot storage exists to:

Capture a consistent view of article and comments

Decouple processing from live websites

Enable deterministic analysis

Snapshots are immutable per run.

2. Storage Unit

Each snapshot is stored as a single JSON object.

Rules:

One file per article per snapshot run

Comments are embedded inside the article object

Comments are sorted deterministically

3. Required Article Fields

Each snapshot must include:

article_id

canonical_url

source

title (nullable)

text

snapshot_at (UTC timestamp)

snapshot_run_id

4. Comments Array

The snapshot contains a comments array.

Each comment object must include:

comment_id

text

like_count

No author or timestamp fields are stored.

5. Comment Ordering

Comments must be sorted by:

comment_id ascending

This ensures deterministic processing order.

6. Immutability Rules

Once written:

Snapshot files must never be modified

New snapshots require new snapshot_run_id

Old snapshots remain available

End of document
