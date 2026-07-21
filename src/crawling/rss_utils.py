"""Shared RSS discovery helpers."""

from __future__ import annotations

import feedparser
import requests

# limit <= 0 means no cap — use every entry from all feeds
NO_LIMIT = 0

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
}


def fetch_feed_xml(url: str) -> str:
    response = requests.get(url, headers=BROWSER_HEADERS, timeout=25, allow_redirects=True)
    response.raise_for_status()
    return response.text


def discover_from_feeds(feed_urls: list[str], limit: int = NO_LIMIT) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    unlimited = limit <= 0

    for feed_url in feed_urls:
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
