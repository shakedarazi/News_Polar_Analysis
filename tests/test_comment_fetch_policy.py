"""Tests for comment-fetch queue policy (round-robin, caps, permanent errors)."""

import requests

from src.crawling.comments.fetch_policy import (
    is_permanent_comment_failure,
    select_comment_fetch_batch,
)


def _article(source: str, n: int) -> dict:
    return {
        "article_id": f"{source}-{n}",
        "source": source,
        "canonical_url": f"https://example.com/{source}/{n}",
        "title": f"{source} {n}",
    }


def test_round_robin_interleaves_sources():
    articles = [
        _article("haaretz", 1),
        _article("haaretz", 2),
        _article("haaretz", 3),
        _article("ynet", 1),
        _article("ynet", 2),
        _article("mako", 1),
    ]
    selected = select_comment_fetch_batch(articles, limit=6)
    sources = [row["source"] for row in selected]
    assert sources == ["haaretz", "ynet", "mako", "haaretz", "ynet", "haaretz"]


def test_haaretz_cap_does_not_starve_other_sources():
    articles = [_article("haaretz", i) for i in range(20)] + [
        _article("ynet", i) for i in range(5)
    ]
    selected = select_comment_fetch_batch(
        articles, limit=12, per_source_caps={"haaretz": 3}
    )
    sources = [row["source"] for row in selected]
    assert sources.count("haaretz") == 3
    assert sources.count("ynet") == 5
    assert sources[0] == "haaretz"
    assert "ynet" in sources[:2]


def test_overall_limit_applied_after_interleave():
    articles = [_article("ynet", i) for i in range(10)] + [
        _article("mako", i) for i in range(10)
    ]
    selected = select_comment_fetch_batch(articles, limit=4)
    assert len(selected) == 4
    assert [row["source"] for row in selected] == ["ynet", "mako", "ynet", "mako"]


def test_http_4xx_is_permanent():
    response = requests.Response()
    response.status_code = 404
    exc = requests.exceptions.HTTPError(response=response)
    assert is_permanent_comment_failure(exc)


def test_http_5xx_is_not_permanent():
    response = requests.Response()
    response.status_code = 503
    exc = requests.exceptions.HTTPError(response=response)
    assert not is_permanent_comment_failure(exc)


def test_timeout_is_not_permanent():
    assert not is_permanent_comment_failure(requests.exceptions.Timeout("slow"))


def test_extraction_value_error_is_permanent():
    assert is_permanent_comment_failure(ValueError("vcmId not found in __NEXT_DATA__"))


def test_playwright_style_timeout_is_not_permanent():
    class TimeoutError(Exception):
        pass

    TimeoutError.__module__ = "playwright.sync_api"
    assert not is_permanent_comment_failure(TimeoutError("click timeout"))
