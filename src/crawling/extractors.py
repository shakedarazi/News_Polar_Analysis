"""Shared HTML article extractors."""

from __future__ import annotations

import json

from bs4 import BeautifulSoup


def title_from_soup(soup: BeautifulSoup) -> str:
    title_el = soup.select_one("h1") or soup.select_one("meta[property='og:title']")
    if title_el is None:
        return ""
    if title_el.name == "meta":
        return title_el.get("content", "").strip()
    return title_el.get_text(strip=True)


def extract_json_ld_news_article(html: str, *, min_len: int = 100) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    title = title_from_soup(soup)

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type")
            types = item_type if isinstance(item_type, list) else [item_type]
            if "NewsArticle" not in types and item_type != "NewsArticle":
                continue
            body = (item.get("articleBody") or "").strip()
            if len(body) >= min_len:
                headline = (item.get("headline") or "").strip()
                return title or headline, body

    og = soup.select_one("meta[property='og:description']")
    if og is not None:
        desc = og.get("content", "").strip()
        if len(desc) >= min_len:
            return title, desc

    return title, ""


def extract_article_paragraphs(
    html: str,
    selectors: list[str],
    *,
    min_len: int = 100,
    min_paragraph_len: int = 30,
) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    title = title_from_soup(soup)

    for selector in selectors:
        paragraphs = [
            element.get_text(strip=True)
            for element in soup.select(selector)
            if len(element.get_text(strip=True)) >= min_paragraph_len
        ]
        if paragraphs:
            text = "\n\n".join(paragraphs)
            if len(text) >= min_len:
                return title, text

    return title, ""
