"""Shared HTML article extractors.

Every source follows the same tier order when extracting an article's text:
structured JSON-LD (`extract_json_ld`), then a site-specific DOM/CSS fallback
(`extract_article_paragraphs`), then a generic meta-description fallback
(`extract_og_description`). `extract_article_with_fallback` chains all three
for sources whose DOM fallback is a plain paragraph-selector list; sources
with a bespoke DOM fallback (e.g. ynet's draft.js structure) call the tiers
individually instead.
"""

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


def extract_json_ld(html: str, *, min_len: int = 100) -> tuple[str, str]:
    """Structured-data tier: JSON-LD `NewsArticle.articleBody` only."""
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

    return title, ""


def extract_og_description(html: str, *, min_len: int = 100) -> tuple[str, str]:
    """Generic-meta tier: the page's `og:description` tag."""
    soup = BeautifulSoup(html, "lxml")
    title = title_from_soup(soup)

    og = soup.select_one("meta[property='og:description']")
    if og is not None:
        desc = og.get("content", "").strip()
        if len(desc) >= min_len:
            return title, desc

    return title, ""


def extract_json_ld_news_article(html: str, *, min_len: int = 100) -> tuple[str, str]:
    """JSON-LD, falling back to `og:description` — preserved for callers that
    don't yet distinguish a middle DOM tier."""
    title, body = extract_json_ld(html, min_len=min_len)
    if body:
        return title, body
    return extract_og_description(html, min_len=min_len)


def extract_article_paragraphs(
    html: str,
    selectors: list[str],
    *,
    min_len: int = 100,
    min_paragraph_len: int = 30,
) -> tuple[str, str]:
    """Site-specific DOM tier: the first selector yielding paragraphs wins."""
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


def extract_article_with_fallback(
    html: str,
    dom_selectors: list[str],
    *,
    min_len: int = 100,
    min_paragraph_len: int = 30,
) -> tuple[str, str]:
    """Run the full JSON-LD -> DOM -> og:description tier chain."""
    title, text = extract_json_ld(html, min_len=min_len)
    if len(text) >= min_len:
        return title, text

    dom_title, dom_text = extract_article_paragraphs(
        html, dom_selectors, min_len=min_len, min_paragraph_len=min_paragraph_len
    )
    if len(dom_text) >= min_len:
        return title or dom_title, dom_text

    og_title, og_text = extract_og_description(html, min_len=min_len)
    return title or dom_title or og_title, og_text
