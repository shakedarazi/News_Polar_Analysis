"""Mako (Keshet 12) news crawler."""

from src.crawling.base import BaseCrawler
from src.crawling.extract_article import fetch_html
from src.crawling.extractors import extract_json_ld_news_article
from src.crawling.rss_utils import discover_from_feeds

RSS_FEEDS = [
    "https://rcs.mako.co.il/rss/news-israel.xml",
    "https://rcs.mako.co.il/rss/news-world.xml",
    "https://rcs.mako.co.il/rss/news-law.xml",
    "https://rcs.mako.co.il/rss/news-military.xml",
]


class MakoCrawler(BaseCrawler):
    source_name = "mako"

    def discover_urls(self, limit: int) -> list[str]:
        return discover_from_feeds(RSS_FEEDS, limit)

    def extract_article(self, url: str) -> dict[str, str]:
        html = fetch_html(url)
        title, text = extract_json_ld_news_article(html)
        if len(text) < 100:
            raise ValueError(f"Extracted text too short ({len(text)} chars)")
        return {"title": title, "text": text, "url": url}
