"""Score the retrieval threshold against the labelled golden set.

    PYTHONPATH=. python demo/evals/run_evals.py

Two numbers come out, and they are not symmetric in what the sample can
support — which is the whole reason this file is longer than the arithmetic
in it.

**Precision** is direct. Every labelled pair above a threshold is a pair the
similarity criterion would accept, so the share of them labelled `same` is that
threshold's precision, with a Wilson interval for the sample size. Nothing is
extrapolated.

**Recall** is not direct, and cannot be. The strata were sampled at wildly
different rates on purpose (25 of 39 pairs above 0.94; 15 of 137,469 below
0.82), so a positive found in a sparse stratum stands for thousands of pairs.
The estimator weights each stratum by its true size, which is the standard
correction — but weighting does not create precision, it only stops the count
from being wrong in the obvious direction. Two consequences are reported
rather than hidden:

1. Recall is reported **over the region at or above 0.86**, where every stratum
   is sampled densely enough for its rate to mean something.
2. The strata below 0.86 contained no same-event pair in 35 labels. That is a
   bound, not a zero: by the rule of three it is consistent with a positive
   rate up to ~9% in a stratum of 35,358 pairs. A point estimate of overall
   recall would be dominated by that unmeasured region, so this file refuses
   to print one and prints the bound instead.

The keyword baseline is scored on the identical labelled pairs. That is the
comparison demo/README.md item 16 says does not exist: the 77-pair figure on
the wall compares the two on a set the embedding retriever itself defined, so
it wins by construction. Here neither method chose the questions.

What this does NOT measure: `build_event_clusters` is greedy — it seeds on one
article and admits others by similarity **to that seed**, then keeps one
version per source. So these numbers describe the pairwise criterion the
clustering consumes, not the clusters. A pair the criterion accepts can still
be dropped by `_one_per_source`, and cluster-level precision is a different
experiment.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from demo import config
from demo.core.framing import CLUSTER_SIM, KEYWORD_JACCARD

GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "event_pairs.jsonl"
OUT_PATH = config.DATA_DIR / "evals.json"

# Cross-source pair counts per stratum in the snapshot the sample was drawn
# from — the weights that turn a per-stratum rate into a population estimate.
# Regenerate with demo/evals/sample_pairs.py if the snapshot changes; a stale
# weight here silently rescales recall.
BAND_POPULATION: dict[str, int] = {
    "0.94-1.01": 39,
    "0.92-0.94": 47,
    "0.90-0.92": 126,
    "0.86-0.90": 1784,
    "0.82-0.86": 35358,
    "0.00-0.82": 137469,
}

# Strata dense enough for their positive rate to be an estimate rather than a
# bound. Recall is reported over exactly this region and says so.
MEASURED_FLOOR = 0.86

THRESHOLDS = [0.94, 0.92, 0.90, 0.88, 0.86]

# Recall is only reported at stratum edges. A threshold inside a stratum (0.88)
# would count that stratum's estimated positives as entirely below the cut,
# which is not a smaller recall — it is the same recall printed as if the
# sampling had resolved something it did not.
RECALL_THRESHOLDS = [0.94, 0.92, 0.90, 0.86]


def load_golden() -> list[dict]:
    rows = [json.loads(line) for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines() if line]
    unlabelled = [r["pair_id"] for r in rows if r["label"] not in ("same", "not_same")]
    if unlabelled:
        raise SystemExit(f"{len(unlabelled)} pairs are unlabelled, first: {unlabelled[0]}")
    return rows


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval — used instead of the normal approximation because
    several cells here are near 0 or 1, where the normal interval leaves the
    unit range and reports a negative precision."""
    if total == 0:
        return (0.0, 1.0)
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def precision_at(rows: list[dict], threshold: float) -> dict:
    accepted = [r for r in rows if r["cosine"] >= threshold]
    hits = sum(1 for r in accepted if r["label"] == "same")
    low, high = wilson(hits, len(accepted))
    return {
        "threshold": threshold,
        "labelled_accepted": len(accepted),
        "true_positives": hits,
        "precision": round(hits / len(accepted), 4) if accepted else None,
        "ci_low": round(low, 4),
        "ci_high": round(high, 4),
    }


def _by_band(rows: list[dict]) -> dict[str, dict]:
    bands: dict[str, dict] = {}
    for row in rows:
        band = bands.setdefault(row["band"], {"n": 0, "same": 0})
        band["n"] += 1
        band["same"] += row["label"] == "same"
    for name, band in bands.items():
        population = BAND_POPULATION[name]
        band["population"] = population
        band["rate"] = band["same"] / band["n"]
        band["estimated_same"] = population * band["rate"]
    return bands


def recall_report(rows: list[dict]) -> dict:
    """Recall over the densely sampled region, plus the bound on the rest."""
    bands = _by_band(rows)
    measured = {n: b for n, b in bands.items() if float(n.split("-")[0]) >= MEASURED_FLOOR}
    sparse = {n: b for n, b in bands.items() if float(n.split("-")[0]) < MEASURED_FLOOR}

    total_measured = sum(b["estimated_same"] for b in measured.values())
    by_threshold = []
    for threshold in RECALL_THRESHOLDS:
        found = sum(
            b["estimated_same"] for n, b in measured.items()
            if float(n.split("-")[0]) >= threshold
        )
        by_threshold.append({
            "threshold": threshold,
            "recall": round(found / total_measured, 4) if total_measured else None,
        })

    sparse_n = sum(b["n"] for b in sparse.values())
    sparse_same = sum(b["same"] for b in sparse.values())
    sparse_population = sum(b["population"] for b in sparse.values())
    return {
        "region": f"cosine >= {MEASURED_FLOOR}",
        "estimated_same_pairs_in_region": round(total_measured, 1),
        "by_threshold": by_threshold,
        "bands": {
            name: {
                "labelled": b["n"],
                "same": b["same"],
                "population": b["population"],
                "estimated_same": round(b["estimated_same"], 1),
            }
            for name, b in sorted(bands.items(), reverse=True)
        },
        # Rule of three: with 0 positives in n labels the 95% upper bound on the
        # rate is 3/n. Stated as a bound because that is all it is.
        "below_region": {
            "labelled": sparse_n,
            "same_found": sparse_same,
            "population": sparse_population,
            "rate_upper_95": round(3 / sparse_n, 4) if sparse_n and not sparse_same else None,
        },
    }


