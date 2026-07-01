"""Tests for polarization window feature extraction."""

from src.features.article_windows import (
    aggregate_article_polarization,
    compute_article_analysis,
    compute_windows,
)


def test_window_polarization_counts() -> None:
    windows = compute_windows(
        article_id="test-article",
        text="הממשלה התנגדה לרפורמה.",
        token_components={
            "הממשלה": "issue",
            "התנגדה": "affective",
            "לרפורמה": "issue",
        },
        lexicon_version="test-v1",
        pipeline_version="0.1.0",
        run_id="test-run",
    )

    assert len(windows) == 1
    window = windows[0]
    assert window.issue_count == 2
    assert window.affective_count == 1
    assert window.polar_count == 3
    assert window.polar_ratio == 1.0


def test_no_matches_yields_null_ratios() -> None:
    windows = compute_windows(
        article_id="test-article",
        text="טקסט ללא מילים במילון.",
        token_components={},
        lexicon_version="test-v1",
        pipeline_version="0.1.0",
        run_id="test-run",
    )

    assert len(windows) == 1
    assert windows[0].polar_count == 0
    assert windows[0].polar_ratio == 0.0


def test_article_aggregation() -> None:
    windows = compute_windows(
        article_id="test-article",
        text="ממשלה. התנגדה.",
        token_components={"ממשלה": "issue", "התנגדה": "affective"},
        lexicon_version="test-v1",
        pipeline_version="0.1.0",
        run_id="test-run",
    )
    article = aggregate_article_polarization(
        windows,
        article_id="test-article",
        lexicon_version="test-v1",
        pipeline_version="0.1.0",
        run_id="test-run",
    )

    assert article.window_count == 2
    assert article.issue_count == 1
    assert article.affective_count == 1
    assert article.polar_count == 2
    assert article.polar_ratio == 1.0


def test_compute_article_analysis_returns_token_matches() -> None:
    analysis = compute_article_analysis(
        article_id="test-article",
        text="ממשלה. התנגדה.",
        token_components={"ממשלה": "issue", "התנגדה": "affective"},
        lexicon_version="test-v1",
        pipeline_version="0.1.0",
        run_id="test-run",
    )

    assert analysis.token_matches == {
        "ממשלה": "issue",
        "התנגדה": "affective",
    }
    assert analysis.article.polar_count == 2
