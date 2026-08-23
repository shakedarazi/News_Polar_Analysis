---
status: accepted
---

# Parallelize crawl across sources; add retry, alerting, and a per-run observability table

`pipeline/crawl.py` was fully sequential — across sources and across articles within a source — with zero retry on
HTTP failures. This was slow (6 sources processed one after another) and fragile (any transient network blip
became a permanent article failure). Postgres access is already per-call/connection (`src/db/connection.py`), not
a shared global connection, so it's safe to drive it from multiple threads.

We decided: run sources concurrently (one worker per source — 6 sources today — guarded by a lock around the
shared `known_ids` set), keep article processing sequential *within* a source, and add up to 2 retries
(exponential backoff, 2s/4s) for transient failures only (timeout, connection error, HTTP 5xx) — not for HTTP 4xx
or article-extraction failures, which are permanent by definition (see [[Transient failure]] /
[[Permanent failure]] in CONTEXT.md).

We also decided to add a `ingestion_runs` table, one row per `(run_id, source)`, since there was previously no way
to query "how did last week's runs go" without grepping log files — and log-file-only observability doesn't scale
once sources run in parallel and interleave their output. A source is flagged for operator attention (WARNING log)
when its article-failure rate exceeds 30% in a single run, but only once at least 5 articles were discovered (to
avoid noise on tiny RSS batches).

`scripts/run_ingestion.sh` used unqualified `set -e`, so any single failing step (crawl, comments, analyze) aborted
the rest of the pipeline — including steps with no real dependency on the failed one. We decided each pipeline
step should run regardless of earlier step failures, while the script still exits non-zero overall if *any* step
failed, so cron/monitoring still catches it. Mechanically: only the python step invocations are wrapped in
`... || step_failed=1`; `set -e`/`set -u` stay on for the rest of the script (paths, mkdir, etc.) so unrelated
scripting bugs still fail loudly.

This is scoped to the current Postgres-backed pipeline (`pipeline/crawl.py`), not the aspirational Airflow/GCS
design in `docs/pipelines/ingestion_dag.md` — that document's article-level worker-pool model is a separate,
not-yet-built target architecture.
