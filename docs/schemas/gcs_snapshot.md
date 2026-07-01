# 📁 Article Snapshot With Comments Schema (GCS)

This document defines the schema of article snapshots that include both article text and audience comments.

---

## Table of Contents

- [1. Purpose of Snapshot Storage](#1-purpose-of-snapshot-storage)
- [2. Storage Unit](#2-storage-unit)
- [3. Required Article Fields](#3-required-article-fields)
- [4. Comments Array](#4-comments-array)
- [5. Comment Ordering](#5-comment-ordering)
- [6. Immutability Rules](#6-immutability-rules)

---

## 1. Purpose of Snapshot Storage

Snapshot storage exists to:

- Capture a consistent view of article and comments
- Decouple processing from live websites
- Enable deterministic analysis

Snapshots are immutable per run.

---

## 2. Storage Unit

Each snapshot is stored as a single JSON object.

**Rules:**

- One file per article per snapshot run
- Comments are embedded inside the article object
- Comments are sorted deterministically

---

## 3. Required Article Fields

Each snapshot must include:

- article_id
- canonical_url
- source
- title (nullable)
- text
- snapshot_at (UTC timestamp)
- snapshot_run_id

---

## 4. Comments Array

The snapshot contains a comments array.

**Each comment object must include:**

- comment_id
- text
- like_count
- dislike_count (integer, default 0 if source does not expose it)

> 📝 If dislike is not available from the source, store dislike_count = 0 to preserve backward compatibility.

No author or timestamp fields are stored.

---

## 5. Comment Ordering

Comments must be sorted by:

- comment_id ascending

This ensures deterministic processing order.

---

## 6. Immutability Rules

**Once written:**

- Snapshot files must never be modified
- New snapshots require new snapshot_run_id
- Old snapshots remain available

---

End of document
