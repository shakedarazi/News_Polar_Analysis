#!/usr/bin/env python3
"""Probe RSS feeds and article extraction for Israeli news sites."""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MIN_TEXT = 100

# Haaretz blocks non-browser User-Agents on RSS (403).
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
}


@dataclass
class ProbeResult:
    source_name: str
    rss_urls: list[str]
    sample_article_url: str | None
    extraction_method: str | None
    title_selector: str | None
    text_length: int
    title: str | None
    notes: str = ""


def fetch_html(url: str) -> str:
    r = requests.get(url, headers=BROWSER_HEADERS, timeout=25)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def try_rss(url: str) -> tuple[bool, list[str], str]:
    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=20, allow_redirects=True)
        if r.status_code != 200:
            return False, [], f"HTTP {r.status_code} -> {r.url}"
        text = r.text
        if "<rss" not in text.lower() and "<feed" not in text.lower():
            return False, [], "not RSS/XML"
        feed = feedparser.parse(text)
        links = [e.link for e in feed.entries if getattr(e, "link", "").startswith("http")]
        if not links:
            return False, [], "no links"
        return True, links, f"{len(links)} entries @ {r.url}"
    except Exception as ex:
        return False, [], str(ex)


def json_ld_news_article(soup: BeautifulSoup) -> tuple[str, str]:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if not isinstance(item, dict):
                continue
            t = item.get("@type")
            types = t if isinstance(t, list) else [t]
            if "NewsArticle" not in types and t != "NewsArticle":
                continue
            body = (item.get("articleBody") or "").strip()
            headline = (item.get("headline") or "").strip()
            if body:
                return headline, body
    return "", ""


def probe_article(url: str, css_candidates: list[str], title_candidates: list[str]) -> ProbeResult:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    title_sel = ""
    title = ""
    for sel in title_candidates:
        el = soup.select_one(sel)
        if el is not None:
            title = el.get_text(strip=True)
            title_sel = sel
            break
    if not title:
        og = soup.select_one("meta[property='og:title']")
        if og:
            title = (og.get("content") or "").strip()
            title_sel = "meta[property='og:title']"

    h_ld, body_ld = json_ld_news_article(soup)
    if not title and h_ld:
        title, title_sel = h_ld, "json-ld headline"
    if len(body_ld) >= MIN_TEXT:
        return ProbeResult("", [], url, "json-ld NewsArticle articleBody", title_sel, len(body_ld), title)

    for sel in css_candidates:
        root = soup.select_one(sel)
        if root is None:
            continue
        text = root.get_text("\n", strip=True)
        if len(text) >= MIN_TEXT:
            return ProbeResult("", [], url, f"css: {sel}", title_sel, len(text), title)

    og = soup.select_one("meta[property='og:description']")
    og_text = (og.get("content") or "").strip() if og else ""
    if len(og_text) >= MIN_TEXT:
        return ProbeResult("", [], url, "og:description fallback", title_sel, len(og_text), title)

    best = body_ld or og_text
    return ProbeResult("", [], url, "failed/partial", title_sel, len(best), title)


SITE_FEEDS: dict[str, list[str]] = {
    "haaretz": [
        "https://www.haaretz.co.il/srv/rss---feedly",
        "https://www.haaretz.co.il/srv/rss---feedly?section=news",
    ],
    "mako": [
        "https://rcs.mako.co.il/rss/news-israel.xml",
        "https://rcs.mako.co.il/rss/news-world.xml",
        "https://rcs.mako.co.il/rss/news-law.xml",
    ],
    "news12": [
        "https://rcs.mako.co.il/rss/31750a2610f26110VgnVCM1000005201000aRCRD.xml",
    ],
    "reshet13": [
        "https://13news.co.il/feed/",
        "https://13tv.co.il/rss/",
    ],
    "channel14": [
        "https://www.now14.co.il/rss",
        "https://www.c14.co.il/feed/",
    ],
}

SITE_EXTRACT: dict[str, tuple[list[str], list[str]]] = {
    "haaretz": (["h1"], ["[data-test='articleBody']", "div.article-body", "article"]),
    "mako": (["h1"], ["div.ArticleBody", "div[itemprop='articleBody']"]),
    "news12": (["h1"], ["div.ArticleBody", "div[itemprop='articleBody']"]),
    "reshet13": (["h1"], []),  # json-ld only in practice
    "channel14": (["h1"], ["article p", ".entry-content", ".post-content"]),
}


def discover_reshet13_urls(limit: int = 5) -> list[str]:
    html = fetch_html("https://13tv.co.il/news/newsfeed/")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return []
    data = json.loads(m.group(1))
    links: list[str] = []

    def walk(o: object) -> None:
        if isinstance(o, str) and "/item/news/newsfeed/article-" in o:
            path = o if o.startswith("http") else urljoin("https://13tv.co.il/", o.lstrip("/"))
            links.append(path.replace("https://13tv.co.il//", "https://13tv.co.il/"))
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    out: list[str] = []
    for link in links:
        if link not in out:
            out.append(link)
        if len(out) >= limit:
            break
    return out


def probe_site(name: str) -> ProbeResult:
    rss_ok: list[str] = []
    notes: list[str] = []
    article_links: list[str] = []

    for rss in SITE_FEEDS[name]:
        ok, links, note = try_rss(rss)
        notes.append(f"{rss}: {'OK' if ok else 'fail'} ({note})")
        if ok:
            rss_ok.append(note.split(" @ ")[-1] if " @ " in note else rss)
            if not article_links:
                article_links = links

    sample_url: str | None = None
    if name == "reshet13" and not rss_ok:
        discovered = discover_reshet13_urls()
        notes.append(f"newsfeed __NEXT_DATA__: {len(discovered)} article URLs")
        article_links = discovered

    for link in article_links:
        if "/video" in link or "/gallery" in link:
            continue
        sample_url = link
        break
    if not sample_url and article_links:
        sample_url = article_links[0]

    if not sample_url:
        return ProbeResult(name, rss_ok, None, None, None, 0, None, "; ".join(notes))

  # reshet13: ignore stale 13news.co.il single-entry feed for "working" RSS
    if name == "reshet13":
        rss_ok = [u for u in rss_ok if "13news.co.il" not in u]

    titles, css = SITE_EXTRACT[name]
    partial = probe_article(sample_url, css, titles)
    return ProbeResult(
        name,
        rss_ok,
        sample_url,
        partial.extraction_method,
        partial.title_selector,
        partial.text_length,
        partial.title,
        "; ".join(notes),
    )


def main() -> None:
    results = [probe_site(n) for n in SITE_FEEDS]
    print(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
