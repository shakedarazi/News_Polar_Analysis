"""Tests for comment-level polarization scoring."""

from src.features.comments_scoring import compute_comments_analysis

ARTICLE_ID = "article-test-001"
LEXICON_VERSION = "test-lexicon"
PIPELINE_VERSION = "test-pipeline"
RUN_ID = "test-run"


def test_comment_polar_ratios_with_mock_components() -> None:
    comments = [
        {"comment_id": "c1", "text": "ממשלה רפורמה", "like_count": 5},
        {"comment_id": "c2", "text": "שקר בושה", "like_count": 2},
    ]
    token_components = {
        "ממשלה": "issue",
        "רפורמה": "issue",
        "שקר": "affective",
        "בושה": "affective",
    }

    result = compute_comments_analysis(
        ARTICLE_ID,
        comments,
        lexicon_version=LEXICON_VERSION,
        pipeline_version=PIPELINE_VERSION,
        run_id=RUN_ID,
        token_components=token_components,
    )

    assert len(result.comments) == 2
    c1, c2 = result.comments

    assert c1.comment_len == 2
    assert c1.issue_count == 2
    assert c1.affective_count == 0
    assert c1.polar_ratio == 1.0
    assert c1.like_count == 5

    assert c2.comment_len == 2
    assert c2.affective_count == 2
    assert c2.polar_ratio == 1.0

    assert result.audience.num_comments == 2
    assert result.audience.audience_polar_mean == 1.0
    assert result.audience.audience_issue_mean == 0.5
    assert result.audience.audience_affective_mean == 0.5


def test_audience_mean_ignores_empty_comments() -> None:
    comments = [
        {"comment_id": "c1", "text": "ממשלה", "like_count": 0},
        {"comment_id": "c2", "text": "", "like_count": 0},
    ]
    token_components = {"ממשלה": "issue"}

    result = compute_comments_analysis(
        ARTICLE_ID,
        comments,
        lexicon_version=LEXICON_VERSION,
        pipeline_version=PIPELINE_VERSION,
        run_id=RUN_ID,
        token_components=token_components,
    )

    assert result.comments[0].polar_ratio == 1.0
    assert result.comments[1].polar_ratio is None
    assert result.audience.audience_polar_mean == 1.0


def test_comment_id_generated_when_missing() -> None:
    from src.common.hashing import comment_id_from_text

    comments = [{"text": "ממשלה"}]
    expected_id = comment_id_from_text(ARTICLE_ID, "ממשלה", 0)

    result = compute_comments_analysis(
        ARTICLE_ID,
        comments,
        lexicon_version=LEXICON_VERSION,
        pipeline_version=PIPELINE_VERSION,
        run_id=RUN_ID,
        token_components={"ממשלה": "issue"},
    )

    assert result.comments[0].comment_id == expected_id
