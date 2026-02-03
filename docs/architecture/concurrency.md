architecture/concurrency.md

Concurrency Model and Determinism Constraints

This document defines the concurrency model of the system and explains how parallel execution is handled without breaking determinism, correctness, or reproducibility.

Core Concurrency Principle

Concurrency in the system is strictly limited to the article level.

This means:

Multiple articles may be processed in parallel

A single article is always processed by exactly one worker

There is no parallelism inside an article

Explicit Non-Concurrency Rules

The system explicitly forbids concurrency at the following levels:

No concurrency within a single article

No concurrency within article windows (sentences)

No concurrency within comments of the same article

No shared mutable state between workers

These rules are mandatory and non-negotiable.

Atomic Unit of Work

The atomic unit of execution is:

ArticleJob(article_id)

An ArticleJob represents the full, end-to-end processing of one article.

Each ArticleJob performs the following steps sequentially:

Read immutable article snapshot from GCS

Normalize and split article text into windows

Compute window-level features

Process all comments associated with the article

Aggregate comment-level metrics

Write all outputs to staging storage

Once started, an ArticleJob runs to completion without interruption or interleaving.

Worker Pool Execution Model

Airflow manages a pool of workers.

Each worker:

Pulls exactly one article_id from the queue

Executes one ArticleJob

Writes results independently

Does not communicate with other workers

Workers never:

Share memory

Share counters

Depend on execution order of other workers

Why This Model Is Necessary

This concurrency model ensures:

Deterministic results regardless of execution order

No race conditions

No partial writes or inconsistent state

Easy reasoning about correctness

The same article processed twice will always produce identical outputs.

Big-O Complexity and Parallelism

Algorithmic complexity is independent of concurrency.

Total complexity:
O(sum(tokens_in_articles) + sum(tokens_in_comments))

Parallel execution:

Reduces wall-clock runtime

Does not change asymptotic complexity

Important academic note:
Parallelism improves execution time, not algorithmic complexity.

Ordering Guarantees

Ordering is enforced deterministically at all critical points:

Sentence order is preserved via sentence_idx

Comment order is normalized by sorting on comment_id

Staging outputs are written with explicit keys

No computation depends on arrival order or processing order.

Failure Isolation

If a worker fails while processing an article:

Other ArticleJobs continue unaffected

Partial outputs are discarded

The failed article can be retried safely

This is possible because ArticleJobs are idempotent and isolated.

Why Finer-Grained Parallelism Is Avoided

Parallelism inside an article was intentionally avoided because it would:

Introduce synchronization complexity

Risk non-deterministic ordering

Complicate debugging and reproducibility

Provide limited performance gains

Article-level parallelism provides the best trade-off between speed and correctness.

Concurrency and Future Extensions

Future extensions (e.g., LLM enrichment) must respect the same constraints:

LLM calls must be isolated per article

Results must be versioned

Failures must not affect core metrics

LLM enrichment must never block or alter deterministic outputs