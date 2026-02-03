Article Window Segmentation and Feature Extraction

This document defines the exact algorithm used to split article text into windows and compute window-level features for category-based analysis.

1. Purpose of Window-Based Analysis

Window-based analysis exists to:

Capture localized semantic signals

Avoid dilution across long articles

Enable measurement of category richness and dominance

Preserve interpretability at sentence level

The window is the smallest analytical unit for article text.

2. Definition of a Window

A window is defined as:

A single sentence extracted from the article text

If a sentence is too long, it is split into fixed-size sub-windows

Windows do not overlap and do not cross sentence boundaries.

3. Sentence Splitting Rules

Sentence splitting is deterministic and rule-based.

Rules:

Split on ".", "!", "?", and ellipsis

Apply heuristics to avoid splitting on common abbreviations

Preserve original sentence order

Each sentence receives a sequential sentence_idx starting from 0.

4. Chunking Long Sentences

If a sentence contains more than 60 tokens:

It is split into consecutive chunks of 60 tokens

Each chunk becomes a separate window

sentence_idx continues sequentially across chunks

This prevents extreme window sizes from skewing metrics.

5. Tokenization

For each window:

Text is tokenized using whitespace-based tokenization

Tokens are already normalized upstream

Token order is preserved

No stemming or lemmatization is applied at runtime.

6. Category Matching

Category matching is performed using a precomputed dictionary:

word_to_category mapping

One token maps to at most one category

Lookup is O(1)

The lexicon is expanded offline and versioned.

7. Feature Computation per Window

For each window, the following are computed:

counts vector of size 7 (one per category)

active category count

window length (number of tokens)

total category words (sum of counts)

The counts vector is initialized to zeros for each window.

8. Active Category Tracking

When a token matches a category:

The corresponding count is incremented

If the count transitions from 0 to 1:

active category count is incremented

This ensures active reflects unique category presence.

9. Dominance Metric

Dominance is defined as:

dominance = max(counts) / total_category_words

Rules:

If total_category_words equals 0, dominance is NULL

Otherwise dominance is in the range [0, 1]

Dominance measures concentration versus diversity.

10. Computational Complexity

For a single article:

Time complexity: O(number of tokens)

Space complexity: O(1) per window

Across all articles, complexity scales linearly with input size.

11. Determinism Guarantees

The algorithm guarantees:

Same input text produces identical windows

Same lexicon version produces identical matches

Execution order does not affect results

No randomness is involved.

12. Output Fields

Each window produces a single output record with:

article_id

sentence_idx

window_len

counts per category (c1 to c7)

active category count

dominance

lexicon_version

pipeline_version

run_id