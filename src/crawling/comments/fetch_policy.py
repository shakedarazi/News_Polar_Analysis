"""Comment-fetch queue policy: round-robin, per-source caps, permanent vs transient."""

from __future__ import annotations

from collections import defaultdict, deque

import requests


def select_comment_fetch_batch(
    articles: list[dict],
    *,
    limit: int | None = None,
    per_source_caps: dict[str, int] | None = None,
) -> list[dict]:
    """Interleave articles by source so one slow source cannot starve the rest.

    `articles` should already be ordered by recency (e.g. first_seen_at DESC).
    Caps are applied per source before round-robin; `limit` is the overall cap.
    """
    by_source: dict[str, deque[dict]] = defaultdict(deque)
    for article in articles:
        by_source[article["source"]].append(article)

    if per_source_caps:
        for source, cap in per_source_caps.items():
            if cap <= 0 or source not in by_source:
                continue
            by_source[source] = deque(list(by_source[source])[:cap])

    queues: deque[tuple[str, deque[dict]]] = deque(by_source.items())
    selected: list[dict] = []
    while queues and (limit is None or len(selected) < limit):
        source, queue = queues.popleft()
        if not queue:
            continue
        selected.append(queue.popleft())
        if queue:
            queues.append((source, queue))
    return selected


def is_permanent_comment_failure(exc: Exception) -> bool:
    """True when retrying this article next run cannot help.

    HTTP 4xx and extraction errors (missing id / page payload) are permanent.
    Timeouts, connection errors, HTTP 5xx, and Playwright load failures are not
    — those stay `comments_fetched_at IS NULL` and are retried later.
    """
    if isinstance(exc, requests.exceptions.HTTPError):
        response = exc.response
        return response is not None and response.status_code < 500
    return isinstance(exc, ValueError)
