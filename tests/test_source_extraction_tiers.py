"""Fixture-based tests: every source tries JSON-LD, then its DOM fallback,
then og:description, in that order (see docs on the #7 3-tier fallback)."""

import json

import pytest

from src.crawling.sources import feed_dom, reshet13
from src.crawling.sources.feed_dom import SOURCES, FeedDomCrawler
from src.crawling.sources.reshet13 import Reshet13Crawler

LONG_BODY = ("פסקה עם מספיק תוכן כדי לעבור את סף האורך המינימלי הנדרש לבדיקה. " * 3).strip()
SHORT_JSON_LD_BODY = "קצר מדי"  # under min_len, so JSON-LD tier is skipped


def json_ld_script(body: str) -> str:
    payload = {"@type": "NewsArticle", "headline": "כותרת JSON", "articleBody": body}
    return f'<script type="application/ld+json">{json.dumps(payload)}</script>'


def og_tag(desc: str) -> str:
    return f'<meta property="og:description" content="{desc}" />' if desc else ""


def _feed_dom_crawler(name: str) -> FeedDomCrawler:
    cfg = SOURCES[name]
    return FeedDomCrawler(name, cfg.feeds, cfg.dom_selectors, min_len=cfg.min_len)


@pytest.mark.parametrize(
    "patch_module, crawler_factory, dom_wrapper_open, dom_wrapper_close",
    [
        (feed_dom, lambda: _feed_dom_crawler("haaretz"), '<div data-testid="article-body-wrapper"><p data-testid="rich-text">', "</p></div>"),
        (feed_dom, lambda: _feed_dom_crawler("mako"), '<div class="ArticleBodyWrapper_root__abc123"><p>', "</p></div>"),
        (feed_dom, lambda: _feed_dom_crawler("news12"), '<div class="ArticleBodyWrapper_root__abc123"><p>', "</p></div>"),
        (feed_dom, lambda: _feed_dom_crawler("channel14"), '<article><p>', "</p></article>"),
        (reshet13, Reshet13Crawler, '<div class="articleContent_root__xyz"><p>', "</p></div>"),
    ],
)
class TestSourceExtractionTiers:
    def make_html(self, dom_open, dom_close, *, json_ld: str = "", dom_body: str = "", og: str = "") -> str:
        return f"""
        <html><head>{json_ld}{og_tag(og)}</head>
        <body><h1>כותרת H1</h1>
          {dom_open}{dom_body}{dom_close}
        </body></html>
        """

    def test_prefers_json_ld_when_present(self, monkeypatch, patch_module, crawler_factory, dom_wrapper_open, dom_wrapper_close):
        html = self.make_html(
            dom_wrapper_open, dom_wrapper_close,
            json_ld=json_ld_script(LONG_BODY), dom_body="טקסט DOM שלא אמור להיבחר כאן בכלל",
        )
        monkeypatch.setattr(patch_module, "fetch_html", lambda url: html)
        crawler = crawler_factory()

        result = crawler.extract_article("https://example.com/a")

        assert result["text"] == LONG_BODY
        assert "טקסט DOM" not in result["text"]

    def test_falls_back_to_dom_when_json_ld_missing(
        self, monkeypatch, patch_module, crawler_factory, dom_wrapper_open, dom_wrapper_close
    ):
        html = self.make_html(
            dom_wrapper_open, dom_wrapper_close,
            json_ld=json_ld_script(SHORT_JSON_LD_BODY), dom_body=LONG_BODY,
            og="תיאור מטא שלא אמור להיבחר כי יש DOM",
        )
        monkeypatch.setattr(patch_module, "fetch_html", lambda url: html)
        crawler = crawler_factory()

        result = crawler.extract_article("https://example.com/a")

        assert result["text"] == LONG_BODY

    def test_falls_back_to_og_description_when_json_ld_and_dom_missing(
        self, monkeypatch, patch_module, crawler_factory, dom_wrapper_open, dom_wrapper_close
    ):
        html = f"""
        <html><head>{og_tag(LONG_BODY)}</head><body><h1>כותרת H1</h1></body></html>
        """
        monkeypatch.setattr(patch_module, "fetch_html", lambda url: html)
        crawler = crawler_factory()

        result = crawler.extract_article("https://example.com/a")

        assert result["text"] == LONG_BODY

    def test_raises_when_nothing_matches(self, monkeypatch, patch_module, crawler_factory, dom_wrapper_open, dom_wrapper_close):
        html = "<html><body><h1>כותרת H1</h1><p>קצר מדי</p></body></html>"
        monkeypatch.setattr(patch_module, "fetch_html", lambda url: html)
        crawler = crawler_factory()

        with pytest.raises(ValueError):
            crawler.extract_article("https://example.com/a")
