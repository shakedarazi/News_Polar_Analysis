"""How an article is split into retrievable passages (src/rag/chunking.py).

Pure text work — no database, no model — so what the splitter does can be
tested by reading it. What is pinned here is the shape a chunk has to have for
retrieval to work at all: bounded size, no lost text at the seams, and a
passage that still says what story it belongs to once it is on its own.
"""

from __future__ import annotations

from src.rag.chunking import (
    MIN_CHUNK_CHARS,
    OVERLAP_SENTENCES,
    TARGET_CHUNK_CHARS,
    chunk_article,
    embedded_text,
)


def sentences(count: int, word: str = "מילה") -> str:
    """`count` sentences of roughly 100 characters each."""
    body = " ".join([word] * 18)
    return " ".join(f"{body} {i}." for i in range(count))


class TestTheSplit:
    def test_an_empty_article_produces_nothing(self):
        assert chunk_article("") == []
        assert chunk_article(None) == []

    def test_a_short_article_is_one_chunk(self):
        chunks = chunk_article("משפט ראשון. משפט שני.")
        assert len(chunks) == 1
        assert chunks[0].ordinal == 0
        assert "משפט ראשון" in chunks[0].text

    def test_a_long_article_is_split(self):
        chunks = chunk_article(sentences(40))
        assert len(chunks) > 1

    def test_ordinals_are_dense_and_start_at_zero(self):
        chunks = chunk_article(sentences(40))
        assert [c.ordinal for c in chunks] == list(range(len(chunks)))

    def test_no_chunk_runs_far_past_the_target(self):
        """The budget is what makes the cost of a question predictable. A
        sentence can push one chunk over, but not by a multiple."""
        for chunk in chunk_article(sentences(60)):
            assert len(chunk.text) < TARGET_CHUNK_CHARS * 2


class TestNothingIsLostAtTheSeams:
    def test_every_sentence_survives_somewhere(self):
        text = " ".join(f"משפט מספר {i} כאן." for i in range(40))
        joined = " ".join(c.text for c in chunk_article(text))
        for i in range(40):
            assert f"משפט מספר {i} כאן" in joined

    def test_consecutive_chunks_overlap(self):
        """A claim split across a boundary is otherwise retrievable from
        neither side."""
        chunks = chunk_article(sentences(40))
        assert len(chunks) > 1
        for earlier, later in zip(chunks, chunks[1:]):
            tail = earlier.text.split(".")[-OVERLAP_SENTENCES - 1 : -1]
            assert any(part.strip() and part.strip() in later.text for part in tail)

    def test_a_stray_tail_is_merged_rather_than_stored_alone(self):
        """A trailing fragment ("צילום: רויטרס") is not worth a row or a
        vector, and retrieving it wastes context budget."""
        chunks = chunk_article(sentences(14) + " קצר.")
        assert all(
            len(c.text) >= MIN_CHUNK_CHARS for c in chunks
        ), [len(c.text) for c in chunks]


class TestExtractionThatWentWrong:
    def test_one_unpunctuated_run_is_still_split(self):
        """Extraction occasionally yields a whole article as a single sentence.
        One chunk holding all of it would blow the context budget alone."""
        chunks = chunk_article("מילה " * 900)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.text) <= TARGET_CHUNK_CHARS * 2

    def test_the_hard_split_never_cuts_a_word(self):
        chunks = chunk_article("ארוכה " * 900)
        for chunk in chunks:
            for word in chunk.text.split():
                assert word == "ארוכה"


class TestWhatGetsEmbedded:
    def test_the_title_rides_along(self):
        """"הוא הוסיף כי מדובר בצעד הכרחי" says almost nothing alone; with the
        headline in front of it the vector lands near the right story."""
        assert embedded_text("ראש הממשלה נאם", "הוא הוסיף כי מדובר בצעד הכרחי").startswith(
            "ראש הממשלה נאם"
        )

    def test_the_passage_itself_is_unchanged(self):
        assert "הוא הוסיף" in embedded_text("כותרת", "הוא הוסיף כי מדובר בצעד")

    def test_a_missing_title_leaves_no_blank_prefix(self):
        assert embedded_text(None, "טקסט") == "טקסט"
        assert embedded_text("   ", "טקסט") == "טקסט"
