"""Truncate article text for cost-efficient AI classification."""

from __future__ import annotations

import re

MAX_TEXT_CHARS = 1200
MIN_TEXT_CHARS = 400
INITIAL_PARAGRAPHS = 2

MAX_SUMMARY_CHARS = 4000


def _split_paragraphs(text: str) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    parts = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
    if len(parts) > 1:
        return parts

    parts = [part.strip() for part in cleaned.split("\n") if part.strip()]
    return parts if parts else [cleaned]


def truncate_for_classification(text: str) -> str:
    """
    Return a short excerpt for category labeling: first paragraphs, capped at
  1200 chars. Full article text remains stored in the database.
    """
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return ""

    selected = paragraphs[:INITIAL_PARAGRAPHS]
    body = "\n\n".join(selected)

    if len(body) < MIN_TEXT_CHARS:
        for paragraph in paragraphs[len(selected) :]:
            selected.append(paragraph)
            body = "\n\n".join(selected)
            if len(body) >= MIN_TEXT_CHARS:
                break

    if len(body) > MAX_TEXT_CHARS:
        return body[:MAX_TEXT_CHARS].rstrip()

    return body


def truncate_for_summary(text: str) -> str:
    """
    Return an excerpt suitable for full-article summarization: the whole
    article, capped at 4000 chars so long articles stay a bounded-cost prompt.
    """
    cleaned = text.strip()
    if len(cleaned) > MAX_SUMMARY_CHARS:
        return cleaned[:MAX_SUMMARY_CHARS].rstrip()
    return cleaned
