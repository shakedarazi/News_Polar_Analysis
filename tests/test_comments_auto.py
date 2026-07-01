"""Tests for unsupported-source comment marking."""

from src.crawling.comments.registry import UNSUPPORTED_SOURCES, supports_comments


def test_unsupported_sources_defined():
    assert "reshet13" in UNSUPPORTED_SOURCES
    assert "haaretz" not in UNSUPPORTED_SOURCES


def test_haaretz_supports_comments():
    assert supports_comments("haaretz")
