"""Chunk and query vectors, from a provider the API host can actually reach.

**Why this is not src/analysis/embeddings.py.** That module runs
`intfloat/multilingual-e5-small` through sentence-transformers, and its own
docstring forbids the API from importing it: torch does not fit in Render's
512MB free tier, and CI asserts that `src.api.app` pulls in neither torch nor
numpy. That constraint is survivable for event clustering, where both sides of
every comparison are articles embedded during ingestion.

Retrieval is not like that. One side of the comparison is a question typed a
second ago, so *something on the API host* has to turn text into a vector. e5
cannot, and never will on this plan. So retrieval uses a hosted embedding
model, over HTTP, with no local weights: the API embeds the question, ingestion
embeds the chunks, and both get vectors from the same place.

The two vector spaces do not meet and must not be compared. e5 keeps
`articles.title_embedding` and the event threshold measured against it
(ADR 0005); this owns `article_chunks.embedding`. Two columns, two models, two
purposes.

**Cost.** `text-embedding-3-small` is priced per token and the corpus is small:
around 10k chunks at ~150 tokens each is roughly 1.5M tokens, a few cents to
embed the whole corpus once, and a fraction of a cent per thousand questions
after that. Chunks are embedded once and re-embedded only when the model or the
chunking changes, which the `embedding_model` column gates.

**Dimensions.** The model is Matryoshka-trained, so asking for 512 of its 1536
dimensions is a documented truncation, not a lossy hack. It is a third of the
storage and a third of the bytes moved out of Neon on every index scan — and
Neon's transfer quota is not hypothetical here, it was exhausted once already
(ADR 0005). Changing this number invalidates every stored vector.
"""

from __future__ import annotations

import os

from src.nlp.openai_config import USER_KEY_ENV

EMBEDDING_KEY_ENV = "OPENAI_EMBEDDING_API_KEY"

# Pinned, like EMBED_MODEL in src/analysis/embeddings.py. Written into
# sql/migrations/011_rag_chunks.sql as vector(512); a different model or a
# different dimension count means a different column.
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIMENSIONS = 512

# The provider's cap is 8191 tokens per input; this is a character bound well
# under it, and chunks are a tenth of this anyway. It exists so a malformed
# question cannot become an expensive request.
MAX_INPUT_CHARS = 4000

# Batches of 128 keep a single request comfortably inside the provider's payload
# limit while still amortising the round trip over the whole corpus.
DEFAULT_BATCH_SIZE = 128


def _require_key() -> str:
    """The embedding key.

    Falls back to the user-facing key, which is the one place in this codebase
    where a key fallback is correct rather than dangerous. On Render both names
    hold the same real OpenAI key. On GitHub Actions `OPENAI_API_KEY` is not set
    at all — the OpenRouter key is injected as `OPENAI_INGESTION_API_KEY`
    (see .github/workflows/ingestion.yml) — so the fallback finds nothing there
    and the error below is what a maintainer sees, rather than chunk vectors
    quietly coming from a different provider than the query vectors.
    """
    key = os.environ.get(EMBEDDING_KEY_ENV) or os.environ.get(USER_KEY_ENV)
    if not key:
        raise RuntimeError(
            f"{EMBEDDING_KEY_ENV} is not set. Retrieval needs an OpenAI key on "
            "both hosts: the API embeds the question, ingestion embeds the "
            "chunks, and the two vectors are only comparable if they come from "
            "the same provider and model."
        )
    return key


def _client():
    """An OpenAI client pinned to api.openai.com.

    Deliberately ignores OPENAI_BASE_URL. A gateway may serve a given model id
    from a different backend, and a chunk vector and a query vector that came
    from two backends are not in the same space — a failure that shows up as
    quietly bad search results, never as an error.
    """
    from openai import OpenAI

    timeout = float(os.environ.get("OPENAI_EMBEDDING_TIMEOUT_SECONDS", "20"))
    return OpenAI(api_key=_require_key(), timeout=timeout)


def _embed(inputs: list[str]) -> list[list[float]]:
    response = _client().embeddings.create(
        model=EMBED_MODEL,
        input=inputs,
        dimensions=EMBED_DIMENSIONS,
    )
    # The provider documents the response as index-ordered, but sorting costs
    # nothing and a silently shuffled batch would mislabel every vector in it.
    vectors = [item.embedding for item in sorted(response.data, key=lambda d: d.index)]
    for vector in vectors:
        if len(vector) != EMBED_DIMENSIONS:
            raise RuntimeError(
                f"{EMBED_MODEL} returned {len(vector)} dimensions, "
                f"but the column is vector({EMBED_DIMENSIONS})"
            )
    return vectors


def embed_query(text: str) -> list[float]:
    """Embed one question, on the API host. One vector, one HTTP round trip."""
    cleaned = (text or "").strip()[:MAX_INPUT_CHARS]
    if not cleaned:
        raise ValueError("Cannot embed an empty query")
    return _embed([cleaned])[0]


def embed_passages(
    texts: list[str], *, batch_size: int = DEFAULT_BATCH_SIZE
) -> list[list[float]]:
    """Embed chunk texts during ingestion, in provider-sized batches."""
    if not texts:
        return []
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = [t[:MAX_INPUT_CHARS] for t in texts[start : start + batch_size]]
        vectors.extend(_embed(batch))
    return vectors


def to_literal(vector: list[float]) -> str:
    """pgvector's text input format.

    Plain text rather than a binary adapter, matching src/db/embeddings.py: at
    512 dimensions the parsing cost is nothing against the network round trip,
    and it keeps numpy off the API's import path — which CI enforces.
    """
    return "[" + ",".join(f"{float(x):.6f}" for x in vector) + "]"
