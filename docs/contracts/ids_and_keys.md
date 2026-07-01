# 🔐 Identifiers and Primary Keys Contract

This document defines how all entities in the system are identified and how primary keys are constructed.
These rules are mandatory and ensure uniqueness, determinism, and idempotency across the pipeline.

---

## Table of Contents

- [Canonical URL](#-canonical-url)
- [Article Identifier (article_id)](#-article-identifier-article_id)
- [Article Window Identifier](#-article-window-identifier)
- [Comment Identifier (comment_id)](#-comment-identifier-comment_id)
- [Run Identifier (run_id)](#-run-identifier-run_id)
- [Version Identifiers](#-version-identifiers)
- [Primary Key Summary](#-primary-key-summary)
- [Idempotency Guarantees](#-idempotency-guarantees)
- [Prohibited Identifier Behavior](#-prohibited-identifier-behavior)

---

## 🔐 Canonical URL

**Definition:**
The canonical URL is the normalized representation of an article URL.

**Normalization rules:**

- Remove tracking query parameters
- Normalize URL scheme (http/https)
- Remove trailing slashes
- Normalize domain casing

**Purpose:**

- Ensure that the same article always maps to the same identifier
- Prevent duplication due to URL variations

---

## 🔐 Article Identifier (article_id)

**Definition:**
article_id is a deterministic hash derived from the canonical URL.

**Computation:**

```
article_id = sha256(canonical_url)
```

**Characteristics:**

- Globally unique across all sources
- Stable across runs
- Independent of fetch time or processing order

**Primary Key:**
article_id

---

## 🔐 Article Window Identifier

**Definition:**
Article windows are identified by the combination of article_id and sentence index.

**Components:**

- article_id
- sentence_idx

**sentence_idx rules:**

- Starts at 0 for the first sentence
- Increments sequentially
- Continues across sentence splits when chunking is applied

**Primary Key:**
(article_id, sentence_idx)

---

## 🔐 Comment Identifier (comment_id)

**Definition:**
comment_id uniquely identifies a comment within an article.

**If the source provides a stable comment identifier:**

- Use the source-provided identifier

**Otherwise:**

- Generate a deterministic identifier

**Computation:**

```
comment_id = sha256(article_id + comment_text + local_index)
```

**Characteristics:**

- Stable within a snapshot
- Deterministic
- Unique per article

**Primary Key:**
(article_id, comment_id)

---

## 🔐 Run Identifier (run_id)

**Definition:**
run_id uniquely identifies a single execution of the processing pipeline.

**Characteristics:**

- Generated once per pipeline execution
- Shared across all outputs of that execution
- Immutable

**Purpose:**

- Traceability
- Auditability
- Comparison between pipeline runs

---

## 📝 Version Identifiers

The system uses explicit version identifiers to track provenance.

**Types:**

- pipeline_version
- lexicon_version
- comment_lexicon_version

**Rules:**

- Versions must be deterministic
- Any logic or data change requires a new version
- Versions are stored alongside all outputs

---

## 📌 Primary Key Summary

Entity to primary key mapping:

| Entity | Primary Key |
|--------|-------------|
| Article | article_id |
| Article Window | (article_id, sentence_idx) |
| Comment | (article_id, comment_id) |
| Comment Feature | (article_id, comment_id) |
| Article Comment Aggregate | article_id |
| Run | run_id |

---

## ⚙️ Idempotency Guarantees

The identifier strategy guarantees that:

- Reprocessing the same inputs does not create duplicates
- MERGE operations in BigQuery are safe
- Partial failures can be retried without corruption

---

## ⚠️ Prohibited Identifier Behavior

The following are strictly forbidden:

- Using timestamps as identifiers
- Using incremental counters across runs
- Using non-deterministic UUIDs
- Deriving identifiers from processing order
