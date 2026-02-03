# 🧠 System Architecture Overview

This document explains the high-level architectural decisions of the News Analysis Pipeline and the rationale behind them.
It focuses on why the system is designed the way it is, not on implementation details.
---
## Table of Contents

- [System Purpose at the Architectural Level](#-system-purpose-at-the-architectural-level)
- [Batch-Oriented Design (Not Streaming)](#-batch-oriented-design-not-streaming)
- [Two-DAG Architecture](#-two-dag-architecture)
- [Separation of Signals: Articles vs. Comments](#-separation-of-signals-articles-vs-comments)
- [Determinism as a First-Class Constraint](#-determinism-as-a-first-class-constraint)
- [Snapshot-Based Processing](#-snapshot-based-processing)
- [Storage Layer Responsibilities](#-storage-layer-responsibilities)
- [Extensibility Without Breaking the Contract](#-extensibility-without-breaking-the-contract)
- [Architectural Non-Goals](#-architectural-non-goals)

---

## 📌 System Purpose at the Architectural Level

The system is designed to analyze news articles and their audience reactions in a way that is:

- Deterministic
- Stable over time
- Independent of changes in source websites
- Suitable for research and longitudinal analysis

The architecture prioritizes correctness, reproducibility, and explainability over real-time responsiveness.

---

## 🔄 Batch-Oriented Design (Not Streaming)

The system is intentionally batch-oriented.

**Reasons:**

- News websites are unstable sources: articles can change, move, or disappear.
- Audience reactions (comments, likes) evolve over time and require accumulation.
- There is no business or research requirement for real-time metrics.

**Batch processing enables:**

- Snapshot-based analysis
- Stable comparison between articles
- Reproducible historical runs

> ⚠️ Streaming is explicitly out of scope.

---

## 🧩 Two-DAG Architecture

The pipeline is split into two Airflow DAGs with distinct responsibilities.

### DAG 1: Ingestion (Every 6 Hours)

**Responsibilities:**

- Discover newly published articles
- Canonicalize URLs
- Assign stable article identifiers
- Fetch and store article text as raw data

**DAG 1 does NOT:**

- Analyze text
- Fetch comments
- Compute metrics

### DAG 2: Snapshot and Processing (Daily)

**Responsibilities:**

- Select "mature" articles (articles that have existed long enough)
- Fetch accumulated comments
- Perform deterministic text analysis
- Compute all metrics
- Load results into BigQuery

This separation prevents coupling ingestion speed with analysis correctness.

---

## 🧩 Separation of Signals: Articles vs. Comments

The architecture treats article text and audience comments as two different signals.

### Article text:

- Represents editorial intent
- Is structured and relatively stable
- Analyzed using multi-category lexicons

### Comments:

- Represent audience reaction
- Are unstructured and volatile
- Analyzed using a simpler polarity lexicon
- Weighted by likes as a proxy for agreement

They are processed independently and connected only by article_id at query time.

---

## ⚙️ Determinism as a First-Class Constraint

Determinism is enforced at the architectural level:

- No randomization
- No probabilistic models in the critical path
- No order-dependent computation
- No shared mutable state across workers

Given the same inputs, the system must always produce identical outputs.

---

## 🔄 Snapshot-Based Processing

All analysis is performed on immutable snapshots:

- Raw articles are frozen in GCS
- Comments are collected at a defined snapshot time
- Processing always reads from stored snapshots, never directly from live websites

**This guarantees:**

- Reproducibility
- Auditability
- Ability to re-run historical jobs

---

## 📁 Storage Layer Responsibilities

Each storage layer has a clear role:

| Layer | Responsibility |
|-------|----------------|
| GCS Raw | immutable source-of-truth snapshots |
| GCS Staging (Parquet) | computed features and metrics |
| BigQuery | analytical querying and aggregation |

No business logic is embedded in BigQuery beyond deterministic aggregation.

---

## 🔄 Extensibility Without Breaking the Contract

The architecture supports future extensions without breaking existing data:

- Adding new categories
- Adding new metrics
- Adding optional LLM-based enrichment

**This is achieved by:**

- Versioned outputs
- Immutable raw data
- Strict separation between computation and analysis

---

## ⚠️ Architectural Non-Goals

The system explicitly does NOT aim to:

- Provide real-time alerts
- Perform online learning
- Infer author identity or intent
- Moderate content
- Predict future behavior

These constraints keep the system focused and maintainable.
