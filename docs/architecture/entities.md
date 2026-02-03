Core Entities Definition

This document defines the core entities used throughout the system, their meaning, and their boundaries.
These entity definitions form a hard contract between ingestion, processing, storage, and analysis.

Article Entity

Definition:
An Article represents a single news item published by a news source.

Characteristics:

Identified uniquely by article_id

Immutable once stored in raw storage

Serves as the root entity for all downstream data

Primary responsibilities:

Anchor for window-level analysis

Anchor for comment-level analysis

Anchor for all aggregations

An Article exists even if it has:

No comments

No detected lexicon matches

Article Window Entity

Definition:
An Article Window represents a contiguous segment of article text used for analysis.

In this system:

A window corresponds to a sentence

Long sentences may be split into fixed-size sub-windows

Characteristics:

Always associated with exactly one Article

Identified by (article_id, sentence_idx)

Ordered deterministically within an article

Purpose:

Capture localized semantic signals

Enable measurement of category distribution

Enable computation of dominance and category richness

Windows do not:

Overlap

Cross article boundaries

Depend on other windows

Comment Entity

Definition:
A Comment represents a single audience reaction to an article.

Characteristics:

Associated with exactly one Article

Identified by (article_id, comment_id)

Text-only analysis (no author metadata)

Assumptions:

Comment identity is stable within a snapshot

Likes represent agreement intensity

Comment text is treated as an atomic unit

Comments are:

Independent of each other

Not temporally ordered for analysis

Not attributed to users

Comment Feature Entity

Definition:
A Comment Feature is the computed analytical representation of a Comment.

Includes:

Comment length

Polarity ratio

Like-based weight

Final comment score

Characteristics:

Fully deterministic

Derived only from comment text and like count

Immutable once computed for a given run

Article Comment Aggregate Entity

Definition:
An Article Comment Aggregate summarizes audience reaction at the article level.

Includes:

Number of comments

Weighted mean of comment scores

Weighted p85 of comment scores

Purpose:

Represent overall audience polarity

Reduce comment-level noise

Enable article-level comparison

Aggregates:

Are computed only from comment features

Do not include article text signals

Are recomputable from staging data

Lexicon Entity

Definition:
A Lexicon is a versioned collection of terms used for matching during analysis.

Types:

Article lexicon (7 categories)

Comment polarity lexicon (single category)

Characteristics:

Expanded offline

Immutable per version

Referenced by lexicon_version identifiers

Lexicons are:

Deterministic

Explicitly versioned

Independent of runtime text processing

Run Entity

Definition:
A Run represents a single execution of the processing pipeline.

Characteristics:

Identified by run_id

Tied to specific versions of code and lexicons

Groups all outputs generated during that execution

Purpose:

Enable auditability

Enable rollback

Enable comparison between runs

Entity Relationships Summary

One Article has many Article Windows

One Article has many Comments

One Comment produces one Comment Feature

One Article produces one Comment Aggregate

One Run produces many entities of all types

Entity Immutability Rules

Once written:

Raw Article entities must never change

Snapshot Article entities must never change

Window features must never change

Comment features must never change

Aggregates must never change

Any change requires a new run with a new run_id.

End of document.
