"""Mako / News12 comments API (comments.mako.co.il)."""

from __future__ import annotations

import json
import re
from datetime import datetime

import requests

from src.crawling.comments.models import RawComment
from src.crawling.rss_utils import BROWSER_HEADERS

COMMENTS_API = "https://comments.mako.co.il/api/rest/comments"


def extract_vcm_id(html: str) -> str:
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        raise ValueError("__NEXT_DATA__ not found on page")
    data = json.loads(match.group(1))
    vcm_id = data.get("props", {}).get("pageProps", {}).get("pageData", {}).get("vcmId")
    if not vcm_id:
        raise ValueError("vcmId not found in __NEXT_DATA__")
    return vcm_id


def fetch_comments(article_url: str, *, html: str | None = None) -> list[RawComment]:
    from src.crawling.extract_article import fetch_html

    page_html = html if html is not None else fetch_html(article_url)
    vcm_id = extract_vcm_id(page_html)
    headers = {
        **BROWSER_HEADERS,
        "Accept": "application/json",
        "Referer": "https://comments.mako.co.il/",
    }

    comments: list[RawComment] = []
    cursor: str | None = None

    while True:
        params: dict = {"originId": vcm_id, "limit": 20}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(COMMENTS_API, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        batch = payload.get("comments") or []

        for item in batch:
            text = (item.get("content") or "").strip()
            if not text:
                continue
            published_at = None
            created = item.get("created_at")
            if created:
                try:
                    published_at = datetime.fromisoformat(created.replace(" ", "T", 1))
                except ValueError:
                    pass
            comments.append(
                RawComment(
                    source_comment_id=str(item["id"]),
                    text=text,
                    author=item.get("responder_name"),
                    like_count=0,
                    published_at=published_at,
                )
            )

        cursor = payload.get("cursor")
        if not cursor or not batch:
            break

    return comments
