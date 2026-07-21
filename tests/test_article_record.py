"""Tests for article record building."""

from datetime import datetime, timezone

from src.crawling.extract_article import build_article_record


def test_build_article_record_fields():
    when = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    record = build_article_record(
        source="ynet",
        title="כותרת",
        text="גוף המאמר",
        url="https://www.ynet.co.il/news/article/example?utm_source=test",
        run_id="run_test",
        ingestion_time=when,
    )
    assert record["source"] == "ynet"
    assert record["title"] == "כותרת"
    assert record["text"] == "גוף המאמר"
    assert record["ingestion_run_id"] == "run_test"
    assert record["first_seen_at"] == when
    assert len(record["article_id"]) == 64
    assert "utm" not in record["canonical_url"]
