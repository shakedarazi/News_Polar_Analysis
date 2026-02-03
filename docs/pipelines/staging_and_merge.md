# 🔄 Staging Storage and BigQuery Merge Strategy

This document defines how computed outputs are staged in GCS and deterministically merged into BigQuery final tables.

---

## Table of Contents

- [1. Purpose of Staging](#1-purpose-of-staging)
- [2. Staging as a Hard Boundary](#2-staging-as-a-hard-boundary)
- [3. Staging Format](#3-staging-format)
- [4. Staging Datasets](#4-staging-datasets)
- [5. Required Fields in All Staging Records](#5-required-fields-in-all-staging-records)
- [6. Staging Storage Layout in GCS](#6-staging-storage-layout-in-gcs)
- [7. Load to BigQuery Staging Tables](#7-load-to-bigquery-staging-tables)
- [8. Merge Strategy](#8-merge-strategy)
- [9. Merge Keys](#9-merge-keys)
- [10. Failure and Retry Semantics](#10-failure-and-retry-semantics)
- [11. Separation from Analysis](#11-separation-from-analysis)
- [12. Extensibility Rules](#12-extensibility-rules)

---

## 1. Purpose of Staging

Staging exists to:

- Decouple computation from analytical storage
- Enforce schema validation before BigQuery
- Enable idempotent and safe MERGE operations
- Isolate partial or failed runs

No business logic is executed in BigQuery beyond deterministic merges.

---

## 2. Staging as a Hard Boundary

All computation must finish before data enters staging.

**Rules:**

- No transformations after staging
- No joins between staging outputs
- No cross-article dependencies

Staging is write-once per run.

---

## 3. Staging Format

The staging format is Parquet.

**Reasons:**

- Strong schema enforcement
- Columnar storage
- Efficient BigQuery ingestion
- Explicit typing

Each staging dataset corresponds to exactly one logical entity.

---

## 4. Staging Datasets

The system produces three staging datasets:

| Dataset | Description |
|---------|-------------|
| windows_features_staging | One row per article window |
| comments_features_staging | One row per comment |
| article_comments_agg_staging | One row per article |

Each dataset is written independently.

---

## 5. Required Fields in All Staging Records

Every staging record must include:

- article_id
- run_id
- pipeline_version
- Source-specific version fields
- Deterministic primary key fields

Records missing any of these fields must be rejected.

---

## 6. Staging Storage Layout in GCS

Staging files are stored in GCS using a deterministic layout:

- Partitioned by run date
- Partitioned by logical dataset
- Files are immutable once written

Each run produces a new set of staging files.

---

## 7. Load to BigQuery Staging Tables

Staging Parquet files are loaded into temporary BigQuery staging tables.

**Characteristics:**

- One-to-one schema mapping
- No transformations
- Load is repeatable and safe

Temporary staging tables are isolated per run.

---

## 8. Merge Strategy

Final tables are updated using deterministic MERGE statements.

**Rules:**

- Primary keys define uniqueness
- Existing rows are updated
- New rows are inserted
- No deletes are performed

MERGE logic must be idempotent.

---

## 9. Merge Keys

Merge keys by dataset:

| Dataset | Merge Key |
|---------|-----------|
| windows_features | (article_id, sentence_idx) |
| comments_features | (article_id, comment_id) |
| article_comments_agg | article_id |

These keys are mandatory and immutable.

---

## 10. Failure and Retry Semantics

If a merge fails:

- The run is marked as failed
- Final tables remain unchanged
- The same staging data can be re-merged safely

No partial merges are allowed.

---

## 11. Separation from Analysis

BigQuery is used only for:

- Querying
- Aggregation
- Visualization

All analytical feature computation happens upstream.

---

## 12. Extensibility Rules

New metrics or entities must:

- Introduce new columns or tables
- Preserve existing schemas
- Respect versioning and primary keys

Breaking changes require new tables or versions.
