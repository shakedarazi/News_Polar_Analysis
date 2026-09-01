"""Draw the candidate pairs a human labels to make the retrieval golden set.

    PYTHONPATH=. python demo/evals/sample_pairs.py

The problem this exists for is written down in demo/README.md item 16: the 77
version pairs the demo shows were *defined* by the semantic retriever, so it
finds 100% of them by construction. Precision was never checked against a human
and recall could not be defined at all — which is why the accuracy arc was cut
(demo/HANDOFF3.md line 16). A set of pairs sampled independently of the
retriever's own output is the only thing that gives either number a meaning.

Two decisions make that possible:

1. **Cross-source pairs only.** A same-outlet pair is a follow-up, not a second
   version of the story, and `_one_per_source` in demo/core/framing.py already
   collapses those. The comparison the demo makes is between outlets, so that
   is the population the retriever should be measured on.

2. **Stratified by cosine, well below the threshold.** Sampling only above
   CLUSTER_SIM would measure precision and call it accuracy. The bands below it
   are where a miss can hide, and they are the entire reason recall becomes
   sayable. The strata are deliberately uneven: 0.90+ holds 212 of 174,823
   cross-source pairs, so a uniform sample would draw ~0 of them and answer
   nothing.

What the sample can and cannot support is a property of the band sizes, and
run_evals.py states it rather than papering over it: the dense bands near the
threshold carry enough labels for a rate, and the two huge low bands carry
enough only for an upper bound on the miss rate. Extrapolating a point estimate
of recall from 20 labels standing for 35,358 pairs would be arithmetic, not
evidence.

Output is JSONL with `label: null` on every row — this script produces the
questions, never the answers. demo/evals/golden/README.md defines the labels.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np

from demo.core.framing import Snapshot, keyword_jaccard

OUT_PATH = Path(__file__).resolve().parent / "golden" / "event_pairs.jsonl"

# Seeded so the same corpus always yields the same questions: a golden set whose
# membership drifts between runs cannot be reviewed once and trusted after.
SEED = 20260901

LEAD_CHARS = 220

# (low, high, n). Bounds are [low, high). The three above 0.90 are the
# retriever's own positives and give precision; 0.86-0.90 is the near band
# where a miss is most likely and most costly; the last two are sparse on
# purpose — they buy a bound, not a rate.
BANDS: list[tuple[float, float, int]] = [
    (0.94, 1.01, 25),
    (0.92, 0.94, 25),
    (0.90, 0.92, 30),
    (0.86, 0.90, 45),
    (0.82, 0.86, 20),
    (0.00, 0.82, 15),
]


def _lead(text: str | None) -> str:
    return " ".join((text or "").split())[:LEAD_CHARS]


def build_rows() -> list[dict]:
    snap = Snapshot()
    articles = snap.articles()
    ids = [i for i in snap.vec_by_id if i in articles]
    matrix = np.stack([snap.vec_by_id[i] for i in ids])
    sim = matrix @ matrix.T

    upper = np.triu_indices(len(ids), 1)
    sources = np.array([articles[i]["source"] for i in ids])
    cross = sources[upper[0]] != sources[upper[1]]
    rows_i = upper[0][cross]
    rows_j = upper[1][cross]
    scores = sim[upper][cross]

    rng = random.Random(SEED)
    rows: list[dict] = []
    for low, high, n in BANDS:
        in_band = np.flatnonzero((scores >= low) & (scores < high))
        picked = sorted(rng.sample(list(in_band), min(n, len(in_band))))
        for idx in picked:
            a = articles[ids[rows_i[idx]]]
            b = articles[ids[rows_j[idx]]]
            # Ordered by source then id so a pair reads the same way every run.
            first, second = sorted((a, b), key=lambda r: (r["source"], r["article_id"]))
            rows.append({
                "pair_id": f"{first['article_id'][:12]}_{second['article_id'][:12]}",
                "band": f"{low:.2f}-{high:.2f}",
                "cosine": round(float(scores[idx]), 4),
                "jaccard": round(keyword_jaccard(first["title"], second["title"]), 4),
                "a": _side(first),
                "b": _side(second),
                # The three fields a reviewer fills in. `label` is the answer;
                # `note` is for the pair that needed a judgement call, so the
                # next reader can see why rather than re-litigating it.
                "label": None,
                "labelled_by": None,
                "note": "",
            })
    return rows


def _side(row: dict) -> dict:
    return {
        "article_id": row["article_id"],
        "source": row["source"],
        "title": row["title"],
        "url": row["canonical_url"],
        "first_seen_at": row["first_seen_at"],
        "lead": _lead(row["text"]),
    }


def main() -> None:
    rows = build_rows()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    by_band: dict[str, int] = {}
    for row in rows:
        by_band[row["band"]] = by_band.get(row["band"], 0) + 1
    print(f"{len(rows)} pairs -> {OUT_PATH.relative_to(Path.cwd())}")
    for band, n in by_band.items():
        print(f"  {band}: {n}")


if __name__ == "__main__":
    main()