def keyword_baseline(rows: list[dict], threshold: float = KEYWORD_JACCARD) -> dict:
    """The word-overlap baseline, scored on the same labelled pairs.

    Recall here is over the labelled sample as drawn, not weighted to the
    population: the baseline is being compared against the embedding criterion
    on identical questions, and both are read off the same denominator.
    """
    accepted = [r for r in rows if r["jaccard"] >= threshold]
    positives = [r for r in rows if r["label"] == "same"]
    hits = sum(1 for r in accepted if r["label"] == "same")
    p_low, p_high = wilson(hits, len(accepted))
    r_low, r_high = wilson(hits, len(positives))
    return {
        "threshold": threshold,
        "labelled_accepted": len(accepted),
        "true_positives": hits,
        "precision": round(hits / len(accepted), 4) if accepted else None,
        "precision_ci": [round(p_low, 4), round(p_high, 4)],
        "recall_on_sample": round(hits / len(positives), 4) if positives else None,
        "recall_ci": [round(r_low, 4), round(r_high, 4)],
        "zero_overlap_positives": sum(1 for r in positives if r["jaccard"] == 0),
    }


def embedding_on_sample(rows: list[dict], threshold: float = CLUSTER_SIM) -> dict:
    """The embedding criterion read off the same denominator as the baseline,
    so the two lines of the comparison are the same experiment."""
    accepted = [r for r in rows if r["cosine"] >= threshold]
    positives = [r for r in rows if r["label"] == "same"]
    hits = sum(1 for r in accepted if r["label"] == "same")
    r_low, r_high = wilson(hits, len(positives))
    return {
        "threshold": threshold,
        "labelled_accepted": len(accepted),
        "true_positives": hits,
        "precision": round(hits / len(accepted), 4) if accepted else None,
        "recall_on_sample": round(hits / len(positives), 4) if positives else None,
        "recall_ci": [round(r_low, 4), round(r_high, 4)],
    }


def build() -> dict:
    rows = load_golden()
    labellers = sorted({r.get("labelled_by") or "unknown" for r in rows})
    return {
        "golden_set": {
            "pairs": len(rows),
            "same": sum(1 for r in rows if r["label"] == "same"),
            # Surfaced, not buried: who produced the labels decides what the
            # numbers below are evidence of. A model-labelled set is a stated
            # baseline awaiting review, not an independent ground truth.
            "labelled_by": labellers,
            "human_reviewed": all(r.get("labelled_by") == "human" for r in rows),
        },
        "precision_sweep": [precision_at(rows, t) for t in THRESHOLDS],
        "recall": recall_report(rows),
        "head_to_head": {
            "embedding": embedding_on_sample(rows),
            "keyword": keyword_baseline(rows),
        },
        "live_threshold": CLUSTER_SIM,
    }


def main() -> None:
    result = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    g = result["golden_set"]
    print(f"golden set: {g['pairs']} pairs, {g['same']} same, labelled by {', '.join(g['labelled_by'])}")
    if not g["human_reviewed"]:
        print("  NOT human-reviewed — these are a stated baseline, not ground truth")
    print("\nprecision by threshold (labelled pairs only, nothing extrapolated)")
    for row in result["precision_sweep"]:
        mark = "  <- live" if row["threshold"] == result["live_threshold"] else ""
        print(f"  >= {row['threshold']:.2f}: {row['precision']:.0%}"
              f"  [{row['ci_low']:.0%}-{row['ci_high']:.0%}]"
              f"  ({row['true_positives']}/{row['labelled_accepted']}){mark}")
    rec = result["recall"]
    print(f"\nrecall over {rec['region']} "
          f"(~{rec['estimated_same_pairs_in_region']} same-event pairs estimated there)")
    for row in rec["by_threshold"]:
        mark = "  <- live" if row["threshold"] == result["live_threshold"] else ""
        print(f"  >= {row['threshold']:.2f}: {row['recall']:.0%}{mark}")
    below = rec["below_region"]
    print(f"  below {MEASURED_FLOOR}: {below['same_found']} same in {below['labelled']} labels"
          f" over {below['population']:,} pairs"
          f" -> rate bounded at <={below['rate_upper_95']:.0%}, not measured")
    h = result["head_to_head"]
    print("\nsame questions, two methods")
    print(f"  embedding >= {h['embedding']['threshold']}: "
          f"precision {h['embedding']['precision']:.0%}, "
          f"recall {h['embedding']['recall_on_sample']:.0%} of the sample's 45 positives")
    print(f"  keyword   >= {h['keyword']['threshold']}: "
          f"precision {h['keyword']['precision']:.0%}, "
          f"recall {h['keyword']['recall_on_sample']:.0%}"
          f"  ({h['keyword']['zero_overlap_positives']} positives share no word at all)")
    print(f"\nwrote {OUT_PATH}")


if __name__ == "__main__":
    main()
