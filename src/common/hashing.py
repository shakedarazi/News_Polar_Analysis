"""URL canonicalization and deterministic identifiers."""

from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
    }
)


def canonicalize_url(url: str) -> str:
    """Normalize a URL for stable article identification."""
    parsed = urlparse(url.strip())
    scheme = "https" if parsed.scheme in ("http", "https") else parsed.scheme
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"

    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(sorted(query_pairs))

    return urlunparse((scheme, netloc, path, "", query, ""))


def sha256_hex(value: str) -> str:
    """Return the SHA-256 hex digest of a UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def article_id_from_url(url: str) -> str:
    """Compute article_id = sha256(canonical_url)."""
    return sha256_hex(canonicalize_url(url))


def comment_id_from_text(article_id: str, comment_text: str, local_index: int) -> str:
    """Compute comment_id = sha256(article_id + text + index) when source has no id."""
    return sha256_hex(f"{article_id}:{local_index}:{comment_text}")
