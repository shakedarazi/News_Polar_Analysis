"""Database schema migrations.

There is no version-tracking table by design (see CLAUDE.md): every pipeline
script and every API startup re-applies all of sql/migrations/, and the DDL is
written to be idempotent. That makes *when* migrations run uncontrolled — a
GitHub Actions ingestion step routinely migrates the same Neon database that a
live Render API is serving traffic from.

Two things can go wrong there, and this module defends against both:

  - Two migration passes at once. Serialized with an advisory lock.
  - A migration pass racing ordinary application queries. This is what actually
    failed in production (2026-08-31): migration DDL held ACCESS EXCLUSIVE on
    `articles` and wanted ShareLock for a CREATE INDEX, while a concurrent
    query held its index lock and wanted a RowShareLock on `articles` — a
    lock-order inversion no amount of migration-side serialization can prevent.
    Postgres kills one side; retrying is the standard remedy, and is safe here
    precisely because re-running the whole pass is a no-op.
"""

from __future__ import annotations

import time
from pathlib import Path

from src.db.connection import get_connection

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "sql" / "migrations"

# Arbitrary but fixed key identifying "this repo's migration pass" to
# pg_advisory_xact_lock. Any stable bigint works; it only has to be the same in
# every process, and not collide with another advisory lock on this database.
_MIGRATION_LOCK_ID = 4_171_368_421

# Wait this long for a table lock before giving up an attempt. Without it a
# migration blocked behind a long-running query waits indefinitely, which on
# API startup means the process never finishes booting.
_LOCK_TIMEOUT_MS = 15_000

_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 1.0


def _apply_once(migration_files: list[Path]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Bounded wait, so a stuck attempt fails fast enough to retry
            # rather than hanging the caller.
            cur.execute(f"SET LOCAL lock_timeout = '{_LOCK_TIMEOUT_MS}ms'")
            # Transaction-scoped: released on the commit below, on rollback,
            # or if the process dies. It cannot leak.
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK_ID,))
            for path in migration_files:
                cur.execute(path.read_text(encoding="utf-8"))


def apply_migrations() -> None:
    import psycopg

    if not _MIGRATIONS_DIR.is_dir():
        return
    migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))

    # Only lock-contention failures are retried. A broken migration raises
    # something else and still fails loudly on the first attempt.
    transient = (psycopg.errors.DeadlockDetected, psycopg.errors.LockNotAvailable)

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            _apply_once(migration_files)
            return
        except transient:
            if attempt == _MAX_ATTEMPTS:
                raise
            time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
