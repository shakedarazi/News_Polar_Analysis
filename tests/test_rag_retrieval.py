"""Search inputs, the diversity cap, and the evidence the model is handed.

The SQL itself is exercised end to end against a real database elsewhere; what
is pinned here is everything around it that is a decision rather than a query —
which words are searched for, how a follow-up borrows its subject, which
passages survive the per-article cap, and what the context block looks like.
"""

from __future__ import annotations

from src.db.chunks import MAX_CHUNKS_PER_ARTICLE, _cap_per_article
from src.rag.context import (
    MAX_CONTEXT_CHARS,
    build_user_message,
    format_passages,
    source_display,
)
from src.rag.retrieval import MAX_TERMS, query_terms, search_text_for

STATS = {
    "total_articles": 246,
    "total_comments": 1000,
    "avg_audience_mean": 0.1234,
    "by_source": [{"source": "haaretz", "article_count": 98, "avg_audience_mean": 0.2}],
    "by_category": [{"category": "פוליטיקה", "article_count": 40}],
}


def chunk(article_id="a1", text="טקסט הקטע", **over):
    base = {
        "chunk_id": f"{article_id}-{over.get('ordinal', 0)}",
        "article_id": article_id,
        "ordinal": 0,
        "text": text,
        "source": "ynet",
        "title": "כותרת",
        "primary_category": "כלכלה",
        "first_seen_at": "2026-09-01",
        "audience_mean": 0.25,
        "num_comments": 7,
    }
    base.update(over)
    return base


class TestWhatGetsSearchedFor:
    def test_question_words_are_not_search_terms(self):
        """"מה", "כמה", "האם" match every chunk in the corpus, which narrows
        nothing once the ranks are fused."""
        terms = query_terms("מה כמה האם נכתב על נתניהו?")
        assert "נתניהו" in terms
        assert "מה" not in terms and "כמה" not in terms and "האם" not in terms

    def test_a_hebrew_acronym_stays_one_term(self):
        assert 'צה"ל' in query_terms('מה נכתב על צה"ל?')

    def test_a_repeated_name_does_not_spend_two_slots(self):
        assert query_terms("נתניהו אמר ש נתניהו").count("נתניהו") == 1

    def test_the_term_list_is_bounded(self):
        assert len(query_terms(" ".join(f"מילה{i}" for i in range(40)))) <= MAX_TERMS

    def test_terms_keep_the_order_they_were_written_in(self):
        # "בן" survives as its own term: it is a connector that trending.py
        # refuses to emit as a standalone keyword, but the lexical channel
        # matches substrings, so searching for it costs nothing and the two
        # halves of "בן גביר" both contribute a match.
        assert query_terms("נתניהו וגם בן גביר") == ["נתניהו", "וגם", "בן", "גביר"]


class TestFollowUps:
    def test_a_first_question_searches_for_itself(self):
        assert search_text_for("כמה כתבות יש?") == "כמה כתבות יש?"

    def test_a_follow_up_borrows_the_previous_subject(self):
        text = search_text_for("ומה לגבי הארץ?", "מה מדד הקיטוב של ynet?")
        assert "ynet" in text and "הארץ" in text

    def test_a_blank_previous_turn_changes_nothing(self):
        assert search_text_for("שאלה", "   ") == "שאלה"


class TestTheDiversityCap:
    def test_one_article_cannot_fill_the_answer(self):
        """A long on-topic article otherwise contributes six near-identical
        passages and crowds out the second outlet's version of the story —
        which, for a corpus about comparing outlets, is the worst failure."""
        rows = [chunk("a1", ordinal=i) for i in range(6)]
        assert len(_cap_per_article(rows, limit=8)) == MAX_CHUNKS_PER_ARTICLE

    def test_room_freed_by_the_cap_goes_to_another_article(self):
        rows = [chunk("a1", ordinal=i) for i in range(6)] + [chunk("a2")]
        kept = _cap_per_article(rows, limit=8)
        assert {r["article_id"] for r in kept} == {"a1", "a2"}

    def test_the_best_chunks_survive_in_order(self):
        rows = [chunk("a1", ordinal=i) for i in range(6)]
        assert [r["ordinal"] for r in _cap_per_article(rows, limit=8)] == [0, 1]

    def test_the_limit_still_binds(self):
        rows = [chunk(f"a{i}") for i in range(20)]
        assert len(_cap_per_article(rows, limit=8)) == 8


class TestTheEvidenceBlock:
    def test_passages_are_numbered_from_one(self):
        text, included = format_passages([chunk("a1"), chunk("a2")])
        assert "[1]" in text and "[2]" in text
        assert len(included) == 2

    def test_a_numbered_passage_always_matches_the_returned_list(self):
        """Citation [3] must resolve to the third element, or a citation points
        at the wrong article."""
        rows = [chunk(f"a{i}", text="ארוך " * 400) for i in range(20)]
        text, included = format_passages(rows)
        assert f"[{len(included)}]" in text
        assert f"[{len(included) + 1}]" not in text

    def test_the_budget_is_enforced(self):
        rows = [chunk(f"a{i}", text="ארוך " * 400) for i in range(20)]
        text, _ = format_passages(rows)
        assert len(text) < MAX_CONTEXT_CHARS * 1.5

    def test_one_huge_passage_is_still_included(self):
        """Truncated rather than dropped — dropping it would leave the model
        with no evidence at all."""
        _, included = format_passages([chunk("a1", text="ארוך " * 5000)])
        assert len(included) == 1

    def test_an_empty_result_says_so_rather_than_being_blank(self):
        text, included = format_passages([])
        assert "לא נמצאו" in text
        assert included == []

    def test_the_hebrew_outlet_name_is_supplied_not_guessed(self):
        assert source_display("haaretz") == "haaretz (הארץ)"
        assert source_display("ynet") == "ynet"

    def test_the_question_and_both_blocks_are_in_the_message(self):
        message, _ = build_user_message(
            question="מה מדד הקיטוב של הארץ?", stats=STATS, chunks=[chunk()]
        )
        assert "246" in message
        assert "haaretz (הארץ)" in message
        assert "טקסט הקטע" in message
        assert "מה מדד הקיטוב של הארץ?" in message

    def test_a_missing_polarity_reads_as_missing_not_as_zero(self):
        text, _ = format_passages([chunk(audience_mean=None)])
        assert "אין נתון" in text
        assert "0.0000" not in text
