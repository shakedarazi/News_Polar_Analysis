"""Thread-safe wrapper around the in-memory set of known article IDs.

Shared by every source worker when crawl runs sources concurrently
(`pipeline/crawl.run_all_sources`). An unguarded `if aid in known_ids: ...
known_ids.add(aid)` sequence is a check-then-act race: two workers could
both see an ID as unknown and both proceed before either records it. This
wraps membership-check and add in a single locked operation instead.
"""

from __future__ import annotations

import threading


class KnownIds:
    def __init__(self, ids: set[str] | None = None) -> None:
        self._ids = set(ids) if ids is not None else set()
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._ids)

    def check_and_add(self, article_id: str) -> bool:
        """Atomically check membership and add if absent.

        Returns True if `article_id` was newly added (proceed), False if
        it was already present (skip as a duplicate).
        """
        with self._lock:
            if article_id in self._ids:
                return False
            self._ids.add(article_id)
            return True
