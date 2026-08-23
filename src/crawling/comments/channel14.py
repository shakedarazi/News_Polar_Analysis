"""Channel 14 (c14.co.il) WordPress comments API."""

from __future__ import annotations

import re

import requests

from src.crawling.comments.models import RawComment
from src.crawling.retry import fetch_with_retry
from src.crawling.rss_utils import BROWSER_HEADERS

API_URL = "https://www.c14.co.il/wp-json/now14-api/v1/comments"


def channel14_post_id(url: str) -> int:
    match = re.search(r"/article/(\d+)", url)
    if not match:
        raise ValueError(f"Cannot extract post id from URL: {url}")
    return int(match.group(1))


def fetch_comments(article_url: str) -> list[RawComment]:
    post_id = channel14_post_id(article_url)

    def _do_fetch() -> requests.Response:
        response = requests.get(
            API_URL,
            params={"article_id": post_id},
            headers=BROWSER_HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        return response

    response = fetch_with_retry(_do_fetch)
    payload = response.json()
    if not isinstance(payload, list):
        return []

    comments: list[RawComment] = []
    for item in payload:
        text = (item.get("content") or "").strip()
        if not text:
            continue
        comments.append(
            RawComment(
                source_comment_id=str(item["id"]),
                text=text,
                author=item.get("author"),
                like_count=int(item.get("likes") or 0),
            )
        )
    return comments
