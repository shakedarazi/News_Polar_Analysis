Comment-Level Scoring Algorithm

This document defines the deterministic algorithm used to analyze audience comments and compute per-comment scores.

1. Purpose of Comment Scoring

Comment scoring exists to:

Capture audience polarity signal

Quantify intensity of agreement or disagreement

Weight reactions by collective approval (likes)

Each comment is treated as an independent analytical unit.

2. Definition of a Comment Window

A comment is treated as a single window.

Rules:

No splitting into sub-windows

No overlap with other comments

No temporal ordering assumptions

3. Input Assumptions

Each comment provides:

Normalized comment text

Like count (non-negative integer)

No author metadata or timestamps are used.

4. Tokenization

For each comment:

Tokenize text by whitespace

Tokens are already normalized

Token order is preserved

No stemming or lemmatization is applied.

5. Polarity Lexicon Matching

Matching is performed against a single polarity lexicon.

Rules:

Each token is checked for presence in the lexicon

Lookup is O(1)

Tokens either match or do not match

No categories exist at this level.

6. Polarity Count

For each comment:

polar_count = number of tokens found in the polarity lexicon

comment_len = total number of tokens

These values are deterministic.

7. Polarity Ratio

Polarity ratio is defined as:

polar_ratio = polar_count / max(1, comment_len)

This ensures:

No division by zero

A value in the range [0, 1]

8. Like-Based Weight

Likes are treated as a signal of agreement.

Weight is computed as:

like_weight = 1 + ln(1 + like_count)

Properties:

Minimum weight is 1

Growth is sub-linear

Prevents extreme domination by viral comments

9. Comment Score

The final comment score is defined as:

comment_score = polar_ratio

Likes influence aggregation, not the score itself.

10. Determinism Guarantees

The algorithm guarantees:

Same comment text and likes produce identical scores

Order of comment processing does not matter

No randomness or external dependencies

11. Output Fields

Each comment produces one output record with:

article_id

comment_id

comment_len

polar_count

polar_ratio

like_count

like_weight

comment_score

comment_lexicon_version

pipeline_version

run_id

End of document
