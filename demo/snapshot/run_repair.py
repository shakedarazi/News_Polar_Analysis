"""Run the repair loop over the whole corpus and record what it did.

This is a prepare-time script, never a showtime one: it fills
`demo/data/repair_cache.json` and writes `demo/data/repair_log.json`, and the
kiosk then replays those files with no network. Re-running it is idempotent —
anything already in the cache is skipped, so a second run costs nothing.

Run:
    PYTHONPATH=. python demo/snapshot/run_repair.py            # live, cached
    PYTHONPATH=. python demo/snapshot/run_repair.py --offline  # no calls
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

from demo import config
from demo.core.framing import (EXTRACT_LEAD_CHARS, MAX_REPAIR_ATTEMPTS,
                               REPAIR_ATTEMPTS_MEASURED, Repairer, Snapshot,
                               _normalise, build_event_clusters,
                               verify_contrast, verify_framing)
from demo.snapshot.prepare_demo import CONTRAST_VERSIONS

LOG_PATH = config.DATA_DIR / "repair_log.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="replay the cache only; make no model calls")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after N repairs (for a cheap trial run)")
    args = ap.parse_args()

    from demo.core.framing import ContrastExtractor, FramingExtractor

    snap = Snapshot()
    articles = snap.articles()
    events = build_event_clusters(snap)
    framer, contraster = FramingExtractor(), ContrastExtractor()
    # The measurement runs at the higher cap so the log can answer whether
    # the extra attempt is worth keeping. Production uses MAX_REPAIR_ATTEMPTS.
    repairer = Repairer(attempts=REPAIR_ATTEMPTS_MEASURED)
    allow = not args.offline
    done = 0

    # Framing first: it is the cheaper call and the smaller population, so a
    # prompt that does not work shows up before the expensive half runs.
    framing_needed = 0
    for version in (v for e in events for v in e.versions):
        framing = framer.cached(version.article_id)
        article = articles.get(version.article_id)
        if not framing or not article:
            continue
        if verify_framing(framing, version.title, article["text"]).clean:
            continue
        framing_needed += 1
        if args.limit and done >= args.limit:
            continue
        repairer.repair_framing(version.article_id, framing, version.title,
                                article["text"], allow_network=allow)
        done += 1

    contrast_needed = 0
    for event in events:
        result = contraster.cached(event.event_id)
        if not result:
            continue
        versions = [(v.source, v.title, articles[v.article_id]["text"])
                    for v in event.versions[:CONTRAST_VERSIONS]]
        if not verify_contrast(result, versions)[1]:
            continue
        contrast_needed += 1
        if args.limit and done >= args.limit:
            continue
        repairer.repair_contrast(event.event_id, result, versions,
                                 allow_network=allow)
        done += 1
        if done % 10 == 0:
            repairer.save()
            print(f"  {done} repaired (${repairer.cost_usd():.4f})")

    repairer.save()
    write_log(repairer, framing_needed, contrast_needed,
              measure_outcomes(repairer, contraster, events, articles))


def measure_outcomes(repairer: Repairer, contraster, events,
                     articles: dict) -> dict[str, int]:
    """Split "no violations left" into the two things it can mean.

    An item reaches zero violations either because the loop found a quote that
    grounds, or because the model answered `null` and the sentence now stands
    without evidence. Both are correct outcomes and only one is a recovery, so
    reporting them as one number would overstate what the loop does.
    """
    by_event = {e.event_id: e for e in events}
    regrounded = nulled = destroyed = 0
    for key, entry in repairer.cache.items():
        if not key.startswith("contrast:"):
            continue
        event = by_event.get(key.split(":", 1)[1])
        original = contraster.cached(key.split(":", 1)[1])
        if event is None or original is None:
            continue
        versions = [(v.source, v.title, articles[v.article_id]["text"])
                    for v in event.versions[:CONTRAST_VERSIONS]]
        hay = {s: _normalise(f"{t} {(l or '')[:EXTRACT_LEAD_CHARS]}")
               for s, t, l in versions}
        before = {i.get("source"): i.get("evidence")
                  for i in original.get("per_source") or []}
        for item in entry["result"].get("per_source") or []:
            source = item.get("source")
            was, now = before.get(source), item.get("evidence")
            was_ok = bool(was) and _normalise(was) in hay.get(source, "")
            now_ok = bool(now) and _normalise(now) in hay.get(source, "")
            if now_ok and not was_ok:
                regrounded += 1
            elif was and not was_ok and not now:
                nulled += 1
            elif was_ok and not now_ok:
                destroyed += 1
    return {"quotes_regrounded": regrounded,
            "quotes_nulled_honestly": nulled,
            "valid_quotes_destroyed": destroyed}


def write_log(repairer: Repairer, framing_needed: int,
              contrast_needed: int, outcomes: dict[str, int]) -> None:
    """Aggregate the attempts into the numbers the explainer module reads."""
    attempts = [a.as_dict() for a in repairer.log]
    by_key: dict[str, list[dict]] = {}
    for a in attempts:
        by_key.setdefault(a["key"], []).append(a)

    fixed_fully = sum(1 for rows in by_key.values()
                      if rows[-1]["accepted"] and rows[-1]["violations_after"] == 0)
    improved = sum(1 for rows in by_key.values()
                   if any(r["accepted"] for r in rows)
                   and rows[-1]["violations_after"] > 0)
    unchanged = len(by_key) - fixed_fully - improved
    per_attempt = Counter()
    for rows in by_key.values():
        for r in rows:
            if r["accepted"]:
                per_attempt[r["attempt"]] += 1

    prompt_tokens = sum(a["prompt_tokens"] for a in attempts)
    completion_tokens = sum(a["completion_tokens"] for a in attempts)
    usd = (prompt_tokens * config.PRICE_PROMPT_PER_M
           + completion_tokens * config.PRICE_COMPLETION_PER_M) / 1_000_000

    payload = {
        "max_attempts_production": MAX_REPAIR_ATTEMPTS,
        "max_attempts_measured": REPAIR_ATTEMPTS_MEASURED,
        "candidates": {"framing": framing_needed, "contrast": contrast_needed},
        "items_entered": len(by_key),
        "calls": len(attempts),
        "fixed_fully": fixed_fully,
        "improved_partially": improved,
        "unchanged": unchanged,
        "accepted_by_attempt": {str(k): v for k, v in sorted(per_attempt.items())},
        "violations_before": sum(rows[0]["violations_before"]
                                 for rows in by_key.values()),
        "violations_after": sum(rows[-1]["violations_after"]
                                for rows in by_key.values()),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "usd": round(usd, 6),
        **outcomes,
        "attempts": attempts,
    }
    LOG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"wrote {LOG_PATH}")
    print(f"  candidates: {framing_needed} framing · {contrast_needed} contrast")
    print(f"  entered {len(by_key)} · {len(attempts)} calls · "
          f"fixed {fixed_fully} · partial {improved} · unchanged {unchanged}")
    print(f"  violations {payload['violations_before']} -> "
          f"{payload['violations_after']} · ${usd:.4f}")
    print(f"  quotes: {outcomes['quotes_regrounded']} re-grounded · "
          f"{outcomes['quotes_nulled_honestly']} answered null · "
          f"{outcomes['valid_quotes_destroyed']} good ones lost")


if __name__ == "__main__":
    main()
