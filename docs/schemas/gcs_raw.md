# 📁 Raw Article Storage Schema (GCS)

This document defines the schema and structure of raw article data stored in Google Cloud Storage.

---

## Table of Contents

- [1. Purpose of Raw Storage](#1-purpose-of-raw-storage)
- [2. Storage Unit](#2-storage-unit)
- [3. Required Fields](#3-required-fields)
- [4. Optional Fields](#4-optional-fields)
- [5. Storage Layout](#5-storage-layout)
- [6. Immutability Rules](#6-immutability-rules)

---

## 1. Purpose of Raw Storage

Raw storage exists to:

- Preserve the original article content
- Serve as immutable source-of-truth
- Enable full reproducibility

Raw data must never be modified after ingestion.

---

## 2. Storage Unit

Each article is stored as a single JSON object.

**Rules:**

- One file per article
- Immutable after write
- Deterministic file path

---

## 3. Required Fields

Each raw article object must include:

- article_id
- canonical_url
- source
- title (nullable)
- text (full article text)
- first_seen_at (UTC timestamp)
- ingestion_run_id

---

## 4. Optional Fields

Optional metadata may include:

- author (if available)
- section
- tags
- language

Optional fields must not affect downstream computation.

---

## 5. Storage Layout

Logical layout in GCS:

- Grouped by source
- Partitioned by ingestion date
- One JSON file per article

---

## 6. Immutability Rules

**Once written:**

- Raw article files must never be updated
- Corrections require a new file with a new article_id
- Historical files must remain accessible

---

End of document
