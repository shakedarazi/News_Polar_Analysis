"""Tests for post-ingestion classification hook."""

from src.db.classification import maybe_classify_after_save


def test_maybe_classify_skipped_when_disabled():
    record = {
        "article_id": "abc",
        "source": "ynet",
        "title": "כותרת",
        "text": "טקסט",
    }
    assert maybe_classify_after_save(record, enabled=False) is None
