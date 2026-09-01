"""Local vector index for RAG retrieval.

Simplification, on purpose (kiosk reliability): a normalized numpy matrix with
cosine similarity instead of a vector-DB server. At ~1.2k passages a full dot
product is <1ms, fully deterministic, and has zero moving parts. The embedding
model is real (multilingual-e5-small, run offline at prep time).

The index is built once by prepare_demo and never changes at runtime. It used
to carry `add()` and `reset_to_base()` for a "cumulative RAG" — earlier rounds'
confirmed classifications becoming later rounds' retrieval context — which no
caller ever used and no screen ever claimed (demo/README.md item 47). Two
methods and a docstring promising a capability are indistinguishable from the
capability when someone reads the file, so both are gone.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from demo import config


class Embedder:
    """Lazy singleton around sentence-transformers (heavy import)."""

    _model = None

    @classmethod
    def model(cls):
        if cls._model is None:
            from sentence_transformers import SentenceTransformer
            cls._model = SentenceTransformer(config.EMBED_MODEL)
        return cls._model

    @classmethod
    def embed_passages(cls, texts: list[str]) -> np.ndarray:
        vecs = cls.model().encode(
            [f"passage: {t}" for t in texts],
            normalize_embeddings=True, show_progress_bar=False,
        )
        return np.asarray(vecs, dtype=np.float32)

    @classmethod
    def embed_query(cls, text: str) -> np.ndarray:
        vec = cls.model().encode([f"query: {text}"], normalize_embeddings=True)
        return np.asarray(vec, dtype=np.float32)[0]


class VectorIndex:
    def __init__(self, vectors: np.ndarray, meta: list[dict[str, Any]]) -> None:
        self.vectors = vectors  # (n, d) float32, L2-normalized
        self.meta = meta        # aligned: {article_id, title, category, source}

    @classmethod
    def load(cls) -> "VectorIndex":
        data = np.load(config.INDEX_PATH)
        meta = json.loads(config.INDEX_META_PATH.read_text(encoding="utf-8"))
        return cls(data["vectors"], meta)

    def query(self, vec: np.ndarray, k: int = 6) -> list[dict[str, Any]]:
        if len(self.meta) == 0:
            return []
        scores = self.vectors @ vec
        top = np.argsort(-scores)[:k]
        return [{**self.meta[i], "score": float(scores[i])} for i in top]
