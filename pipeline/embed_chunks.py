#!/usr/bin/env python3
"""Chunk new articles and embed the chunks, for the assistant's retrieval.

Two passes, and unlike pipeline/embed_articles.py they are genuinely
independent: chunking is pure text work that needs no API key, and embedding is
a paid call that can fail on its own. Splitting them means a run with no
embedding key still leaves the corpus chunked and lexically searchable — which
is exactly the degraded mode src/rag/retrieval.py falls back to.

Runs at the end of ingestion. It costs a few cents for the whole corpus once,
then a fraction of that per run as new articles arrive, because both passes are
gated on what is missing rather than redoing the corpus.

Nothing here loads a model: the vectors come over HTTP, which is what lets the
same code embed a chunk here and a question on Render. See
src/rag/embedding.py for why that is not src/analysis/embeddings.py.
"""

from __future__ import annotations

import argparse
import sys
import time

from src.common.hashing import chunk_id_from_position
from src.db.chunks import (
    iter_articles_needing_chunks,
    iter_chunks_needing_embedding,
    save_chunk_embeddings,
    save_chunks,
)
from src.db.config import require_database_url
from src.rag.chunking import chunk_article, embedded_text
from src.rag.embedding import DEFAULT_BATCH_SIZE, EMBED_MODEL, embed_passages, to_literal


def chunk_pending(limit: int | None) -> int:
    articles = iter_articles_needing_chunks(limit=limit)
    print(f"Articles needing chunks: {len(articles)}")
    if not articles:
        return 0

    written = 0
    for article in articles:
        chunks = chunk_article(article["text"])
        if not chunks:
            continue
        written += save_chunks(
            article["article_id"],
            [
                (chunk_id_from_position(article["article_id"], c.ordinal), c.ordinal, c.text)
                for c in chunks
            ],
        )
    print(f"Wrote {written} chunks across {len(articles)} articles")
    return written


def embed_pending(limit: int | None, batch_size: int) -> int:
    pending = iter_chunks_needing_embedding(EMBED_MODEL, limit=limit)
    print(f"Chunks needing an embedding: {len(pending)}")
    if not pending:
        return 0

    written = 0
    started = time.monotonic()
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        vectors = embed_passages(
            [embedded_text(row["title"], row["text"]) for row in batch],
            batch_size=batch_size,
        )
        written += save_chunk_embeddings(
            [(row["chunk_id"], to_literal(vector)) for row, vector in zip(batch, vectors)],
            model=EMBED_MODEL,
        )
        print(f"  embedded {written}/{len(pending)}")
    print(f"Embedded {written} chunks in {time.monotonic() - started:.1f}s")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Chunk articles and embed the chunks")
    parser.add_argument("--limit", type=int, default=0, help="Cap articles chunked this run")
    parser.add_argument(
        "--embed-limit", type=int, default=0, help="Cap chunks embedded this run"
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--chunk-only", action="store_true", help="Skip the paid pass")
    parser.add_argument("--embed-only", action="store_true", help="Embed existing chunks")
    args = parser.parse_args()

    try:
        require_database_url()
    except Exception as exc:  # noqa: BLE001 - the message is the whole point
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not args.embed_only:
        chunk_pending(args.limit or None)
    if not args.chunk_only:
        try:
            embed_pending(args.embed_limit or None, args.batch_size)
        except Exception as exc:  # noqa: BLE001 - provider errors are not ours to type
            # Non-fatal by design, and this is the same call ingestion makes for
            # the event embeddings: chunks are written and searchable
            # lexically, so a missing key or a provider outage costs recall,
            # not the assistant.
            print(f"WARNING: embedding pass failed: {exc}", file=sys.stderr)
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
