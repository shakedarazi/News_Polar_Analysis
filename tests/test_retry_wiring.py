"""Confirms retry-with-backoff is actually wired into the network fetch points:
extract_article.fetch_html, rss_utils.fetch_feed_xml, and reshet13's custom
feed fetch — not just that the wrapper itself works in isolation.
"""

import json

import requests

from src.crawling import base, extract_article, rss_utils
from src.crawling import retry as retry_module
from src.crawling.base import BaseCrawler
from src.crawling.known_ids import KnownIds
from src.crawling.sources import reshet13


def _fake_response(text: str, status_code: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = text.encode("utf-8")
    return response


class _FetchHtmlCrawler(BaseCrawler):
    source_name = "fetch_html_test"

    def __init__(self, urls):
        self._urls = urls

    def discover_urls(self, limit):
        return self._urls

    def extract_article(self, url):
        html = extract_article.fetch_html(url)
        return {"title": "t", "text": html}


def test_transient_failures_then_success_saves_article_with_no_failure(monkeypatch):
    monkeypatch.setattr(retry_module.time, "sleep", lambda s: None)
    saved = []
    monkeypatch.setattr(base, "save_article", lambda record: saved.append(record))

    calls = {"n": 0}

    def fake_get(url, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.exceptions.ConnectionError("boom")
        return _fake_response("x" * 150)

    monkeypatch.setattr(requests, "get", fake_get)

    crawler = _FetchHtmlCrawler(["https://example.com/a"])
    summary = crawler.crawl(run_id="run_1", delay_seconds=0, known_ids=KnownIds())

    assert calls["n"] == 3
    assert summary.failed == 0
    assert summary.saved == 1
    assert len(saved) == 1


def test_permanent_404_failure_recorded_on_first_attempt_with_no_retry(monkeypatch):
    sleeps = []
    monkeypatch.setattr(retry_module.time, "sleep", lambda s: sleeps.append(s))
    saved = []
    monkeypatch.setattr(base, "save_article", lambda record: saved.append(record))

    calls = {"n": 0}

    def fake_get(url, headers=None, timeout=None):
        calls["n"] += 1
        return _fake_response("", status_code=404)

    monkeypatch.setattr(requests, "get", fake_get)

    crawler = _FetchHtmlCrawler(["https://example.com/missing"])
    summary = crawler.crawl(run_id="run_1", delay_seconds=0, known_ids=KnownIds())

    assert calls["n"] == 1
    assert [s for s in sleeps if s > 0] == []  # no retry backoff; base.crawl()'s own delay_seconds=0 sleep is incidental
    assert summary.failed == 1
    assert summary.saved == 0
    assert saved == []


def test_fetch_feed_xml_retries_transient_failure(monkeypatch):
    monkeypatch.setattr(retry_module.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def fake_get(url, headers=None, timeout=None, allow_redirects=None):
        calls["n"] += 1
        if calls["n"] < 2:
            raise requests.exceptions.Timeout("slow")
        return _fake_response("<rss></rss>")

    monkeypatch.setattr(requests, "get", fake_get)

    xml = rss_utils.fetch_feed_xml("http://fake")

    assert xml == "<rss></rss>"
    assert calls["n"] == 2


def test_reshet13_discover_retries_transient_failure(monkeypatch):
    monkeypatch.setattr(retry_module.time, "sleep", lambda s: None)
    payload = {
        "props": {
            "urls": [
                "https://13tv.co.il/item/news/newsfeed/article-1/",
                "https://13tv.co.il/item/news/newsfeed/article-2/",
            ]
        }
    }
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'

    calls = {"n": 0}

    def fake_get(url, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] < 2:
            raise requests.exceptions.ConnectionError("boom")
        return _fake_response(html)

    monkeypatch.setattr(requests, "get", fake_get)

    urls = reshet13.discover_reshet13_urls()

    assert calls["n"] == 2
    assert urls == [
        "https://13tv.co.il/item/news/newsfeed/article-1/",
        "https://13tv.co.il/item/news/newsfeed/article-2/",
    ]
