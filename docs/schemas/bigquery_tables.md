# 📁 BigQuery Final Tables Schema

This document defines the final analytical tables stored in BigQuery.

---

## Table of Contents

- [1. Purpose of BigQuery Tables](#1-purpose-of-bigquery-tables)
- [2. Final Tables](#2-final-tables)
- [3. windows_features Table](#3-windows_features-table)
- [4. comments_features Table](#4-comments_features-table)
- [5. article_comments_agg Table](#5-article_comments_agg-table)
- [6. articles Table](#6-articles-table)
- [7. Optional LLM Enrichment Table](#7-optional-llm-enrichment-table)
- [8. Merge Semantics](#8-merge-semantics)

---

## 1. Purpose of BigQuery Tables

BigQuery tables exist to:

- Support analytical queries
- Enable aggregation and visualization
- Preserve historical results

BigQuery does not perform feature computation.

---

## 2. Final Tables

The system maintains the following tables:

- articles
- windows_features
- comments_features
- article_comments_agg
- article_llm_enrichment (optional)

---

## 3. windows_features Table

Derived from windows_features_staging.

**Primary key:**
(article_id, sentence_idx)

All staging fields are preserved.

---

## 4. comments_features Table

Derived from comments_features_staging.

**Primary key:**
(article_id, comment_id)

All staging fields are preserved.

---

## 5. article_comments_agg Table

Derived from article_comments_agg_staging.

**Primary key:**
(article_id)

All staging fields are preserved.

---

## 6. articles Table

Contains article-level metadata.

**Fields include:**

- article_id
- canonical_url
- source
- title
- first_seen_at

---

## 7. Optional LLM Enrichment Table

LLM enrichment is stored separately.

**Rules:**

- Does not affect core metrics
- Fully versioned
- Optional per article

---

## 8. Merge Semantics

All tables are updated using MERGE statements.

**Rules:**

- Idempotent
- No deletes
- Updates only by primary key

---

End of document
