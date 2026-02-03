# ⚠️ Data Quality Rules and Validation Constraints

This document defines mandatory data quality rules that must hold for all computed outputs.
These rules ensure correctness, consistency, and analytical reliability.

---

## Table of Contents

- [Purpose of Data Quality Rules](#-purpose-of-data-quality-rules)
- [Window-Level Quality Rules](#-window-level-quality-rules)
- [Category Consistency Rules](#-category-consistency-rules)
- [Comment-Level Quality Rules](#-comment-level-quality-rules)
- [Article-Level Aggregate Rules](#-article-level-aggregate-rules)
- [Cardinality Expectations](#-cardinality-expectations)
- [Referential Integrity Rules](#-referential-integrity-rules)
- [Versioning Completeness Rules](#-versioning-completeness-rules)
- [Immutability Expectations](#-immutability-expectations)
- [Handling of Violations](#-handling-of-violations)
- [Data Quality as a Contract](#-data-quality-as-a-contract)

---

## 📌 Purpose of Data Quality Rules

Data quality rules exist to:

- Detect corrupted or partial outputs
- Prevent silent logical errors
- Enforce assumptions made by the analysis
- Enable safe downstream querying

Violations must be detectable automatically.

---

## 📊 Window-Level Quality Rules

Each article window must satisfy the following constraints:

- window_len must be greater than 0
- window_len must be an integer
- counts per category must be non-negative integers
- sum of category counts must be less than or equal to window_len

**If a window contains no category matches:**

- cat_words equals 0
- dominance must be NULL

**If a window contains category matches:**

- dominance must be between 0 and 1 inclusive

---

## 📊 Category Consistency Rules

For each window:

- active must equal the number of categories with count greater than 0
- present_mask must reflect exactly the same active categories
- present_mask must be consistent with counts vector

Any mismatch indicates a computation defect.

---

## 📊 Comment-Level Quality Rules

Each comment feature must satisfy:

- comment_len must be greater than 0
- polar_count must be between 0 and comment_len
- polar_ratio must be between 0 and 1 inclusive
- like_count must be greater than or equal to 0
- like_weight must be greater than or equal to 1
- comment_score must equal polar_ratio exactly.

---

## 📊 Article-Level Aggregate Rules

For each article aggregate:

- num_comments must be greater than or equal to 0
- sum_like_weight must be greater than or equal to num_comments
- audience_mean must be between 0 and 1 inclusive, or NULL if num_comments is 0
- audience_p85 must be between 0 and 1 inclusive, or NULL if num_comments is 0

**If num_comments equals 0:**

- audience_mean must be NULL
- audience_p85 must be NULL

---

## ⚠️ Cardinality Expectations

Expected ranges are used as warnings, not hard failures:

- num_comments should not exceed 200
- number of windows per article should be within reasonable bounds relative to article length

Exceeding these thresholds triggers warnings for manual inspection.

---

## 🔐 Referential Integrity Rules

The following relationships must always hold:

- Every window references a valid article_id
- Every comment feature references a valid article_id
- Every aggregate references a valid article_id

Missing references indicate incomplete ingestion or processing failure.

---

## 📝 Versioning Completeness Rules

Every computed row must include:

- pipeline_version
- lexicon_version (or comment_lexicon_version)
- run_id

Missing version fields are considered critical errors.

---

## ⚠️ Immutability Expectations

Once data passes validation and is written to final storage:

- Rows must not be updated in place
- Corrections require a new run_id
- Historical data must remain intact

---

## 🚀 Handling of Violations

If a data quality violation is detected:

- The affected article or run must be flagged
- Partial outputs must not be merged into final tables
- The run may be retried safely after correction

---

## 📝 Data Quality as a Contract

Data quality rules are part of the system contract.

Any change to algorithms or schemas that invalidates these rules must:

- Be explicitly documented
- Introduce new versions
- Preserve backward compatibility where possible
