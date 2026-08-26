"""Tests for Haaretz comment UI handling (missing button, pagination cap)."""

from src.crawling.comments.haaretz import (
    MAX_LOAD_MORE_CLICKS,
    _is_playwright_timeout,
    _load_all_comments,
)


class _PlaywrightTimeoutError(Exception):
    pass


_PlaywrightTimeoutError.__name__ = "TimeoutError"
_PlaywrightTimeoutError.__module__ = "playwright.sync_api"


class _Locator:
    def __init__(self, page: "_FakePage", selector: str):
        self._page = page
        self._selector = selector

    @property
    def first(self) -> "_Locator":
        return self

    def click(self, timeout: int | None = None) -> None:
        if "comments-btn" in self._selector:
            if self._page.comments_btn_error is not None:
                raise self._page.comments_btn_error
            self._page.panel_open = True
            return
        if "הצג עוד" in self._selector:
            self._page.load_more_clicks += 1
            self._page.comment_count += 1

    def count(self) -> int:
        if "comments-btn" in self._selector:
            return 1
        if "הצג עוד" in self._selector:
            return 1 if self._page.has_more else 0
        return self._page.comment_count


class _FakePage:
    def __init__(
        self,
        *,
        comments_btn_error: Exception | None = None,
        has_more: bool = False,
        comment_count: int = 0,
    ):
        self.comments_btn_error = comments_btn_error
        self.has_more = has_more
        self.comment_count = comment_count
        self.load_more_clicks = 0
        self.panel_open = False
        self.evaluated = False

    def locator(self, selector: str) -> _Locator:
        return _Locator(self, selector)

    def wait_for_timeout(self, _ms: int) -> None:
        return None

    def evaluate(self, _js: str) -> list[dict]:
        self.evaluated = True
        return [{"rank": "1", "text": "hi", "author": None, "time": None, "like_count": 0}]


def test_playwright_timeout_detector():
    assert _is_playwright_timeout(_PlaywrightTimeoutError("timeout"))
    assert not _is_playwright_timeout(TimeoutError("builtin"))
    assert not _is_playwright_timeout(RuntimeError("other"))


def test_missing_comments_button_returns_empty_list():
    page = _FakePage(comments_btn_error=_PlaywrightTimeoutError("no button"))
    assert _load_all_comments(page) == []
    assert page.evaluated is False
    assert page.load_more_clicks == 0


def test_load_more_is_capped():
    page = _FakePage(has_more=True, comment_count=2)
    items = _load_all_comments(page)
    assert items
    assert page.load_more_clicks == MAX_LOAD_MORE_CLICKS
    assert page.evaluated is True
