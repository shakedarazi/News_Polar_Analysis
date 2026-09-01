"""Group articles into events by embedding similarity.

Replaces the edge test in src/analysis/event_grouping.py, not the idea. That
module clusters on title-token Jaccard, which in Hebrew misses most of what it
should catch: two outlets covering one story routinely share no content word at
all, because Hebrew morphology attaches prefixes to the words that would have
matched and each desk writes its own headline. The lexical grouping was always
labelled a baseline - its own docstring invites this replacement and names
`get_events()` as the seam.

Deliberately pure: it takes vectors and returns groups, and never loads a model
or touches the database. The model lives in src/analysis/embeddings.py (heavy,
ingestion-only) and the storage in src/db/embeddings.py, so the part with the
actual clustering decisions in it can be tested with hand-written vectors.

Greedy single-pass rather than the union-find used by the lexical grouping, and
that difference is deliberate. Union-find joins A to C whenever some B is close
to both, so at a high threshold clusters still chain together into whole
storylines. Greedy seeding gives every article one chance to join the first
cluster that claims it, which cannot chain. The threshold below was measured
under greedy assignment; it does not transfer to connected components.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

# Cosine similarity required to put two articles in one event.
#
# Measured on this corpus (1,436 categorised articles), not inherited. The
# sweep, with clusters read by hand at each step:
#
#   0.92  181 events   91 multi-source   clean on inspection
#   0.93  145 events   69 multi-source   clean on inspection
#   0.94  116 events   55 multi-source   clean, but drops real events -
#                                        Syria off the terror list, the Nepal
#                                        floods, Norway's king - which sit at
#                                        cosine 0.90-0.93
#   0.95   68 events   28 multi-source   splits one storyline into two
#
# 0.93 is the middle of the band where every cluster inspected was one story,
# and it still finds more than twice the multi-source events the lexical
# grouping does (69 vs 32).
#
# The threshold is a property of the TEXT, not just the model. Embedding titles
# alone collapses it: unrelated Hebrew headlines then sit at a median cosine of
# 0.859, 1% of all pairs clear 0.90, and clusters become topic blobs - three
# separate stabbings in three towns read as one event. The lead is what carries
# the names, places and numbers that distinguish one incident from another, so
# embed_titles() is always given "{title}. {lead}". Change what is embedded and
# this number is void.
#
# Articles with under 400 characters of extracted body text are 36% of the
# corpus and are NOT excluded: measured at this threshold they cluster at
# 22.0%, against 23.3% for articles with a full lead, so the thin ones are not
# systematically shut out.
CLUSTER_SIMILARITY_THRESHOLD = 0.93

# Kept from the lexical grouping. Embeddings have no sense of time, and Hebrew
# news repeats: "פיגוע בירושלים" from March and from September embed almost
# identically and are not one event.
EVENT_TIME_WINDOW_HOURS = 72

# A cluster of one is not an event - there is no timeline to show.
MIN_EVENT_SIZE = 2


@dataclass(frozen=True)
class EmbeddedArticle:
    article_id: str
    primary_category: str | None
    first_seen_at: datetime
    vector: np.ndarray  # (384,) float32, L2-normalised


def cluster_by_similarity(
    articles: list[EmbeddedArticle],
    *,
    threshold: float = CLUSTER_SIMILARITY_THRESHOLD,
    window_hours: int = EVENT_TIME_WINDOW_HOURS,
    min_size: int = MIN_EVENT_SIZE,
) -> dict[str, list[str]]:
    """Map event_id -> member article_ids, both in a stable order.

    The event_id is the seed article's id, which makes it reproducible from the
    data rather than allocated: the same corpus clusters to the same ids, so a
    URL to an event survives a recluster as long as the seed still leads it.
    """
    if not articles:
        return {}

    # Sorting by (time, id) is what makes the output reproducible. Greedy
    # clustering depends on visit order, so an unsorted input would return
    # different events for the same corpus on two runs.
    ordered = sorted(articles, key=lambda a: (a.first_seen_at, a.article_id))
    # Full n-by-n Gram matrix: 1.4k articles is 8MB and takes well under a
    # second. This runs in the ingestion job, not the API. It is quadratic in
    # memory, so if the corpus reaches five figures this needs blocking by time
    # window rather than a bigger machine.
    matrix = np.stack([a.vector for a in ordered]).astype(np.float32)
    # Vectors are stored L2-normalised, so the Gram matrix is cosine similarity.
    similarity = matrix @ matrix.T
    np.fill_diagonal(similarity, -1.0)

    window = timedelta(hours=window_hours)
    used: set[int] = set()
    groups: dict[str, list[str]] = {}

    for i, seed in enumerate(ordered):
        if i in used:
            continue
        members = [i]
        # Descending similarity. A stable argsort breaks ties by index, and the
        # index order is itself stable (time, id), so equal similarities cannot
        # reorder between runs.
        for j in np.argsort(-similarity[i], kind="stable"):
            j = int(j)
            if similarity[i][j] < threshold:
                break
            if j in used or j == i:
                continue
            candidate = ordered[j]
            if candidate.primary_category != seed.primary_category:
                continue
            if abs(candidate.first_seen_at - seed.first_seen_at) > window:
                continue
            members.append(j)

        used.update(members)
        if len(members) < min_size:
            continue
        members.sort()
        groups[seed.article_id] = [ordered[m].article_id for m in members]

    return groups
