"""Reshet 13 (13tv) news crawler."""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin

import requests

from src.crawling.base import BaseCrawler
from src.crawling.extract_article import fetch_html
from src.crawling.extractors import extract_article_with_fallback
from src.crawling.retry import fetch_with_retry
from src.crawling.rss_utils import BROWSER_HEADERS, NO_LIMIT

NEWSFEED_URL = "https://13tv.co.il/news/newsfeed/"

DOM_SELECTORS = ["[class*='articleContent'] p", "[class*='ArticleBody'] p", "article p"]


def _fetch_newsfeed_html() -> str:
    response = requests.get(NEWSFEED_URL, headers=BROWSER_HEADERS, timeout=25)
    response.raise_for_status()
    return response.text


def discover_reshet13_urls(limit: int = NO_LIMIT) -> list[str]:
    html = fetch_with_retry(_fetch_newsfeed_html)
    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        return []

    data = json.loads(match.group(1))
    candidates: list[str] = []

    def walk(node) -> None:
        if isinstance(node, str):
            if "/item/news/newsfeed/article-" in node:
                url = node if node.startswith("http") else urljoin("https://13tv.co.il/", node.lstrip("/"))
                candidates.append(url.replace("https://13tv.co.il//", "https://13tv.co.il/"))
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)

    seen: set[str] = set()
    urls: list[str] = []
    unlimited = limit <= 0
    for url in candidates:
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
        if not unlimited and len(urls) >= limit:
            break
    return urls


class Reshet13Crawler(BaseCrawler):
    source_name = "reshet13"

    def discover_urls(self, limit: int) -> list[str]:
        return discover_reshet13_urls(limit)

    def extract_article(self, url: str) -> dict[str, str]:
        html = fetch_html(url)
        title, text = extract_article_with_fallback(html, DOM_SELECTORS, min_len=80)
        if len(text) < 80:
            raise ValueError(f"Extracted text too short ({len(text)} chars)")
        return {"title": title, "text": text, "url": url}
