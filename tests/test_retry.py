"""Tests for the shared retry-with-backoff wrapper."""

import pytest
import requests

from src.crawling import retry as retry_module
from src.crawling.retry import fetch_with_retry, is_transient_failure


def _http_error(status_code: int) -> requests.exceptions.HTTPError:
    response = requests.Response()
    response.status_code = status_code
    return requests.exceptions.HTTPError(response=response)


def test_retries_transient_failures_then_succeeds(monkeypatch):
    sleeps = []
    monkeypatch.setattr(retry_module.time, "sleep", lambda s: sleeps.append(s))
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.exceptions.ConnectionError("boom")
        return "ok"

    assert fetch_with_retry(flaky) == "ok"
    assert calls["n"] == 3
    assert sleeps == [2.0, 4.0]


def test_5xx_is_treated_as_transient_and_retried(monkeypatch):
    monkeypatch.setattr(retry_module.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def flaky_server():
        calls["n"] += 1
        if calls["n"] < 2:
            raise _http_error(503)
        return "ok"

    assert fetch_with_retry(flaky_server) == "ok"
    assert calls["n"] == 2


def test_permanent_4xx_failure_raises_with_no_retry(monkeypatch):
    sleeps = []
    monkeypatch.setattr(retry_module.time, "sleep", lambda s: sleeps.append(s))
    calls = {"n": 0}

    def not_found():
        calls["n"] += 1
        raise _http_error(404)

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_with_retry(not_found)

    assert calls["n"] == 1
    assert sleeps == []


def test_transient_failure_exhausts_retries_and_raises(monkeypatch):
    sleeps = []
    monkeypatch.setattr(retry_module.time, "sleep", lambda s: sleeps.append(s))
    calls = {"n": 0}

    def always_times_out():
        calls["n"] += 1
        raise requests.exceptions.Timeout("slow")

    with pytest.raises(requests.exceptions.Timeout):
        fetch_with_retry(always_times_out)

    assert calls["n"] == 3
    assert sleeps == [2.0, 4.0]


def test_is_transient_failure_matches_retry_policy():
    assert is_transient_failure(requests.exceptions.Timeout("slow"))
    assert is_transient_failure(requests.exceptions.ConnectionError("down"))
    assert is_transient_failure(_http_error(502))
    assert not is_transient_failure(_http_error(404))
    assert not is_transient_failure(ValueError("bad payload"))
