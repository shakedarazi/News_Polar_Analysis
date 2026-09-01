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
model, over HTTP, with no local weights.

The two vector spaces do not meet and must not be compared. e5 keeps
`articles.title_embedding` and the event threshold measured against it
(ADR 0005); this owns `article_chunks.embedding`.

**Two gateways, one vector space.** Like src/nlp/llm.py, this has two entry
points because the two credit pools are real: questions are embedded on Render
against api.openai.com, chunks are embedded on GitHub Actions through
OpenRouter. Both resolve to OpenAI's `text-embedding-3-small` — OpenRouter
routes `openai/text-embedding-3-small` to OpenAI — which is the only reason a
chunk vector and a query vector are comparable at all. That is the invariant
this module exists to protect, and `_check` below is what makes a violation
loud instead of silent.

The provider-prefixed id is a request detail, never a stored one. The column
records the bare model name from either gateway, so the version gate does not
see two names for one model and re-embed the corpus on every run — the same
distinction the codebase already draws for `openai/gpt-4o-mini` vs
`gpt-4o-mini`.

**Why the truncation happens here and not at the provider.** OpenAI accepts a
`dimensions` argument that returns a shortened vector; OpenRouter's embeddings
endpoint documents only `model`, `input` and `encoding_format`. Sending it
anyway would mean a parameter honoured on one host and possibly dropped on the
other — 512 floats from Render, 1536 from Actions, and two incomparable halves
of one column. So neither side sends it: both ask for the full vector and cut
it the same way, in `_truncate`. The model is Matryoshka-trained, so the
leading dimensions are the informative ones and truncating then renormalising
is the documented operation, not a hack.

Storing 512 rather than 1536 is a third of the bytes an index scan moves out of
Neon, whose transfer quota this project has already exhausted once (ADR 0005).
The two thirds discarded travel from the provider to us, which costs nothing
and is not billed by the float.

**Cost.** Around 10k chunks at ~150 tokens is roughly 1.5M tokens — a few cents
to embed the corpus once at $0.02/M, and a fraction of a cent per thousand
questions after that. Chunks are re-embedded only when the model or the
chunking changes, which `embedding_model` gates.
"""

from __future__ import annotations

import math

from src.nlp.openai_config import get_ingestion_openai_client, get_openai_client

# Pinned, like EMBED_MODEL in src/analysis/embeddings.py, and stored in
# article_chunks.embedding_model as written here — bare, whichever gateway
# produced it.
EMBED_MODEL = "text-embedding-3-small"

# What each gateway is asked for. OpenRouter addresses models by
# provider/model; api.openai.com by the bare name.
USER_REQUEST_MODEL = EMBED_MODEL
INGESTION_REQUEST_MODEL = f"openai/{EMBED_MODEL}"

# The model's native width, and what we keep of it. Written into
# sql/migrations/011_rag_chunks.sql as vector(512); changing either number
# invalidates every stored vector.
NATIVE_DIMENSIONS = 1536
EMBED_DIMENSIONS = 512

# The provider's cap is 8191 tokens per input; this is a character bound well
# under it, and chunks are a tenth of this anyway. It exists so a malformed
# question cannot become an expensive request.
MAX_INPUT_CHARS = 4000

# Batches of 128 keep one request comfortably inside the payload limit while
# amortising the round trip over the corpus.
DEFAULT_BATCH_SIZE = 128


def _truncate(vector: list[float]) -> list[float]:
    """Cut a Matryoshka vector to EMBED_DIMENSIONS and renormalise it.

    Renormalising is not optional: a truncated vector is no longer unit length,
    and cosine distance in Postgres is computed on what is stored. Both hosts
    run this same function on the same model output, which is what keeps a
    chunk vector and a query vector in one space.
    """
    if len(vector) < EMBED_DIMENSIONS:
        raise RuntimeError(
            f"{EMBED_MODEL} returned {len(vector)} dimensions, fewer than the "
            f"{EMBED_DIMENSIONS} the column stores. The model or the gateway "
            "changed; re-measure before shipping."
        )
    head = vector[:EMBED_DIMENSIONS]
    norm = math.sqrt(sum(x * x for x in head))
    if norm == 0:
        raise RuntimeError("Embedding provider returned a zero vector")
    return [x / norm for x in head]


def _embed(client, model: str, inputs: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=model, input=inputs)
    # The provider documents the response as index-ordered, but sorting costs
    # nothing and a silently shuffled batch would mislabel every vector in it.
    ordered = sorted(response.data, key=lambda d: d.index)
    return [_truncate(item.embedding) for item in ordered]


def embed_query(text: str) -> list[float]:
    """Embed one question, on the API host, against the user-facing key.

    One vector, one HTTP round trip, on the same balance as the answer that
    follows it.
    """
    cleaned = (text or "").strip()[:MAX_INPUT_CHARS]
    if not cleaned:
        raise ValueError("Cannot embed an empty query")
    # The clients from openai_config already carry OPENAI_TIMEOUT_SECONDS, which
    # exists so a hung provider cannot hold a Render worker — and the assistant
    # spinner — for the SDK's ten-minute default. One bound, set in one place.
    return _embed(get_openai_client(), USER_REQUEST_MODEL, [cleaned])[0]


def embed_passages(
    texts: list[str],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    use_user_key: bool = False,
) -> list[list[float]]:
    """Embed chunk texts during ingestion, on the ingestion key.

    Same model as `embed_query`, reached through OpenRouter rather than
    directly — see the note on the two gateways above. If that ever stops being
    true, the vectors stop being comparable and search quality degrades with no
    error anywhere, which is why the model ids are constants in this file
    rather than environment variables.

    `use_user_key` sends the batch to api.openai.com instead, for a run from a
    machine that only has the OpenAI key. It is a deliberate opt-in with an
    awkward name rather than a silent fallback, because it is exactly the
    switch that would go unnoticed if it ever defaulted the wrong way in CI.
    Note what it costs as a check: a corpus embedded this way and questions
    embedded on Render are both api.openai.com, so retrieval is *more*
    consistent than production — it therefore proves the pipeline works and
    proves nothing about the cross-gateway assumption.
    """
    if not texts:
        return []
    client = get_openai_client() if use_user_key else get_ingestion_openai_client()
    request_model = USER_REQUEST_MODEL if use_user_key else INGESTION_REQUEST_MODEL
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = [t[:MAX_INPUT_CHARS] for t in texts[start : start + batch_size]]
        vectors.extend(_embed(client, request_model, batch))
    return vectors


def to_literal(vector: list[float]) -> str:
    """pgvector's text input format.

    Plain text rather than a binary adapter, matching src/db/embeddings.py: at
    512 dimensions the parsing cost is nothing against the network round trip,
    and it keeps numpy off the API's import path — which CI enforces.
    """
    return "[" + ",".join(f"{float(x):.6f}" for x in vector) + "]"
