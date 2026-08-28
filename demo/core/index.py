"""Local vector index for RAG retrieval.

Simplification, on purpose (kiosk reliability): a normalized numpy matrix with
cosine similarity instead of a vector-DB server. At ~1.2k passages a full dot
product is <1ms, fully deterministic, and has zero moving parts. The embedding
model is real (multilingual-e5-small, run offline at prep time).

Supports appending vectors at runtime — this is the "cumulative RAG": confirmed
classifications from earlier rounds become retrieval context for later rounds.
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
        self.base_size = len(meta)

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

    def add(self, vec: np.ndarray, meta: dict[str, Any]) -> None:
        self.vectors = np.vstack([self.vectors, vec[None, :]])
        self.meta.append(meta)

    def reset_to_base(self) -> None:
        """Drop runtime-added vectors so every 5-minute loop replays the same arc."""
        self.vectors = self.vectors[: self.base_size]
        self.meta = self.meta[: self.base_size]
