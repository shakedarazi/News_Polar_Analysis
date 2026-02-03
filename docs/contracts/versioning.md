# 📝 Versioning and Provenance Rules

This document defines how versioning is handled across the system in order to guarantee reproducibility, traceability, and safe evolution of the pipeline.

---

## Table of Contents

- [Purpose of Versioning](#-purpose-of-versioning)
- [Pipeline Version](#-pipeline-version)
- [Lexicon Version](#-lexicon-version)
- [Comment Lexicon Version](#-comment-lexicon-version)
- [Run Identifier and Versioning](#-run-identifier-and-versioning)
- [Versioning Scope](#-versioning-scope)
- [Backward Compatibility](#-backward-compatibility)
- [Prohibited Versioning Practices](#-prohibited-versioning-practices)
- [Versioning as a Contract](#-versioning-as-a-contract)

---

## 📌 Purpose of Versioning

Versioning exists to ensure that every computed value in the system can be traced back to:

- The exact code logic that produced it
- The exact lexicon used
- The exact execution context

Without strict versioning, results cannot be compared across time or trusted for research.

---

## ⚙️ Pipeline Version

**Definition:**
pipeline_version identifies the version of the processing logic.

**Characteristics:**

- Changes whenever algorithmic logic changes
- Changes whenever feature definitions change
- Changes whenever aggregation logic changes

**Rules:**

- pipeline_version must be explicitly set
- It must not depend on runtime state
- It must be recorded on every output row

**Recommended format:**

- Git commit hash
- Or semantic version tied to a commit

---

## 📝 Lexicon Version

**Definition:**
lexicon_version identifies the exact article lexicon used for analysis.

**Computation:**

- Derived from a hash of the expanded lexicon file

**Characteristics:**

- Changes whenever the lexicon content changes
- Independent of pipeline_version

**Purpose:**

- Allow comparison between different lexicon configurations
- Enable historical re-analysis

---

## 📝 Comment Lexicon Version

**Definition:**
comment_lexicon_version identifies the polarity lexicon used for comment analysis.

**Rules:**

- Versioned independently from article lexicon
- Stored alongside every comment feature

This separation allows evolution of comment analysis without affecting article metrics.

---

## 🔄 Run Identifier and Versioning

Each pipeline execution generates a unique run_id.

**run_id ties together:**

- pipeline_version
- lexicon_version
- comment_lexicon_version
- All outputs produced during that execution

**run_id is required for:**

- Auditing
- Debugging
- Rollbacks
- Historical comparisons

---

## 📌 Versioning Scope

**Versioning applies to:**

- Window-level features
- Comment-level features
- Article-level aggregates
- Optional enrichment outputs

**Versioning does NOT apply to:**

- Raw article text
- Raw comments snapshot

Raw data is immutable and version-independent.

---

## 🔄 Backward Compatibility

**When introducing changes:**

- Old data must remain queryable
- New versions must not overwrite old results
- Schema evolution must be additive where possible

**Breaking changes require:**

- New tables, or
- Clear version separation

---

## ⚠️ Prohibited Versioning Practices

The following are not allowed:

- Implicit versioning
- Time-based versioning without semantic meaning
- Overwriting data from previous versions
- Mixing outputs from different versions without explicit labeling

---

## 📝 Versioning as a Contract

Versioning rules are a hard contract.

Any code change that affects outputs without updating the relevant version identifier is considered a critical defect.
