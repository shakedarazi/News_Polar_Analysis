"""Shared retry-with-backoff wrapper for transient HTTP failures."""

from __future__ import annotations

import time
from typing import Callable, TypeVar

import requests

T = TypeVar("T")

MAX_ATTEMPTS = 3
INITIAL_BACKOFF_SECONDS = 2.0


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        response = exc.response
        return response is not None and response.status_code >= 500
    return False


def fetch_with_retry(fetch_fn: Callable[[], T]) -> T:
    """Call `fetch_fn`, retrying transient failures with exponential backoff.

    Transient failures (timeout, connection error, HTTP 5xx) are retried up to
    `MAX_ATTEMPTS - 1` times, sleeping `INITIAL_BACKOFF_SECONDS` and doubling
    each retry (2s, then 4s). Any other exception (HTTP 4xx, etc.) propagates
    immediately on the first attempt with no retry.
    """
    backoff = INITIAL_BACKOFF_SECONDS
    attempt = 0
    while True:
        attempt += 1
        try:
            return fetch_fn()
        except Exception as exc:
            if attempt >= MAX_ATTEMPTS or not _is_transient(exc):
                raise
            time.sleep(backoff)
            backoff *= 2
