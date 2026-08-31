"""Migrations must survive a lock-contention loss, but not hide a real error.

The production failure (2026-08-31) was a deadlock between migration DDL and
concurrent application queries, which failed the whole ingestion run. Postgres
picks a victim and aborts it; because re-applying every migration is a no-op,
retrying is the correct response. Anything that is not lock contention must
still fail on the first attempt.
"""

import psycopg
import pytest

import src.db.migrations as migrations


@pytest.fixture
def attempts(monkeypatch):
    """Record each _apply_once call and drive its outcome from a script."""
    calls = []

    def make(outcomes):
        def fake_apply_once(files):
            calls.append(files)
            outcome = outcomes[len(calls) - 1]
            if outcome is not None:
                raise outcome

        monkeypatch.setattr(migrations, "_apply_once", fake_apply_once)
        return calls

    monkeypatch.setattr(migrations.time, "sleep", lambda _s: None)
    return make


def test_succeeds_first_try_without_retrying(attempts):
    calls = attempts([None])
    migrations.apply_migrations()
    assert len(calls) == 1


def test_retries_after_a_deadlock_and_then_succeeds(attempts):
    calls = attempts([psycopg.errors.DeadlockDetected("deadlock detected"), None])
    migrations.apply_migrations()
    assert len(calls) == 2


def test_retries_when_the_lock_timeout_fires(attempts):
    calls = attempts([psycopg.errors.LockNotAvailable("timeout"), None])
    migrations.apply_migrations()
    assert len(calls) == 2


def test_gives_up_after_max_attempts_and_raises(attempts):
    deadlock = psycopg.errors.DeadlockDetected("deadlock detected")
    calls = attempts([deadlock] * migrations._MAX_ATTEMPTS)
    with pytest.raises(psycopg.errors.DeadlockDetected):
        migrations.apply_migrations()
    assert len(calls) == migrations._MAX_ATTEMPTS


def test_a_broken_migration_fails_immediately(attempts):
    # Not lock contention — retrying would only delay a real error.
    calls = attempts([psycopg.errors.SyntaxError("bad SQL"), None])
    with pytest.raises(psycopg.errors.SyntaxError):
        migrations.apply_migrations()
    assert len(calls) == 1
