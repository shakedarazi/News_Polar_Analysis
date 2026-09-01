#!/usr/bin/env python3
"""Embed new articles, then recluster the corpus into events.

Runs during ingestion (GitHub Actions), never on the API host - see
src/analysis/embeddings.py for why. Two passes in one script because they are
not independent: reclustering reads every vector, so it must happen after the
new ones are written or the newest articles silently miss their own event.

The clustering pass is whole-corpus rather than incremental, and cheaply so: a
1.4k x 1.4k similarity matrix is 8MB and under a second. An incremental pass
would have to decide what happens when a new article should have merged two
existing events, which is exactly the kind of accumulated-state bug this
codebase avoids by recomputing from scratch.
"""

from __future__ import annotations

import argparse
import sys
import time

from src.analysis.embeddings import EMBED_MODEL, embed_passages, passage_text
from src.analysis.semantic_events import (
    CLUSTER_SIMILARITY_THRESHOLD,
    EmbeddedArticle,
    cluster_by_similarity,
)
from src.db.config import require_database_url
from src.db.embeddings import (
    iter_articles_needing_embedding,
    load_embedded_articles,
    save_embeddings,
    save_event_assignments,
)


def embed_pending(limit: int | None, batch_size: int) -> int:
    pending = iter_articles_needing_embedding(EMBED_MODEL, limit=limit)
    print(f"Articles needing an embedding: {len(pending)}")
    if not pending:
        return 0

    written = 0
    started = time.monotonic()
    for start in range(0, len(pending), batch_size):
        chunk = pending[start : start + batch_size]
        vectors = embed_passages([passage_text(r["title"], r["lead"]) for r in chunk])
        written += save_embeddings(
            [(row["article_id"], vectors[i]) for i, row in enumerate(chunk)],
            model=EMBED_MODEL,
        )
        print(f"  embedded {written}/{len(pending)}")
    print(f"Embedded {written} articles in {time.monotonic() - started:.1f}s")
    return written


def recluster() -> int:
    rows = load_embedded_articles(EMBED_MODEL)
    print(f"\nClustering {len(rows)} embedded articles at cosine >= {CLUSTER_SIMILARITY_THRESHOLD}")
    if not rows:
        print("No embeddings stored; nothing to cluster.")
        return 0

    groups = cluster_by_similarity(
        [
            EmbeddedArticle(
                article_id=r["article_id"],
                primary_category=r["primary_category"],
                first_seen_at=r["first_seen_at"],
                vector=r["vector"],
            )
            for r in rows
        ]
    )

    assignments = {
        article_id: event_id
        for event_id, members in groups.items()
        for article_id in members
    }
    # Everything embedded but not in an event this time round. Written as an
    # explicit clear rather than left alone: an article that dropped out of a
    # cluster would otherwise keep pointing at an event it is no longer in.
    cleared = [r["article_id"] for r in rows if r["article_id"] not in assignments]

    save_event_assignments(assignments, cleared_ids=cleared)
    print(f"Events: {len(groups)}   articles in an event: {len(assignments)}   cleared: {len(cleared)}")
    return len(groups)


def main() -> int:
    parser = argparse.ArgumentParser(description="Embed articles and recluster events")
    parser.add_argument("--limit", type=int, default=0, help="Cap articles embedded this run")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument(
        "--skip-cluster",
        action="store_true",
        help="Embed only. Leaves stored events on the previous corpus.",
    )
    parser.add_argument(
        "--cluster-only",
        action="store_true",
        help="Recluster from stored vectors without loading the model.",
    )
    args = parser.parse_args()

    try:
        require_database_url()
    except Exception as exc:  # noqa: BLE001 - message is the whole point
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not args.cluster_only:
        embed_pending(args.limit or None, args.batch_size)
    if not args.skip_cluster:
        recluster()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
