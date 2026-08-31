"""One-shot demo preparation. Run offline, after export_snapshot.py:

    PYTHONPATH=. python demo/snapshot/prepare_demo.py [--offline] [--events 3]

Does three things:
1. Embeds every analyzable article in the snapshot into the vector index
   (real multilingual-e5-small, computed here) — the index the event
   clustering and the showtime retrieval both read.
2. Picks the showcase events: stories that more than one outlet covered, which
   also carry enough audience data for the comparison to be visible.
3. Precomputes everything the scene machine shows — verified framing per
   version, the contrastive analysis over the retrieved siblings, the outlet
   profile across ALL events, the per-beat matrix, the sampling curve and the
   change-point scan — into demo_set.json.

HONESTY NOTES (say these out loud if asked at the exhibition):
- Which events reach the screen is a CHOICE: they are ranked by how much
  audience data they carry, because an event with no comments leaves half the
  screen empty. The measurements inside a chosen event are untouched, and the
  outlet profile in section `profile` is computed over every event, not the
  chosen ones.
- The link-failure scenarios in the intake scene are scripted, replaying the
  crawler's real fallback tree against the local snapshot.
- Model output is extracted ONCE here, with network, and cached to disk;
  showtime replays it. `--offline` refuses to call the model at all.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from demo import config  # noqa: E402
from demo.core.framing import (EXTRACT_LEAD_CHARS,  # noqa: E402
                               LEX_CATEGORIES_HE, ContrastExtractor, Event,
                               FramingExtractor, Repairer, Snapshot,
                               attach_comment_profiles, bootstrap_ci,
                               build_event_clusters, category_mix_deviation,
                               change_point_power, coverage_matrix,
                               detect_change_point, keyword_recall,
                               outlet_deviation, sampling_curve,
                               topic_framing_matrix, verify_contrast,
                               verify_framing)
from demo.core.index import Embedder  # noqa: E402

# Articles below this length have no usable lead for framing extraction and a
# thin lexicon profile; including them adds noise to the clustering, not reach.
MIN_TEXT_CHARS = 400
# How much of the body rides along with the title into the embedded passage.
# Named rather than inlined so the retrieval explainer can import it instead of
# re-typing it onto the wall.
PASSAGE_LEAD_CHARS = 400
# How many versions of one event the contrastive call is given. Beyond five the
# prompt starts to dilute and the model summarises instead of contrasting.
CONTRAST_VERSIONS = 5
# How many unrelated articles ride along in the intake batch. They are what
# makes the event-map scene an actual discovery: the crawler brings back a
# mixed batch, and only the retrieval step says which of them are one story.
DISTRACTORS = 4
# Scripted intake outcomes by position in the batch. The give-up branch
# (`broken_skip`, where the article is dropped) is only ever assigned to a
# distractor — losing a version would quietly break the comparison.
SCENARIOS = {1: "broken_archive", 4: "broken_rss"}


def passage_text(row: sqlite3.Row | dict[str, Any]) -> str:
    return f"{row['title']}. {(row['text'] or '')[:PASSAGE_LEAD_CHARS]}"


def build_index(conn: sqlite3.Connection) -> int:
    """Embed the analyzable corpus and write the index the demo reads.

    Everything is indexed — there is no held-out set any more, because the demo
    no longer predicts a label it must not have seen. What the index is for now
    is finding the other outlets' versions of the same story.
    """
    rows = conn.execute(
        "select a.article_id, a.source, a.title, a.text, a.primary_category"
        " from articles a where length(coalesce(a.text,'')) > ?"
        " and exists (select 1 from windows_features w"
        "             where w.article_id = a.article_id)"
        " order by a.article_id",
        (MIN_TEXT_CHARS,),
    ).fetchall()
    print(f"embedding {len(rows)} passages (offline, one-time)...")
    vectors = Embedder.embed_passages([passage_text(r) for r in rows])
    meta = [{"article_id": r["article_id"], "title": r["title"],
             "category": r["primary_category"], "source": r["source"]}
            for r in rows]
    np.savez_compressed(config.INDEX_PATH, vectors=vectors)
    config.INDEX_META_PATH.write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"index written: {config.INDEX_PATH} ({len(meta)} vectors)")
    return len(meta)


def showcase_score(event: Event) -> tuple[int, int, int]:
    """Prefer events that are multi-source AND actually have audience data —
    without comments the whole audience half of the screen is empty."""
    with_comments = sum(1 for v in event.versions if (v.num_comments or 0) >= 15)
    return (len(event.sources), with_comments, event.total_comments)


def version_payload(snap: Snapshot, version, article: dict[str, Any],
                    framing: dict[str, Any] | None,
                    repairer: Repairer | None = None,
                    allow_network: bool = False) -> dict[str, Any]:
    text = article["text"] or ""
    payload: dict[str, Any] = {
        "article_id": version.article_id,
        "source": version.source,
        "title": version.title,
        "url": version.url,
        "first_seen_at": version.first_seen_at,
        "excerpt": text[:300],
        "windows": version.windows,
        "mean_dominance": version.mean_dominance,
        "lex_counts": version.lex_counts,
        "lex_top_he": version.lex_top_he,
        "num_comments": version.num_comments,
        "audience_mean": version.audience_mean,
        "audience_p85": version.audience_p85,
        "comment_counts": version.comment_counts,
        "comment_top_he": version.comment_top_he,
        "audience_hijacked": version.audience_hijacked,
        "top_comment": snap.top_comment(version.article_id),
        "framing": None,
        "framing_raw": framing,
        "framing_dropped": [],
        "framing_actor_grounded": None,
    }
    if framing:
        verdict = verify_framing(framing, version.title, text)
        # `framing` is the verified view and the only one anything downstream
        # should render; `framing_raw` is kept so the verifier can be re-run
        # live on stage against the same text and show what it cut.
        payload["framing"] = {**framing, "loaded_terms": verdict.kept_terms}
        payload["framing_dropped"] = verdict.dropped_terms
        payload["framing_actor_grounded"] = verdict.actor_grounded
        # The repair loop runs after the verifier, never instead of it:
        # `framing_dropped` stays the record of what the extractor got wrong,
        # and anything the loop wins back is listed separately so the screen
        # can label it as recovered rather than as originally correct.
        if repairer is not None and verdict.violations:
            fixed = repairer.repair_framing(version.article_id, framing,
                                            version.title, text,
                                            allow_network=allow_network)
            if fixed is not framing:
                after = verify_framing(fixed, version.title, text)
                recovered = [t for t in after.kept_terms
                             if t not in verdict.kept_terms]
                payload["framing"] = {**fixed, "loaded_terms": after.kept_terms}
                payload["framing_repaired"] = recovered
    return payload


def build_intake(event: Event, events: list[Event],
                 articles: dict[str, Any]) -> list[dict[str, Any]]:
    """The crawler's batch: this event's versions mixed with unrelated stories.

    The demo would be circular if intake announced "here are the three
    versions" — finding them is the retrieval step's job one scene later. So
    intake carries a realistic mixed batch and says nothing about which is
    which.
    """
    own = {v.article_id for v in event.versions}
    pool = [e.versions[0] for e in events
            if e.event_id != event.event_id and e.topic_he != event.topic_he
            and e.versions[0].article_id not in own]
    pool.sort(key=lambda v: -(v.num_comments or 0))
    distractors = pool[:DISTRACTORS]

    batch: list[tuple[Any, bool]] = []
    versions, others = list(event.versions), list(distractors)
    while versions or others:
        if others:
            batch.append((others.pop(0), False))
        if versions:
            batch.append((versions.pop(0), True))

    items = []
    for idx, (version, is_version) in enumerate(batch):
        scenario = SCENARIOS.get(idx, "ok")
        last = idx == len(batch) - 1
        items.append({
            "article_id": version.article_id, "source": version.source,
            "title": version.title, "url": version.url,
            "is_version": is_version,
            "scenario": "broken_skip" if (last and not is_version) else scenario,
        })
    return items


def build_showcase(snap: Snapshot, event: Event, events: list[Event],
                   articles: dict[str, Any], framer: FramingExtractor,
                   contraster: ContrastExtractor,
                   allow_network: bool,
                   repairer: Repairer | None = None) -> dict[str, Any]:
    attach_comment_profiles(snap, event)
    kw_found, kw_total = keyword_recall(snap, event)

    versions = []
    for version in event.versions:
        article = articles[version.article_id]
        framing = framer.extract(version.article_id, version.title,
                                 article["text"], allow_network=allow_network)
        versions.append(version_payload(snap, version, article, framing,
                                        repairer, allow_network))

    sibling_texts = [(v.source, v.title, articles[v.article_id]["text"])
                     for v in event.versions[:CONTRAST_VERSIONS]]
    contrast = contraster.extract(event.event_id, sibling_texts,
                                  allow_network=allow_network)
    contrast_raw, contrast_rejected, contrast_repaired = contrast, [], []
    if contrast:
        verified, contrast_rejected = verify_contrast(contrast, sibling_texts)
        contrast = verified
        # Same order as the framing side: verify, then try to recover. A source
        # lands in `contrast_repaired` only if the deterministic verifier
        # accepted a quote it had just thrown out.
        if repairer is not None and contrast_rejected:
            fixed = repairer.repair_contrast(event.event_id, contrast_raw,
                                             sibling_texts,
                                             allow_network=allow_network)
            if fixed is not contrast_raw:
                after, _ = verify_contrast(fixed, sibling_texts)
                had = {i.get("source") for i in verified.get("per_source") or []
                       if i.get("evidence")}
                contrast_repaired = [i.get("source")
                                     for i in after.get("per_source") or []
                                     if i.get("evidence") and i.get("source") not in had]
                contrast = after

    return {
        "event_id": event.event_id,
        "headline": event.headline,
        "topic_he": event.topic_he,
        "first_seen_at": event.first_seen_at,
        "sources": event.sources,
        "keyword_found": kw_found,
        "keyword_total": kw_total,
        "intake": build_intake(event, events, articles),
        "versions": versions,
        "contrast": contrast,
        "contrast_raw": contrast_raw,
        "contrast_rejected": contrast_rejected,
        "contrast_repaired": contrast_repaired,
    }


def build_profile(events: list[Event], articles: dict[str, Any]) -> dict[str, Any]:
    """The aggregate half of the demo: every event, not the chosen ones."""
    deviations = outlet_deviation(events, "dominance")
    mixes = category_mix_deviation(events)
    outlets = []
    for source, values in sorted(deviations.items(), key=lambda kv: -len(kv[1])):
        ci = bootstrap_ci(values)
        mix = mixes.get(source, np.zeros(7))
        order = np.argsort(-np.abs(mix))[:2]
        outlets.append({
            "source": source, "n": len(values),
            "mean": ci[0] if ci else None,
            "lo": ci[1] if ci else None, "hi": ci[2] if ci else None,
            "significant": bool(ci and (ci[1] > 0 or ci[2] < 0)),
            "mix_top": [[LEX_CATEGORIES_HE[i], float(mix[i])] for i in order],
        })

    curve_source = max(deviations, key=lambda s: len(deviations[s]))
    curve = sampling_curve(deviations[curve_source])

    cells = []
    for cell in sorted(topic_framing_matrix(events).values(),
                       key=lambda c: -c.n):
        cells.append({
            "source": cell.source, "topic_he": cell.topic_he, "n": cell.n,
            "mean": cell.ci[0] if cell.ci else None,
            "lo": cell.ci[1] if cell.ci else None,
            "hi": cell.ci[2] if cell.ci else None,
            "usable": cell.usable, "significant": cell.significant,
            "top_mix": [[name, value] for name, value in cell.top_mix(2)],
        })

    in_snapshot: dict[str, int] = {}
    for row in articles.values():
        in_snapshot[row["source"]] = in_snapshot.get(row["source"], 0) + 1
    coverage = coverage_matrix(events, in_snapshot)
    for source in coverage:
        coverage[source]["in_snapshot"] = in_snapshot.get(source, 0)

    return {
        "events_total": len(events),
        "outlets": outlets,
        "curve_source": curve_source,
        "sampling_curve": curve,
        "topic_cells": cells,
        "change_scans": build_change_scans(events),
        "power_table": [{"n": n, "power_1sd": change_point_power(n, 1.0, iterations=150),
                         "power_half_sd": change_point_power(n, 0.5, iterations=150)}
                        for n in (20, 40, 75)],
        "coverage": coverage,
    }


def build_change_scans(events: list[Event]) -> list[dict[str, Any]]:
    """Scan every (outlet, beat) series that is long enough to split.

    The detector's power is reported next to each result so a null reads as
    "no shift of a size we could have seen", not "no shift".
    """
    series: dict[tuple[str, str], list[tuple[str, float]]] = {}
    for event in events:
        topic = event.topic_he
        if topic is None:
            continue
        observed = [(v.source, v.mean_dominance) for v in event.versions
                    if v.mean_dominance is not None]
        if len(observed) < 2:
            continue
        median = float(np.median([v for _, v in observed]))
        for source, value in observed:
            series.setdefault((source, topic), []).append(
                (event.first_seen_at, value - median))

    scans = []
    for (source, topic), points in sorted(series.items(), key=lambda kv: -len(kv[1])):
        cp = detect_change_point(points)
        if cp is None:
            continue
        scans.append({
            "source": source, "topic_he": topic, "n": cp.n, "at": cp.at,
            "shift": cp.shift, "p_value": cp.p_value, "detected": cp.detected,
            "before_mean": cp.before_mean, "after_mean": cp.after_mean,
            "power_1sd": change_point_power(cp.n, 1.0, iterations=120),
        })
    return scans


def run_verifier(events: list[Event], articles: dict[str, Any],
                 framer: FramingExtractor,
                 contraster: ContrastExtractor) -> dict[str, Any]:
    """Grounding pass over everything the model produced, cached or fresh.

    Counted across the whole cache rather than the showcase events alone, so
    the rejection rate on screen describes the extractor's real behaviour and
    not one lucky story.
    """
    terms_total = terms_rejected = actors_total = actors_rejected = 0
    for event in events:
        for version in event.versions:
            framing = framer.cached(version.article_id)
            if not framing:
                continue
            verdict = verify_framing(framing, version.title,
                                     articles[version.article_id]["text"])
            terms_total += len(verdict.kept_terms) + len(verdict.dropped_terms)
            terms_rejected += len(verdict.dropped_terms)
            if framing.get("actor"):
                actors_total += 1
                actors_rejected += int(not verdict.actor_grounded)

    quotes_total = quotes_rejected = 0
    by_id = {e.event_id: e for e in events}
    for event_id, result in contraster.cache.items():
        event = by_id.get(event_id)
        if event is None:
            continue
        versions = [(v.source, v.title, articles[v.article_id]["text"])
                    for v in event.versions[:CONTRAST_VERSIONS]]
        quotes_total += sum(1 for item in (result.get("per_source") or [])
                            if item.get("evidence"))
        _, violations = verify_contrast(result, versions)
        quotes_rejected += sum(1 for v in violations if v.startswith("ציטוט"))

    return {"terms_total": terms_total, "terms_rejected": terms_rejected,
            "actors_total": actors_total, "actors_rejected": actors_rejected,
            "quotes_total": quotes_total, "quotes_rejected": quotes_rejected,
            "lead_chars": EXTRACT_LEAD_CHARS}


def accumulate_usage(framer: FramingExtractor,
                     contraster: ContrastExtractor) -> dict[str, Any]:
    """Every token this demo's AI has ever cost, across prepare runs.

    Showtime replays the cache and therefore spends nothing, which would make
    the economy scene report $0 and mean nothing. The real number is what
    building the cache cost, so it is accumulated on disk rather than measured
    per run.
    """
    path = config.DATA_DIR / "llm_usage.json"
    total = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0}
    if path.exists():
        total.update(json.loads(path.read_text(encoding="utf-8")))
    for extractor in (framer, contraster):
        total["calls"] += extractor.calls
        total["prompt_tokens"] += extractor.prompt_tokens
        total["completion_tokens"] += extractor.completion_tokens
        total["usd"] += extractor.cost_usd()
    total["usd"] = round(total["usd"], 6)
    total["cached_outputs"] = len(framer.cache) + len(contraster.cache)
    path.write_text(json.dumps(total, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true",
                        help="never call the model; use the caches as they are")
    parser.add_argument("--events", type=int, default=3,
                        help="how many showcase events to precompute")
    parser.add_argument("--skip-index", action="store_true",
                        help="reuse the existing vector index (dev shortcut)")
    args = parser.parse_args()

    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    if not args.skip_index:
        build_index(conn)

    snap = Snapshot()
    events = build_event_clusters(snap)
    articles = snap.articles()
    print(f"cross-source events: {len(events)} "
          f"({sum(1 for e in events if len(e.sources) >= 3)} with 3+ sources)")

    framer = FramingExtractor()
    contraster = ContrastExtractor()
    # Prepare-time only. At showtime the caches are complete, so the loop
    # replays them and makes no call; if a cache entry is missing the loop
    # returns the pre-repair object and the screen degrades to a blank quote.
    repairer = Repairer()
    # Framing is extracted for EVERY version of every event, not just the ones
    # that reach the screen: the verifier's rejection rate is only meaningful
    # as a statement about the extractor, and three hand-picked stories cannot
    # carry that claim.
    pending = [v for e in events for v in e.versions
               if framer.cached(v.article_id) is None]
    if pending and not args.offline:
        print(f"extracting framing for {len(pending)} versions...")
        for i, version in enumerate(pending, start=1):
            framer.extract(version.article_id, version.title,
                           articles[version.article_id]["text"])
            if i % 25 == 0:
                framer.save()
                print(f"  {i}/{len(pending)} (${framer.cost_usd():.4f})")
        framer.save()

    # Same reasoning for the contrastive step: it runs on every event, so the
    # share of evidence quotes the verifier throws out is a real rate and not
    # an anecdote from the three stories on screen.
    todo = [e for e in events if contraster.cached(e.event_id) is None]
    if todo and not args.offline:
        print(f"contrasting {len(todo)} events...")
        for i, event in enumerate(todo, start=1):
            contraster.extract(event.event_id,
                               [(v.source, v.title, articles[v.article_id]["text"])
                                for v in event.versions[:CONTRAST_VERSIONS]])
            if i % 25 == 0:
                contraster.save()
                print(f"  {i}/{len(todo)} (${contraster.cost_usd():.4f})")
        contraster.save()
    ranked = sorted(events, key=showcase_score, reverse=True)[:args.events]
    showcases = []
    for event in ranked:
        showcases.append(build_showcase(snap, event, events, articles, framer,
                                        contraster, not args.offline,
                                        repairer))
        print(f"  showcase: {event.headline[:55]}… "
              f"({len(event.sources)} sources, {event.total_comments} comments, "
              f"keyword {showcases[-1]['keyword_found']}/{showcases[-1]['keyword_total']})")
    if framer.calls or contraster.calls or repairer.calls:
        framer.save()
        contraster.save()
        repairer.save()
        print(f"model calls: {framer.calls + contraster.calls + repairer.calls}, "
              f"{framer.failures + contraster.failures} failures, "
              f"${framer.cost_usd() + contraster.cost_usd() + repairer.cost_usd():.4f}")
    repaired = sum(len(s["contrast_repaired"]) for s in showcases)
    if repaired:
        print(f"repair loop: {repaired} evidence quotes recovered on stage")
    usage = accumulate_usage(framer, contraster)

    profile = build_profile(events, articles)
    verifier = run_verifier(events, articles, framer, contraster)
    print(f"profile: {len(profile['outlets'])} outlets, "
          f"{sum(1 for c in profile['topic_cells'] if c['significant'])} significant cells, "
          f"{sum(1 for s in profile['change_scans'] if s['detected'])} change points "
          f"of {len(profile['change_scans'])} series")
    print(f"verifier: {verifier['terms_rejected']}/{verifier['terms_total']} terms, "
          f"{verifier['quotes_rejected']}/{verifier['quotes_total']} evidence quotes rejected")

    config.DEMO_SET_PATH.write_text(
        json.dumps({"showcase_events": showcases, "profile": profile,
                    "verifier": verifier, "usage": usage},
                   ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"demo set written: {config.DEMO_SET_PATH}")


if __name__ == "__main__":
    main()
