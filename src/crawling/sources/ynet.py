"""Ynet news crawler."""

import json

import feedparser

from src.crawling.base import BaseCrawler
from src.crawling.extract_article import fetch_html
from src.crawling.rss_utils import NO_LIMIT, fetch_feed_xml

RSS_FEEDS = [
    "https://www.ynet.co.il/Integration/StoryRss2.xml",
    "https://www.ynet.co.il/Integration/StoryRss1854.xml",
]


def extract_ynet_article(html: str) -> tuple[str, str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    title = ""
    title_el = soup.select_one("h1.mainTitle") or soup.find("h1")
    if title_el is not None:
        title = title_el.get_text(strip=True)

    text = _extract_from_json_ld(soup)
    if not text:
        text = _extract_from_draftjs(soup)

    if not title:
        og = soup.select_one("meta[property='og:title']")
        if og is not None:
            title = og.get("content", "").strip()

    return title, text


def _extract_from_json_ld(soup) -> str:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") != "NewsArticle":
                continue
            body = (item.get("articleBody") or "").strip()
            if body:
                return body
    return ""


def _extract_from_draftjs(soup) -> str:
    root = (
        soup.select_one("div.article-body")
        or soup.select_one("div.ArticleBodyComponent")
        or soup.select_one("[data-contents='true']")
    )
    if root is None:
        return ""

    spans = root.select("span[data-text='true']")
    parts = [span.get_text(strip=True) for span in spans if span.get_text(strip=True)]
    if parts:
        return "\n\n".join(parts)

    return root.get_text("\n", strip=True)


class YnetCrawler(BaseCrawler):
    source_name = "ynet"

    def discover_urls(self, limit: int = NO_LIMIT) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        unlimited = limit <= 0

        for feed_url in RSS_FEEDS:
            try:
                xml = fetch_feed_xml(feed_url)
                feed = feedparser.parse(xml)
            except Exception:
                continue

            for entry in feed.entries:
                link = getattr(entry, "link", None)
                if not link or not link.startswith("http") or link in seen:
                    continue
                seen.add(link)
                urls.append(link)
                if not unlimited and len(urls) >= limit:
                    return urls

        return urls

    def extract_article(self, url: str) -> dict[str, str]:
        html = fetch_html(url)
        title, text = extract_ynet_article(html)

        if len(text) < 100:
            raise ValueError(
                f"Extracted text too short ({len(text)} chars); page structure may have changed"
            )

        return {"title": title, "text": text, "url": url}
