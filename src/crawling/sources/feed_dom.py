"""Generic feed+DOM crawler for sources with no bespoke parsing needs.

Covers sources whose discovery is a plain RSS/feed pull and whose extraction
is the standard JSON-LD -> DOM -> og:description fallback chain
(see extract_article_with_fallback). Sources with real per-site parsing
logic (ynet, reshet13) stay as dedicated BaseCrawler subclasses instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.crawling.base import BaseCrawler
from src.crawling.extract_article import fetch_html
from src.crawling.extractors import extract_article_with_fallback
from src.crawling.rss_utils import discover_from_feeds


@dataclass(frozen=True)
class SourceConfig:
    feeds: list[str] = field(default_factory=list)
    dom_selectors: list[str] = field(default_factory=list)
    min_len: int = 100


SOURCES: dict[str, SourceConfig] = {
    "haaretz": SourceConfig(
        feeds=[
            "https://www.haaretz.co.il/srv/rss---feedly",
            "https://www.haaretz.co.il/srv/rss---feedly?section=news",
        ],
        dom_selectors=["[data-testid='article-body-wrapper'] p[data-testid='rich-text']"],
    ),
    "mako": SourceConfig(
        feeds=[
            "https://rcs.mako.co.il/rss/news-israel.xml",
            "https://rcs.mako.co.il/rss/news-world.xml",
            "https://rcs.mako.co.il/rss/news-law.xml",
            "https://rcs.mako.co.il/rss/news-military.xml",
        ],
        dom_selectors=["[class*='ArticleBodyWrapper'] p"],
    ),
    "news12": SourceConfig(
        # News 12 articles are hosted on mako.co.il and share its DOM template.
        #
        # Dormant since 2026-08-07: this feed's newest item has that date and
        # discovery now returns the same 20 already-stored URLs every run. It is
        # left in place rather than repointed at a live mako feed, because the
        # live ones are already crawled as "mako" and re-crawling them under a
        # second label would double-count one newsroom in every source chart.
        # See "Source" and "Dormant source" in CONTEXT.md.
        feeds=["https://rcs.mako.co.il/rss/31750a2610f26110VgnVCM1000005201000aRCRD.xml"],
        dom_selectors=["[class*='ArticleBodyWrapper'] p"],
    ),
    "channel14": SourceConfig(
        feeds=["https://www.c14.co.il/feed/"],
        dom_selectors=["article p", ".entry-content p"],
    ),
}


class FeedDomCrawler(BaseCrawler):
    def __init__(self, source_name: str, feeds: list[str], dom_selectors: list[str], *, min_len: int = 100):
        self.source_name = source_name
        self.feeds = feeds
        self.dom_selectors = dom_selectors
        self.min_len = min_len

    def discover_urls(self, limit: int) -> list[str]:
        return discover_from_feeds(self.feeds, limit)

    def extract_article(self, url: str) -> dict[str, str]:
        html = fetch_html(url)
        title, text = extract_article_with_fallback(html, self.dom_selectors, min_len=self.min_len)
        if len(text) < self.min_len:
            raise ValueError(f"Extracted text too short ({len(text)} chars)")
        return {"title": title, "text": text, "url": url}
