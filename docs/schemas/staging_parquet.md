# 📁 Staging Parquet Schemas

This document defines the schemas of Parquet files written to staging storage before loading into BigQuery.

---

## Table of Contents

- [1. Purpose of Staging Schemas](#1-purpose-of-staging-schemas)
- [2. Windows Features Staging Schema](#2-windows-features-staging-schema)
- [3. Comments Features Staging Schema](#3-comments-features-staging-schema)
- [4. Article Comments Aggregate Staging Schema](#4-article-comments-aggregate-staging-schema)
- [5. Staging Rules](#5-staging-rules)

---

## 1. Purpose of Staging Schemas

Staging schemas exist to:

- Enforce strong typing
- Validate computation results
- Serve as boundary before BigQuery

Each schema corresponds to one logical entity.

---

## 2. Windows Features Staging Schema

**Fields:**

- article_id (string)
- sentence_idx (integer)
- window_len (integer)
- c1, c2, c3, c4, c5, c6, c7 (integer)
- active (integer)
- dominance (float, nullable)
- lexicon_version (string)
- pipeline_version (string)
- run_id (string)

**Primary key:**
(article_id, sentence_idx)

---

## 3. Comments Features Staging Schema

**Fields:**

- article_id (string)
- comment_id (string)
- comment_len (integer)
- polar_count (integer)
- polar_ratio (float)
- like_count (integer)
- dislike_count (integer)
- engagement_weight (float)
- comment_score (float)
- controversy (float)
- comment_lexicon_version (string)
- pipeline_version (string)
- run_id (string)

**Primary key:**
(article_id, comment_id)

---

## 4. Article Comments Aggregate Staging Schema

**Fields:**

- article_id (string)
- num_comments (integer)
- audience_mean (float, nullable)
- audience_p85 (float, nullable)
- controversy_mean (float, nullable)
- controversy_p85 (float, nullable)
- sum_engagement_weight (float)
- pipeline_version (string)
- run_id (string)

**Primary key:**
(article_id)

---

## 5. Staging Rules

- All fields are required unless explicitly marked nullable
- No derived fields are added later
- Schema changes must be additive

---

End of document
