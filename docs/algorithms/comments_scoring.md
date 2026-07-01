# 📊 Comment-Level Scoring Algorithm

This document defines the deterministic algorithm used to analyze audience comments and compute per-comment scores.

---

## Table of Contents

- [1. Purpose of Comment Scoring](#1-purpose-of-comment-scoring)
- [2. Definition of a Comment Window](#2-definition-of-a-comment-window)
- [3. Input Assumptions](#3-input-assumptions)
- [4. Tokenization](#4-tokenization)
- [5. Polarity Lexicon Matching](#5-polarity-lexicon-matching)
- [6. Polarity Count](#6-polarity-count)
- [7. Polarity Ratio](#7-polarity-ratio)
- [8. Engagement Weight](#8-engagement-weight)
- [9. Controversy per Comment](#9-controversy-per-comment)
- [10. Comment Score](#10-comment-score)
- [11. Determinism Guarantees](#11-determinism-guarantees)
- [12. Computational Complexity](#12-computational-complexity)
- [13. Output Fields](#13-output-fields)

---

## 1. Purpose of Comment Scoring

Comment scoring exists to:

- Capture audience polarity signal
- Quantify intensity of agreement or disagreement
- Weight reactions by collective approval (likes)

Each comment is treated as an independent analytical unit.

---

## 2. Definition of a Comment Window

A comment is treated as a single window.

**Rules:**

- No splitting into sub-windows
- No overlap with other comments
- No temporal ordering assumptions

---

## 3. Input Assumptions

Each comment provides:

- Normalized comment text
- Like count (non-negative integer)
- Dislike count (non-negative integer, default 0 if source does not expose it)

No author metadata or timestamps are used.

---

## 4. Tokenization

For each comment:

- Tokenize text by whitespace
- Tokens are already normalized
- Token order is preserved

No stemming or lemmatization is applied.

---

## 5. Polarity Lexicon Matching

Matching is performed against a single polarity lexicon.

**Rules:**

- Each token is checked for presence in the lexicon
- Lookup is O(1)
- Tokens either match or do not match

No categories exist at this level.

---

## 6. Polarity Count

For each comment:

- polar_count = number of tokens found in the polarity lexicon
- comment_len = total number of tokens

These values are deterministic.

---

## 7. Polarity Ratio

Polarity ratio is defined as:

```
polar_ratio = polar_count / max(1, comment_len)
```

**This ensures:**

- No division by zero
- A value in the range [0, 1]

---

## 8. Engagement Weight

Total engagement (likes + dislikes) is used as a signal of audience attention.

**Weight is computed as:**

```
engagement_weight = 1 + ln(1 + like_count + dislike_count)
```

**Properties:**

- Minimum weight is 1
- Growth is sub-linear
- Prevents extreme domination by viral comments
- Captures total engagement regardless of sentiment

---

## 9. Controversy per Comment

Controversy measures how divisive a comment is based on the like/dislike split.

**Computation:**

```
total_votes = like_count + dislike_count
p = like_count / max(1, total_votes)
controversy = 4 * p * (1 - p)
```

**Properties:**

- Range is [0, 1]
- Maximum (1.0) when likes and dislikes are equal (p = 0.5)
- Minimum (0.0) when all votes are one-sided
- If total_votes = 0, controversy = 0

This separates divisiveness (how split the crowd was) from intensity (what was said).

---

## 10. Comment Score

The final comment score is defined as:

```
comment_score = polar_ratio
```

Engagement weight influences aggregation, not the score itself.

---

## 11. Determinism Guarantees

The algorithm guarantees:

- Same comment text, likes, and dislikes produce identical scores
- Order of comment processing does not matter
- No randomness or external dependencies

---

## 12. Computational Complexity

For each comment:

- Tokenization + lexicon lookup: O(tokens_in_comment)
- Engagement weight computation: O(1)
- Controversy computation: O(1)

Per article comment processing remains:

- Time: O(total_comment_tokens)
- Space: O(1) extra per comment row

---

## 13. Output Fields

Each comment produces one output record with:

- article_id
- comment_id
- comment_len
- polar_count
- polar_ratio
- like_count
- dislike_count
- engagement_weight
- comment_score
- controversy
- comment_lexicon_version
- pipeline_version
- run_id

---

End of document
