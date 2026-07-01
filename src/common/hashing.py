"""Deterministic hashing utilities."""

import hashlib

from src.common.canonical_url import canonicalize_url


def article_id_from_url(url: str) -> str:
    """Compute stable article_id from canonical URL."""
    canonical = canonicalize_url(url)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
