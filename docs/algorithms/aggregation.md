# 📊 Article-Level Aggregation Algorithms

This document defines how comment-level scores are aggregated to produce article-level audience metrics.

---

## Table of Contents

- [1. Purpose of Aggregation](#1-purpose-of-aggregation)
- [2. Inputs to Aggregation](#2-inputs-to-aggregation)
- [3. Number of Comments](#3-number-of-comments)
- [4. Weighted Mean](#4-weighted-mean)
- [5. Weighted Quantile (p85)](#5-weighted-quantile-p85)
- [6. Why p85](#6-why-p85)
- [7. Output Fields](#7-output-fields)
- [8. Determinism Guarantees](#8-determinism-guarantees)
- [9. Computational Complexity](#9-computational-complexity)

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

- A set of comment_score values
- A corresponding set of like_weight values

Both sets are derived deterministically.

---

## 3. Number of Comments

num_comments is defined as:

- The total number of comments associated with the article

This value is informational and used for validation.

---

## 4. Weighted Mean

Audience mean score is computed as a weighted mean:

```
audience_mean = sum(comment_score * like_weight) / sum(like_weight)
```

**Rules:**

- If num_comments equals 0, audience_mean is NULL
- sum(like_weight) must be greater than 0

---

## 5. Weighted Quantile (p85)

Audience p85 is computed as a weighted quantile at 0.85.

**Procedure:**

1. Sort comments by comment_score ascending
2. Accumulate like_weight cumulatively
3. Identify the smallest score where cumulative weight >= 85% of total weight

**Rules:**

- If num_comments equals 0, audience_p85 is NULL
- Quantile computation is deterministic

---

## 6. Why p85

p85 was chosen because:

- It captures strong reactions
- It is robust to outliers
- It reflects dominant audience sentiment

It balances sensitivity and stability.

---

## 7. Output Fields

Each article produces one aggregation record with:

- article_id
- num_comments
- audience_mean
- audience_p85
- sum_like_weight
- pipeline_version
- run_id

---

## 8. Determinism Guarantees

Aggregation guarantees:

- Same inputs produce identical outputs
- Ordering does not affect results
- No random sampling is used

---

## 9. Computational Complexity

For one article:

- Time complexity: O(n log n), due to sorting for quantile
- Space complexity: O(n), where n is number of comments

Given the comment volume is small (<= 200), this is acceptable.
