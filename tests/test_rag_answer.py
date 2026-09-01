"""The assistant's flow: what it costs, what it cites, what it refuses.

No network and no database — retrieval, the statistics query and the model are
all replaced. What is pinned here is the part that is this codebase's decision
rather than the provider's: how many paid calls a question costs, which
evidence the model is shown, and what happens to a citation the model made up.
"""

from __future__ import annotations

import pytest

from src.nlp.llm import Message
from src.rag import answer as answer_module
from src.rag.answer import REFUSAL, answer_question, reset_cache
from src.rag.retrieval import Retrieval

STATS = {
    "total_articles": 246,
    "total_comments": 0,
    "avg_audience_mean": None,
    "by_source": [{"source": "ynet", "article_count": 60, "avg_audience_mean": 0.12}],
    "by_category": [{"category": "פוליטיקה", "article_count": 40}],
}


def chunk(article_id: str = "a1", **over) -> dict:
    base = {
        "chunk_id": f"{article_id}-0",
        "article_id": article_id,
        "ordinal": 0,
        "text": "מחירי הדיור עלו בארבעה אחוזים ברבעון האחרון.",
        "source": "ynet",
        "title": "מחירי הדיור",
        "url": "https://example.com/a",
        "primary_category": "כלכלה",
        "first_seen_at": "2026-09-01",
        "audience_mean": 0.3,
        "audience_p85": 0.5,
        "num_comments": 12,
        "score": 0.03,
    }
    base.update(over)
    return base


class Harness:
    """Records every call the assistant makes."""

    def __init__(self):
        self.embed_calls = 0
        self.model_calls: list[dict] = []
        self.stats_calls = 0
        self.reply = {"answer": "תשובה", "citations": []}
        self.chunks: list[dict] = [chunk()]
        self.degraded = False


@pytest.fixture
def harness(monkeypatch):
    h = Harness()

    def fake_retrieve(question, *, previous_question=None, **kw):
        h.embed_calls += 1
        h.last_previous = previous_question
        return Retrieval(chunks=h.chunks, terms=["דיור"], degraded=h.degraded)

    def fake_stats(*a, **kw):
        h.stats_calls += 1
        return STATS

    def fake_model(*, system, user, history=(), **kw):
        h.model_calls.append({"system": system, "user": user, "history": list(history)})
        return h.reply

    monkeypatch.setattr(answer_module, "retrieve", fake_retrieve)
    monkeypatch.setattr(answer_module, "get_dashboard_stats", fake_stats)
    monkeypatch.setattr(answer_module, "user_json", fake_model)
    reset_cache()
    return h


class TestWhatAQuestionCosts:
    def test_one_embedding_and_one_completion(self, harness):
        """The cost shape is the architecture: no planner call, no rewrite
        call, no tool loop, no self-critique pass."""
        answer_question("מה קרה למחירי הדיור?")
        assert harness.embed_calls == 1
        assert len(harness.model_calls) == 1

    def test_small_talk_costs_nothing_at_all(self, harness):
        result = answer_question("היי")
        assert harness.embed_calls == 0
        assert harness.model_calls == []
        assert harness.stats_calls == 0
        assert "NewsLens" in result.answer

    def test_a_repeated_opening_question_is_served_from_cache(self, harness):
        """The frontend offers example questions and visitors click them."""
        answer_question("כמה כתבות יש במערכת?")
        answer_question("כמה כתבות יש במערכת!")  # same after normalisation
        assert len(harness.model_calls) == 1

    def test_a_follow_up_is_not_cached(self, harness):
        """Keying a follow-up on the thread that preceded it would almost never
        hit, and would risk answering one thread from another."""
        history = [Message("user", "כמה כתבות יש ב-ynet?"), Message("assistant", "60")]
        answer_question("ומה לגבי הארץ?", history)
        answer_question("ומה לגבי הארץ?", history)
        assert len(harness.model_calls) == 2


