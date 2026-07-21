"""Normalized comment record from a news source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawComment:
    source_comment_id: str
    text: str
    author: str | None = None
    like_count: int = 0
    published_at: datetime | None = None
