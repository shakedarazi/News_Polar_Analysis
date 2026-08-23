"""Fixture-based tests: every source tries JSON-LD, then its DOM fallback,
then og:description, in that order (see docs on the #7 3-tier fallback)."""

import json

import pytest

from src.crawling.sources import channel14, haaretz, mako, news12, reshet13
from src.crawling.sources.channel14 import Channel14Crawler
from src.crawling.sources.haaretz import HaaretzCrawler
from src.crawling.sources.mako import MakoCrawler
from src.crawling.sources.news12 import News12Crawler
from src.crawling.sources.reshet13 import Reshet13Crawler

CRAWLER_CLASSES = {
    haaretz: HaaretzCrawler,
    mako: MakoCrawler,
    news12: News12Crawler,
    channel14: Channel14Crawler,
    reshet13: Reshet13Crawler,
}

LONG_BODY = ("פסקה עם מספיק תוכן כדי לעבור את סף האורך המינימלי הנדרש לבדיקה. " * 3).strip()
SHORT_JSON_LD_BODY = "קצר מדי"  # under min_len, so JSON-LD tier is skipped


def json_ld_script(body: str) -> str:
    payload = {"@type": "NewsArticle", "headline": "כותרת JSON", "articleBody": body}
    return f'<script type="application/ld+json">{json.dumps(payload)}</script>'


def og_tag(desc: str) -> str:
    return f'<meta property="og:description" content="{desc}" />' if desc else ""


@pytest.mark.parametrize(
    "module, dom_wrapper_open, dom_wrapper_close",
    [
        (haaretz, '<div data-testid="article-body-wrapper"><p data-testid="rich-text">', "</p></div>"),
        (mako, '<div class="ArticleBodyWrapper_root__abc123"><p>', "</p></div>"),
        (news12, '<div class="ArticleBodyWrapper_root__abc123"><p>', "</p></div>"),
        (channel14, '<article><p>', "</p></article>"),
        (reshet13, '<div class="articleContent_root__xyz"><p>', "</p></div>"),
    ],
)
class TestSourceExtractionTiers:
    def make_html(self, module, dom_open, dom_close, *, json_ld: str = "", dom_body: str = "", og: str = "") -> str:
        return f"""
        <html><head>{json_ld}{og_tag(og)}</head>
        <body><h1>כותרת H1</h1>
          {dom_open}{dom_body}{dom_close}
        </body></html>
        """

    def crawler_for(self, module):
        return CRAWLER_CLASSES[module]()

    def test_prefers_json_ld_when_present(self, monkeypatch, module, dom_wrapper_open, dom_wrapper_close):
        html = self.make_html(
            module, dom_wrapper_open, dom_wrapper_close,
            json_ld=json_ld_script(LONG_BODY), dom_body="טקסט DOM שלא אמור להיבחר כאן בכלל",
        )
        monkeypatch.setattr(module, "fetch_html", lambda url: html)
        crawler = self.crawler_for(module)

        result = crawler.extract_article("https://example.com/a")

        assert result["text"] == LONG_BODY
        assert "טקסט DOM" not in result["text"]

    def test_falls_back_to_dom_when_json_ld_missing(
        self, monkeypatch, module, dom_wrapper_open, dom_wrapper_close
    ):
        html = self.make_html(
            module, dom_wrapper_open, dom_wrapper_close,
            json_ld=json_ld_script(SHORT_JSON_LD_BODY), dom_body=LONG_BODY,
            og="תיאור מטא שלא אמור להיבחר כי יש DOM",
        )
        monkeypatch.setattr(module, "fetch_html", lambda url: html)
        crawler = self.crawler_for(module)

        result = crawler.extract_article("https://example.com/a")

        assert result["text"] == LONG_BODY

    def test_falls_back_to_og_description_when_json_ld_and_dom_missing(
        self, monkeypatch, module, dom_wrapper_open, dom_wrapper_close
    ):
        html = f"""
        <html><head>{og_tag(LONG_BODY)}</head><body><h1>כותרת H1</h1></body></html>
        """
        monkeypatch.setattr(module, "fetch_html", lambda url: html)
        crawler = self.crawler_for(module)

        result = crawler.extract_article("https://example.com/a")

        assert result["text"] == LONG_BODY

    def test_raises_when_nothing_matches(self, monkeypatch, module, dom_wrapper_open, dom_wrapper_close):
        html = "<html><body><h1>כותרת H1</h1><p>קצר מדי</p></body></html>"
        monkeypatch.setattr(module, "fetch_html", lambda url: html)
        crawler = self.crawler_for(module)

        with pytest.raises(ValueError):
            crawler.extract_article("https://example.com/a")
