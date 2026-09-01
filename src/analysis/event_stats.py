"""Per-outlet framing profiles, measured within events rather than across them.

The problem this solves: the dashboard's source comparison averages every
article an outlet published. That number is dominated by *which stories the
outlet chooses to cover*, not by how it covers them — a channel that reports
mostly politics will look more charged than one reporting mostly traffic, and
neither fact is about framing.

The fix is to hold the news itself fixed. For every event covered by two or
more outlets, each outlet's value is compared to the MEDIAN OF THAT EVENT.
What survives the subtraction is the editorial choice.

Two constraints are baked in and both are load-bearing:

- **One version per outlet per event.** An outlet that published five
  follow-ups to the same story would otherwise supply five of nine versions,
  and the median would drift towards being that outlet.
- **Most events are pairs.** In a pair the median is the midpoint, so the two
  deviations are necessarily +d/2 and -d/2 — one comparison recorded twice,
  not two independent observations. `pair_share` is reported so a reader can
  discount accordingly; it is not a number to bury.

Pure Python on purpose: src/api/ imports this, and nothing on the API path may
pull in numpy (see .github/workflows/ci.yml).
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

# Which per-article numbers can be profiled this way. Every one of them is
# already computed by the deterministic pipeline; this module never derives a
# new measurement, only re-bases existing ones onto the event median.
METRICS = (
    "dominance",
    "audience_mean",
    "audience_p85",
    "audience_issue_mean",
    "audience_affective_mean",
)

# An outlet needs this many events before a confidence interval means anything.
# Below it the bootstrap resamples the same two or three numbers and reports a
# reassuringly narrow interval around an accident.
MIN_OBSERVATIONS = 3

BOOTSTRAP_ITERATIONS = 2000

# Fixed so the same corpus yields the same interval on every request. A CI that
# moves when you refresh the page is not a finding.
BOOTSTRAP_SEED = 20260901


@dataclass(frozen=True)
class Version:
    """One outlet's coverage of one event, reduced to a single number."""

    article_id: str
    source: str
    value: float
    # Comment volume. Used only to choose which of an outlet's several articles
    # represents it in this event — never as a weight in the statistics.
    weight: int = 0


def median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def one_per_source(versions: Iterable[Version]) -> list[Version]:
    """Keep the best-attested article per outlet: most comments, then the
    lowest article_id so the choice is stable across runs."""
    best: dict[str, Version] = {}
    for version in versions:
        current = best.get(version.source)
        if current is None or (
            version.weight > current.weight
            or (version.weight == current.weight and version.article_id < current.article_id)
        ):
            best[version.source] = version
    return [best[source] for source in sorted(best)]


def deviations_by_source(
    events: Mapping[str, Sequence[Version]], *, min_sources: int = 2
) -> tuple[dict[str, list[float]], dict[str, int]]:
    """Each outlet's per-event distance from the median of its own event.

    Returns the deviations per source, plus counts describing the events that
    contributed (`events_used`, `pair_events`).
    """
    per_source: dict[str, list[float]] = {}
    events_used = 0
    pair_events = 0

    for _, raw_versions in sorted(events.items()):
        versions = one_per_source(raw_versions)
        if len(versions) < min_sources:
            continue
        events_used += 1
        if len(versions) == 2:
            pair_events += 1
        event_median = median([v.value for v in versions])
        for version in versions:
            per_source.setdefault(version.source, []).append(version.value - event_median)

    return per_source, {"events_used": events_used, "pair_events": pair_events}


def bootstrap_ci(
    values: Sequence[float],
    *,
    confidence: float = 0.95,
    iterations: int = BOOTSTRAP_ITERATIONS,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, float] | None:
    """Percentile bootstrap interval for the mean. None below MIN_OBSERVATIONS.

    Resampling rather than a t-interval because these deviations are skewed and
    bounded below by the event median construction, so a symmetric interval
    would claim precision on the wrong side.
    """
    n = len(values)
    if n < MIN_OBSERVATIONS:
        return None
    rng = random.Random(seed)
    pool = list(values)
    means = sorted(sum(rng.choices(pool, k=n)) / n for _ in range(iterations))
    tail = (1.0 - confidence) / 2.0
    lo = means[max(0, int(round(tail * (iterations - 1))))]
    hi = means[min(iterations - 1, int(round((1.0 - tail) * (iterations - 1))))]
    return lo, hi


def source_profiles(
    events: Mapping[str, Sequence[Version]], *, min_sources: int = 2
) -> dict:
    """The full profile: mean deviation per outlet, with two intervals.

    Both intervals come from the same resampling. The second is widened by
    Bonferroni for the number of outlets tested at once, because testing five
    outlets and reporting whichever crossed zero is how noise becomes a finding
    — at five tests the chance of at least one false positive at 95% is 23%.
    `significant_adjusted` is the only column that should be read as a claim.
    """
    per_source, counts = deviations_by_source(events, min_sources=min_sources)

    testable = [s for s, values in per_source.items() if len(values) >= MIN_OBSERVATIONS]
    k = len(testable)
    adjusted_confidence = 1.0 - (0.05 / k) if k else 0.95

    sources = []
    for source in sorted(per_source):
        values = per_source[source]
        mean = sum(values) / len(values)
        plain = bootstrap_ci(values)
        adjusted = bootstrap_ci(values, confidence=adjusted_confidence) if k else None
        sources.append(
            {
                "source": source,
                "events": len(values),
                "mean_deviation": mean,
                "ci_low": plain[0] if plain else None,
                "ci_high": plain[1] if plain else None,
                "significant": bool(plain and (plain[0] > 0 or plain[1] < 0)),
                "ci_low_adjusted": adjusted[0] if adjusted else None,
                "ci_high_adjusted": adjusted[1] if adjusted else None,
                "significant_adjusted": bool(
                    adjusted and (adjusted[0] > 0 or adjusted[1] < 0)
                ),
            }
        )

    sources.sort(key=lambda s: s["mean_deviation"], reverse=True)

    events_used = counts["events_used"]
    return {
        "sources": sources,
        "events_used": events_used,
        "pair_events": counts["pair_events"],
        "pair_share": (counts["pair_events"] / events_used) if events_used else None,
        "tests_run": k,
        "min_observations": MIN_OBSERVATIONS,
    }
