"""Tests for the thread-safe KnownIds check-and-add wrapper."""

import threading

from src.crawling.known_ids import KnownIds


def test_check_and_add_returns_true_the_first_time_false_after():
    ids = KnownIds()

    assert ids.check_and_add("a") is True
    assert ids.check_and_add("a") is False
    assert len(ids) == 1


def test_seeded_ids_are_treated_as_already_known():
    ids = KnownIds({"a"})

    assert ids.check_and_add("a") is False
    assert ids.check_and_add("b") is True
    assert len(ids) == 2


def test_concurrent_check_and_add_on_the_same_id_has_exactly_one_winner():
    """A barrier forces every thread to call check_and_add for the same ID
    at essentially the same instant - controlled contention, rather than
    hoping real thread scheduling happens to produce an overlap. Without
    the internal lock, an unguarded check-then-add would let more than one
    thread see the ID as absent and both "win"; the lock guarantees exactly
    one winner regardless of how the threads are actually scheduled.
    """
    ids = KnownIds()
    thread_count = 20
    start = threading.Barrier(thread_count)
    results: list[bool] = [None] * thread_count  # type: ignore[list-item]

    def worker(index):
        start.wait(timeout=2)
        results[index] = ids.check_and_add("same-id")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert sum(1 for r in results if r is True) == 1
    assert sum(1 for r in results if r is False) == thread_count - 1
    assert len(ids) == 1


def test_concurrent_check_and_add_on_distinct_ids_loses_no_updates():
    ids = KnownIds()
    thread_count = 20
    start = threading.Barrier(thread_count)

    def worker(index):
        start.wait(timeout=2)
        ids.check_and_add(f"id-{index}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(ids) == thread_count
