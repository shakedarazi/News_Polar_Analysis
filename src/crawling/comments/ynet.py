"""Ynet talkbacks API."""

from __future__ import annotations

from datetime import datetime

import requests

from src.crawling.comments.models import RawComment
from src.crawling.rss_utils import BROWSER_HEADERS

API_BASE = "https://www.ynet.co.il/iphone/json/api/talkbacks/list/v2"


def ynet_article_id(url: str) -> str:
    return url.rstrip("/").split("/article/")[-1].split("?")[0]


def _parse_pub_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_comments(article_url: str) -> list[RawComment]:
    article_id = ynet_article_id(article_url)
    headers = {**BROWSER_HEADERS, "Referer": "https://www.ynet.co.il/"}
    comments: list[RawComment] = []
    page = 1

    while True:
        response = requests.get(
            f"{API_BASE}/{article_id}/end_to_start/{page}",
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        channel = response.json()["rss"]["channel"]
        items = channel.get("item") or []
        if not isinstance(items, list):
            items = [items] if items else []

        for item in items:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            comments.append(
                RawComment(
                    source_comment_id=str(item["id"]),
                    text=text,
                    author=item.get("author"),
                    like_count=int(item.get("likes") or 0),
                    published_at=_parse_pub_date(item.get("pubDate")),
                )
            )

        if not channel.get("hasMore"):
            break
        page += 1

    return comments
