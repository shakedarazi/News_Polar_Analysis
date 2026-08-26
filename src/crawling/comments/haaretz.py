"""Haaretz comments (client-rendered; requires Playwright)."""

from __future__ import annotations

import os
import re
from datetime import date, datetime
from pathlib import Path

from src.crawling.comments.models import RawComment

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"/(\d{4}-\d{2}-\d{2})/")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

GOTO_TIMEOUT_MS = 25_000
COMMENTS_BTN_TIMEOUT_MS = 8_000
MAX_LOAD_MORE_CLICKS = 15

_EXTRACT_JS = """
() => {
  const articles = document.querySelectorAll('#comments-section article[data-testid="comment"]');
  return Array.from(articles).map((el) => {
    const rank = el.querySelector('span.x1rbjxxp')?.textContent?.trim() || '';
    const author = el.querySelector('address')?.textContent?.trim() || null;
    const time = el.querySelector('span.xlyc7x9')?.textContent?.trim() || null;
    const text = el.querySelector('[data-testid="comment-text"]')?.innerText?.trim() || '';
    const likeText = el.querySelector('[data-testid="like-btn"]')?.textContent || '';
    const likeMatch = likeText.match(/(\\d+)/);
    return { rank, author, time, text, like_count: likeMatch ? parseInt(likeMatch[1], 10) : 0 };
  });
}
"""


def haaretz_article_id(url: str) -> str:
    match = _UUID_RE.search(url)
    if not match:
        raise ValueError(f"No Haaretz article UUID in URL: {url}")
    return match.group(0)


def _article_date_from_url(url: str) -> date | None:
    match = _DATE_RE.search(url)
    if not match:
        return None
    return date.fromisoformat(match.group(1))


def _parse_published_at(url: str, time_str: str | None) -> datetime | None:
    if not time_str:
        return None
    match = _TIME_RE.match(time_str.strip())
    if not match:
        return None
    article_date = _article_date_from_url(url)
    if not article_date:
        return None
    return datetime(
        article_date.year,
        article_date.month,
        article_date.day,
        int(match.group(1)),
        int(match.group(2)),
    )


def _ensure_playwright_browsers_path() -> None:
    if "PLAYWRIGHT_BROWSERS_PATH" in os.environ:
        return
    default = Path.home() / "Library" / "Caches" / "ms-playwright"
    if default.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(default)


def _is_playwright_timeout(exc: Exception) -> bool:
    module = getattr(type(exc), "__module__", "") or ""
    return type(exc).__name__ == "TimeoutError" and "playwright" in module


def _load_all_comments(page) -> list[dict]:
    """Open the comments panel and paginate. Missing UI is an empty list, not an error.

    A loaded page with no comments button (paywall, closed thread, layout change)
    must not raise — otherwise the article is retried forever and blocks analyze.
    A timeout loading the page itself still propagates so the caller can retry.
    """
    try:
        page.locator('[data-testid="comments-btn"]').first.click(timeout=COMMENTS_BTN_TIMEOUT_MS)
    except Exception as exc:
        if _is_playwright_timeout(exc):
            return []
        raise
    page.wait_for_timeout(2_000)

    for _ in range(MAX_LOAD_MORE_CLICKS):
        articles = page.locator('#comments-section article[data-testid="comment"]')
        count = articles.count()
        more = page.locator('button:has-text("הצג עוד")')
        if more.count() == 0:
            break
        more.first.click()
        page.wait_for_timeout(1_500)
        if articles.count() <= count:
            break

    return page.evaluate(_EXTRACT_JS)


def fetch_comments(article_url: str) -> list[RawComment]:
    _ensure_playwright_browsers_path()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Haaretz comments require Playwright. Install: pip install playwright && playwright install chromium"
        ) from exc

    url = article_url.rstrip("/")
    if "#comments-section" not in url:
        url += "#comments-section"

    raw_items: list[dict]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=_USER_AGENT, locale="he-IL")
            page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
            page.wait_for_timeout(2_000)
            raw_items = _load_all_comments(page)
        finally:
            browser.close()

    comments: list[RawComment] = []
    for item in raw_items:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        rank = str(item.get("rank") or len(comments) + 1)
        comments.append(
            RawComment(
                source_comment_id=rank,
                text=text,
                author=item.get("author"),
                like_count=int(item.get("like_count") or 0),
                published_at=_parse_published_at(article_url, item.get("time")),
            )
        )

    return comments
