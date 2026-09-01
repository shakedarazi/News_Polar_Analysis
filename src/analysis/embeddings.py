"""Article embeddings for semantic event clustering.

Ingestion-only. Importing this module is cheap, but calling encode() pulls in
sentence-transformers and torch, which do not fit in Render's 512MB free web
service and have no reason to be there: vectors are computed during ingestion
on GitHub Actions (7GB) and stored in Postgres, so the API only reads a column.
The dependency lives in requirements-embed.txt, which Render does not install,
so on Render the import fails loudly rather than quietly degrading.

Nothing under src/api/ may import this module.
"""

from __future__ import annotations

import numpy as np

# Pinned, not configurable. The dimension is written into
# sql/migrations/009_embeddings.sql as vector(384), and the clustering threshold
# in src/analysis/semantic_events.py was measured on this model's output. A
# different model invalidates both.
EMBED_MODEL = "intfloat/multilingual-e5-small"
EMBED_DIMENSIONS = 384

# How much of the body rides along with the title into the embedded passage.
#
# This is not a tuning knob - it is half of what the clustering threshold means.
# Embedding titles alone puts unrelated Hebrew headlines at a median cosine of
# 0.859 and makes three separate stabbings in three towns read as one event: a
# headline says what kind of thing happened, and the lead says which one. 400
# characters is enough to carry the names, places and numbers that separate two
# incidents of the same kind.
PASSAGE_LEAD_CHARS = 400

# e5 models are trained with these prefixes and behave differently without them.
# "passage:" on BOTH sides, which is what keeps an article-to-article comparison
# symmetric - this is not the asymmetric query/passage retrieval pattern. The
# threshold was measured under this prefix; switching either side to "query:"
# shifts the whole similarity distribution and silently invalidates it.
_PREFIX = "passage: "

_model = None


def passage_text(title: str | None, lead: str | None) -> str:
    """The exact string that gets embedded. One definition, so that the
    clustering pass and any later re-measurement cannot disagree about it."""
    return f"{title or ''}. {(lead or '')[:PASSAGE_LEAD_CHARS]}"


def _get_model():
    """Load once per process. The import is deferred so that merely importing
    this module - which the test suite does - costs nothing."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def embed_passages(passages: list[str], *, batch_size: int = 64) -> np.ndarray:
    """Return an (n, 384) float32 matrix of L2-normalised row vectors.

    Normalising here rather than at comparison time is what lets the clustering
    use a plain dot product as cosine similarity, and what lets the stored
    vectors be compared by pgvector's inner product if that is ever wanted.
    """
    if not passages:
        return np.zeros((0, EMBED_DIMENSIONS), dtype=np.float32)

    vectors = _get_model().encode(
        [_PREFIX + p for p in passages],
        normalize_embeddings=True,
        batch_size=batch_size,
        show_progress_bar=False,
    )
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.shape[1] != EMBED_DIMENSIONS:
        raise ValueError(
            f"{EMBED_MODEL} returned {matrix.shape[1]} dimensions, "
            f"but the column is vector({EMBED_DIMENSIONS})"
        )
    return matrix
