# 📊 Article-Level Aggregation Algorithms

This document defines how comment-level scores are aggregated to produce article-level audience metrics.

---

## Table of Contents

- [1. Purpose of Aggregation](#1-purpose-of-aggregation)
- [2. Inputs to Aggregation](#2-inputs-to-aggregation)
- [3. Number of Comments](#3-number-of-comments)
- [4. Weighted Mean (Audience)](#4-weighted-mean-audience)
- [5. Weighted Quantile p85 (Audience)](#5-weighted-quantile-p85-audience)
- [6. Controversy Aggregation](#6-controversy-aggregation)
- [7. Why p85](#7-why-p85)
- [8. Output Fields](#8-output-fields)
- [9. Determinism Guarantees](#9-determinism-guarantees)
- [10. Computational Complexity](#10-computational-complexity)

---

## 1. Purpose of Aggregation

Aggregation exists to:

- Reduce noise from individual comments
- Produce stable article-level audience signals
- Enable comparison across articles

Aggregation operates only on comment features.

---

## 2. Inputs to Aggregation

For a given article, aggregation receives:

- A set of comment_score values (text intensity)
- A set of controversy values (divisiveness)
- A corresponding set of engagement_weight values

All sets are derived deterministically from comment features.

---

## 3. Number of Comments

num_comments is defined as:

- The total number of comments associated with the article

This value is informational and used for validation.

---

## 4. Weighted Mean (Audience)

Audience mean score is computed as a weighted mean:

```
audience_mean = sum(comment_score * engagement_weight) / sum(engagement_weight)
```

**Rules:**

- If num_comments equals 0, audience_mean is NULL
- sum(engagement_weight) must be greater than 0

---

## 5. Weighted Quantile p85 (Audience)

Audience p85 is computed as a weighted quantile at 0.85.

**Procedure:**

1. Sort comments by comment_score ascending
2. Accumulate engagement_weight cumulatively
3. Identify the smallest score where cumulative weight >= 85% of total weight

**Rules:**

- If num_comments equals 0, audience_p85 is NULL
- Quantile computation is deterministic

---

## 6. Controversy Aggregation

Controversy metrics aggregate divisiveness across all comments.

### Controversy Mean

```
controversy_mean = sum(controversy * engagement_weight) / sum(engagement_weight)
```

**Rules:**

- If num_comments equals 0, controversy_mean is NULL
- Range is [0, 1]

### Controversy p85

Computed as a weighted quantile at 0.85 over controversy values.

**Procedure:**

1. Sort comments by controversy ascending
2. Accumulate engagement_weight cumulatively
3. Identify the smallest controversy where cumulative weight >= 85% of total weight

**Rules:**

- If num_comments equals 0, controversy_p85 is NULL
- Range is [0, 1]

---

## 7. Why p85

p85 was chosen because:

- It captures strong reactions
- It is robust to outliers
- It reflects dominant audience sentiment

It balances sensitivity and stability.

---

## 8. Output Fields

Each article produces one aggregation record with:

- article_id
- num_comments
- audience_mean
- audience_p85
- controversy_mean
- controversy_p85
- sum_engagement_weight
- pipeline_version
- run_id

---

## 9. Determinism Guarantees

Aggregation guarantees:

- Same inputs produce identical outputs
- Ordering does not affect results
- No random sampling is used

---

## 10. Computational Complexity

For one article:

- Mean computations: O(n) for n comments
- p85 computations require sorting: O(n log n) time, O(n) space
- Two sorts may be performed (one for comment_score, one for controversy)

Given the comment volume is small (<= 200), this is acceptable.

> 📝 Optional micro-optimization: sort once by comment_score and once by controversy; keep it simple.
