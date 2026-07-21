"""Tests for lexicon-based polarity analysis."""

import math

from src.analysis.aggregation import aggregate_comments
from src.analysis.article_windows import extract_window_features
from src.analysis.comments_scoring import controversy, engagement_weight, score_comment
from src.lexicon.load_lexicon import build_article_lexicon, build_comment_lexicon, lexicon_version
from src.nlp.normalize import normalize_text
from src.nlp.sentence_splitter import split_sentences
from src.nlp.tokenize import tokenize


def test_normalize_text_strips_niqqud_and_urls():
    text = "בוקר טוב https://example.com לכולם"
    assert normalize_text(text) == "בוקר טוב לכולם"


def test_split_sentences_basic():
    assert split_sentences("משפט ראשון. משפט שני!") == ["משפט ראשון.", "משפט שני!"]


def test_comment_polar_ratio():
    lexicon = {"גרוע", "נורא", "ממשלה", "גרועה"}
    feature = score_comment(
        comment_id="a:1",
        text="ממשלה גרועה נורא",
        polar_lexicon=lexicon,
        like_count=5,
    )
    assert feature.polar_count >= 2
    assert 0 < feature.polar_ratio <= 1
    assert feature.comment_score == feature.polar_ratio
    assert feature.engagement_weight == engagement_weight(5, 0)


def test_controversy_max_at_equal_split():
    assert math.isclose(controversy(5, 5), 1.0)


def test_aggregate_comments_weighted_mean():
    lexicon = {"גרוע", "נורא"}
    low = score_comment(comment_id="a:1", text="גרוע", polar_lexicon=lexicon, like_count=0)
    high = score_comment(comment_id="a:2", text="גרוע נורא", polar_lexicon=lexicon, like_count=10)
    agg = aggregate_comments("article", [low, high])
    assert agg.num_comments == 2
    assert agg.audience_mean is not None
    assert agg.audience_p85 == 1.0
    assert agg.sum_engagement_weight > low.engagement_weight


def test_article_window_features():
    mapping = {"ממשלה": 1, "הממשלה": 1, "צהל": 2, "הצהל": 2}
    windows = extract_window_features("הממשלה דנו. הצהל פעל.", mapping)
    assert len(windows) == 2
    assert windows[0].c1 >= 1
    assert windows[1].c2 >= 1


def test_build_lexicons_non_empty():
    article = build_article_lexicon()
    comment = build_comment_lexicon()
    assert len(article) > 50
    assert len(comment) > 50
    assert lexicon_version(article) == lexicon_version(article)
