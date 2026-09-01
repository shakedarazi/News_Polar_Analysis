"""The vector both hosts have to agree on (src/rag/embedding.py).

A chunk is embedded on GitHub Actions through OpenRouter; the question it is
compared against is embedded on Render against api.openai.com. Everything here
protects the one property that makes that comparison mean anything — that both
paths produce the same vector for the same text.

No network: the OpenAI client is replaced with a stub.
"""

from __future__ import annotations

import math

import pytest

from src.rag import embedding
from src.rag.embedding import (
    EMBED_DIMENSIONS,
    EMBED_MODEL,
    INGESTION_REQUEST_MODEL,
    NATIVE_DIMENSIONS,
    USER_REQUEST_MODEL,
    embed_passages,
    embed_query,
    to_literal,
)


class _Stub:
    """Stands in for the OpenAI SDK client, capturing the request."""

    def __init__(self, width: int = NATIVE_DIMENSIONS):
        self.width = width
        self.calls: list[dict] = []
        self.timeout = None
        self.embeddings = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        count = 1 if isinstance(kwargs["input"], str) else len(kwargs["input"])
        data = [
            type("D", (), {"index": i, "embedding": [float(i + 1)] * self.width})
            for i in range(count)
        ]
        return type("R", (), {"data": data})


@pytest.fixture
def stubs(monkeypatch):
    user, ingestion = _Stub(), _Stub()
    monkeypatch.setattr(embedding, "get_openai_client", lambda: user)
    monkeypatch.setattr(embedding, "get_ingestion_openai_client", lambda: ingestion)
    return user, ingestion


class TestTheTwoGatewaysStayInOneSpace:
    def test_a_question_goes_to_the_user_key(self, stubs):
        user, ingestion = stubs
        embed_query("שאלה")
        assert user.calls and not ingestion.calls
        assert user.calls[0]["model"] == USER_REQUEST_MODEL

    def test_chunks_go_to_the_ingestion_key(self, stubs):
        user, ingestion = stubs
        embed_passages(["קטע"])
        assert ingestion.calls and not user.calls
        assert ingestion.calls[0]["model"] == INGESTION_REQUEST_MODEL

    def test_the_gateways_address_the_same_model_by_different_names(self):
        """OpenRouter routes provider/model; api.openai.com takes the bare
        name. Different strings, one model — which is the only reason a chunk
        vector and a query vector are comparable."""
        assert INGESTION_REQUEST_MODEL == f"openai/{USER_REQUEST_MODEL}"

    def test_the_stored_model_name_is_the_bare_one(self):
        """The provider prefix is a request detail. Storing it would make the
        version gate see two names for one model and re-embed the corpus on
        every run."""
        assert EMBED_MODEL == "text-embedding-3-small"
        assert "/" not in EMBED_MODEL

    def test_neither_side_asks_the_provider_to_truncate(self, stubs):
        """OpenRouter documents no `dimensions` parameter. Sending it would
        risk 512 floats from one host and 1536 from the other in one column."""
        user, ingestion = stubs
        embed_query("שאלה")
        embed_passages(["קטע"])
        assert "dimensions" not in user.calls[0]
        assert "dimensions" not in ingestion.calls[0]


class TestTruncation:
    def test_the_vector_is_cut_to_the_column_width(self, stubs):
        assert len(embed_query("שאלה")) == EMBED_DIMENSIONS
        assert len(embed_passages(["קטע"])[0]) == EMBED_DIMENSIONS

    def test_the_result_is_unit_length(self, stubs):
        """A truncated vector is no longer normalised, and cosine distance in
        Postgres is computed on what is stored."""
        assert math.isclose(
            math.sqrt(sum(x * x for x in embed_query("שאלה"))), 1.0, rel_tol=1e-9
        )

    def test_both_paths_truncate_identically(self, stubs):
        """The whole point: same text, two gateways, one vector."""
        assert embed_query("אותו טקסט") == embed_passages(["אותו טקסט"])[0]

    def test_a_narrower_vector_than_the_column_is_an_error(self, monkeypatch):
        """The model or the gateway changed under us. Loud beats a column of
        two incomparable halves."""
        narrow = _Stub(width=EMBED_DIMENSIONS - 1)
        monkeypatch.setattr(embedding, "get_openai_client", lambda: narrow)
        with pytest.raises(RuntimeError, match="fewer than"):
            embed_query("שאלה")

    def test_a_zero_vector_is_refused_rather_than_stored(self, monkeypatch):
        class Zeros(_Stub):
            def create(self, **kwargs):
                self.calls.append(kwargs)
                d = type("D", (), {"index": 0, "embedding": [0.0] * NATIVE_DIMENSIONS})
                return type("R", (), {"data": [d]})

        monkeypatch.setattr(embedding, "get_openai_client", lambda: Zeros())
        with pytest.raises(RuntimeError, match="zero vector"):
            embed_query("שאלה")


class TestBatching:
    def test_an_empty_list_makes_no_request(self, stubs):
        _, ingestion = stubs
        assert embed_passages([]) == []
        assert ingestion.calls == []

    def test_a_long_corpus_is_split_into_batches(self, stubs):
        _, ingestion = stubs
        vectors = embed_passages([f"קטע {i}" for i in range(300)], batch_size=128)
        assert len(vectors) == 300
        assert [len(c["input"]) for c in ingestion.calls] == [128, 128, 44]

    def test_an_empty_question_is_refused_before_it_is_billed(self, stubs):
        user, _ = stubs
        with pytest.raises(ValueError):
            embed_query("   ")
        assert user.calls == []


class TestTheLiteral:
    def test_it_is_pgvector_shaped(self):
        assert to_literal([0.5, -0.25]) == "[0.500000,-0.250000]"