class TestWhatTheModelIsShown:
    def test_both_evidence_blocks_are_always_present(self, harness):
        """Fetching both is what replaces a planner call — and it is the fix
        for the old assistant refusing aggregate questions because retrieval
        found nothing relevant."""
        answer_question("איזה נושא הכי מסוקר?")
        sent = harness.model_calls[0]["user"]
        assert "נתוני סיכום כלליים" in sent
        assert "246" in sent
        assert "מחירי הדיור" in sent

    def test_the_stats_block_survives_an_empty_retrieval(self, harness):
        harness.chunks = []
        answer_question("כמה כתבות יש?")
        sent = harness.model_calls[0]["user"]
        assert "246" in sent
        assert "לא נמצאו קטעים רלוונטיים" in sent

    def test_history_reaches_the_model(self, harness):
        history = [Message("user", "כמה כתבות יש ב-ynet?"), Message("assistant", "60")]
        answer_question("ומה לגבי הארץ?", history)
        assert harness.model_calls[0]["history"] == history

    def test_a_follow_up_borrows_its_subject_for_the_search(self, harness):
        """"ומה לגבי הארץ?" embeds to nothing useful on its own."""
        answer_question(
            "ומה לגבי הארץ?",
            [Message("user", "כמה כתבות יש ב-ynet?"), Message("assistant", "60")],
        )
        assert harness.last_previous == "כמה כתבות יש ב-ynet?"

    def test_history_is_bounded(self, harness):
        long_thread = [
            Message("user" if i % 2 == 0 else "assistant", f"turn {i}") for i in range(20)
        ]
        answer_question("ועכשיו?", long_thread)
        assert len(harness.model_calls[0]["history"]) <= answer_module.MAX_HISTORY_TURNS

    def test_the_transcript_the_model_reads_opens_on_a_question(self, harness):
        """Trimming mid-exchange can leave an answer with no question in front
        of it, which reads as the assistant talking to itself."""
        thread = [Message("user" if i % 2 == 0 else "assistant", str(i)) for i in range(9)]
        answer_question("ועכשיו?", thread)
        history = harness.model_calls[0]["history"]
        assert history and history[0].role == "user"


class TestCitations:
    def test_a_cited_passage_becomes_a_source(self, harness):
        harness.reply = {"answer": "עלו ב-4%", "citations": [1]}
        result = answer_question("מה קרה למחירי הדיור?")
        assert [s["article_id"] for s in result.sources] == ["a1"]
        assert result.sources[0]["title"] == "מחירי הדיור"

    def test_an_invented_citation_is_dropped_not_redirected(self, harness):
        """Pointing a fabricated number at some real article would launder it
        into a plausible-looking link."""
        harness.reply = {"answer": "משהו", "citations": [9]}
        assert answer_question("שאלה") .sources == []

    def test_nonsense_in_the_citation_list_does_not_crash_the_answer(self, harness):
        harness.reply = {"answer": "משהו", "citations": ["שתיים", None, 1]}
        assert [s["article_id"] for s in answer_question("שאלה").sources] == ["a1"]

    def test_two_chunks_of_one_article_are_one_source(self, harness):
        harness.chunks = [chunk("a1"), chunk("a1", chunk_id="a1-1", ordinal=1)]
        harness.reply = {"answer": "משהו", "citations": [1, 2]}
        assert len(answer_question("שאלה").sources) == 1

    def test_answering_from_the_stats_block_needs_no_citation(self, harness):
        harness.reply = {"answer": "246 כתבות", "citations": []}
        result = answer_question("כמה כתבות יש?")
        assert result.answer == "246 כתבות"
        assert result.sources == []


class TestDegradedAndEmpty:
    def test_a_missing_embedding_provider_is_reported_not_hidden(self, harness):
        harness.degraded = True
        assert answer_question("שאלה").degraded is True

    def test_an_empty_answer_becomes_the_refusal(self, harness):
        harness.reply = {"answer": "   ", "citations": []}
        assert answer_question("מה מזג האוויר?").answer == REFUSAL

    def test_an_empty_question_is_rejected(self, harness):
        with pytest.raises(ValueError):
            answer_question("   ")
