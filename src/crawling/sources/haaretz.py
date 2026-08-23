"""Haaretz news crawler."""

from src.crawling.base import BaseCrawler
from src.crawling.extract_article import fetch_html
from src.crawling.extractors import extract_article_with_fallback
from src.crawling.rss_utils import discover_from_feeds

RSS_FEEDS = [
    "https://www.haaretz.co.il/srv/rss---feedly",
    "https://www.haaretz.co.il/srv/rss---feedly?section=news",
]

DOM_SELECTORS = ["[data-testid='article-body-wrapper'] p[data-testid='rich-text']"]


class HaaretzCrawler(BaseCrawler):
    source_name = "haaretz"

    def discover_urls(self, limit: int) -> list[str]:
        return discover_from_feeds(RSS_FEEDS, limit)

    def extract_article(self, url: str) -> dict[str, str]:
        html = fetch_html(url)
        title, text = extract_article_with_fallback(html, DOM_SELECTORS)
        if len(text) < 100:
            raise ValueError(f"Extracted text too short ({len(text)} chars)")
        return {"title": title, "text": text, "url": url}
