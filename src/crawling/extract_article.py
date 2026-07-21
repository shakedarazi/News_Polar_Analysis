"""Shared article extraction helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from src.common.canonical_url import canonicalize_url
from src.common.hashing import article_id_from_url
from src.crawling.rss_utils import BROWSER_HEADERS

DEFAULT_HEADERS = BROWSER_HEADERS


def fetch_html(url: str, *, timeout: int = 20) -> str:
    import requests

    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def extract_title_and_text(html: str, selectors: list[str]) -> tuple[str, str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    title = ""
    title_el = soup.select_one("h1") or soup.select_one("meta[property='og:title']")
    if title_el is not None:
        if title_el.name == "meta":
            title = title_el.get("content", "").strip()
        else:
            title = title_el.get_text(strip=True)

    paragraphs: list[str] = []
    for selector in selectors:
        for element in soup.select(selector):
            text = element.get_text(strip=True)
            if text:
                paragraphs.append(text)
        if paragraphs:
            break

    text = "\n".join(paragraphs)
    return title, text


def build_article_record(
    *,
    source: str,
    title: str,
    text: str,
    url: str,
    run_id: str,
    ingestion_time: datetime | None = None,
) -> dict:
    when = ingestion_time or datetime.now(timezone.utc)
    return {
        "article_id": article_id_from_url(url),
        "canonical_url": canonicalize_url(url),
        "source": source,
        "title": title or None,
        "text": text,
        "first_seen_at": when,
        "ingestion_run_id": run_id,
    }
