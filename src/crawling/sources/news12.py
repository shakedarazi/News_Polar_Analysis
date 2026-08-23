"""News 12 (N12) crawler — articles hosted on mako.co.il."""

from src.crawling.base import BaseCrawler
from src.crawling.extract_article import fetch_html
from src.crawling.extractors import extract_article_with_fallback
from src.crawling.rss_utils import discover_from_feeds

RSS_FEEDS = [
    "https://rcs.mako.co.il/rss/31750a2610f26110VgnVCM1000005201000aRCRD.xml",
]

# News 12 articles are hosted on mako.co.il and share its DOM template.
DOM_SELECTORS = ["[class*='ArticleBodyWrapper'] p"]


class News12Crawler(BaseCrawler):
    source_name = "news12"

    def discover_urls(self, limit: int) -> list[str]:
        return discover_from_feeds(RSS_FEEDS, limit)

    def extract_article(self, url: str) -> dict[str, str]:
        html = fetch_html(url)
        title, text = extract_article_with_fallback(html, DOM_SELECTORS)
        if len(text) < 100:
            raise ValueError(f"Extracted text too short ({len(text)} chars)")
        return {"title": title, "text": text, "url": url}
