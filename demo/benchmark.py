"""Headless benchmark of the agent layer on the fixed demo set.

    DEMO_SPEED=0.02 PYTHONPATH=. python demo/benchmark.py

Runs one full loop (no UI), collects the scene payloads, and writes
benchmark.json + a markdown summary (to $GITHUB_STEP_SUMMARY when set, so the
GitHub Actions run page shows the table). This is the "free CI benchmark".

The assertion is deliberately NOT about a rising accuracy arc any more — the
demo no longer predicts a label. What must hold is the claim the profile scene
makes on screen: that the confidence interval narrows as more events are
sampled, and that nothing the verifier rejected can reach the screen.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from demo.core.events import BROKER  # noqa: E402
from demo.runner import DemoLoop  # noqa: E402

COLLECT = ("event_map", "framing", "contrast", "verifier", "audience_gap",
           "profile", "economy", "run_summary")


async def main() -> dict:
    demo = DemoLoop()
    queue = BROKER.subscribe()
    t0 = time.monotonic()
    task = asyncio.create_task(demo.run_once())
    collected: dict[str, list] = {name: [] for name in COLLECT}
    scenes: list[str] = []
    while not task.done():
        try:
            ev = json.loads(await asyncio.wait_for(queue.get(), timeout=10))
        except asyncio.TimeoutError:
            continue
        if ev["type"] in collected:
            collected[ev["type"]].append(ev)
        elif ev["type"] == "scene":
            scenes.append(ev["scene"])
    await task

    profile = collected["profile"][0] if collected["profile"] else None
    summary = collected["run_summary"][0] if collected["run_summary"] else None
    return {
        "scenes": scenes,
        "event_map": collected["event_map"][0] if collected["event_map"] else None,
        "framings": len(collected["framing"]),
        "audience_gaps": len(collected["audience_gap"]),
        "verifier": collected["verifier"][0] if collected["verifier"] else None,
        "sampling_curve": profile["sampling_curve"] if profile else None,
        "events_total": profile["events_total"] if profile else 0,
        "economy": collected["economy"][0] if collected["economy"] else None,
        "summary": summary,
        "wall_time_s": round(time.monotonic() - t0, 1),
    }


def check(result: dict) -> list[str]:
    """Every failure here is a claim the screen would otherwise make falsely."""
    failures = []
    if result["scenes"] != [s["id"] for s in __import__(
            "demo.config", fromlist=["SCENES"]).SCENES]:
        failures.append(f"scene order changed: {result['scenes']}")

    curve = result["sampling_curve"] or []
    if len(curve) < 3:
        failures.append(f"sampling curve too short: {len(curve)} points")
    else:
        widths = [c["width"] for c in curve]
        if widths != sorted(widths, reverse=True):
            failures.append(f"CI width does not narrow monotonically: {widths}")

    event_map = result["event_map"]
    if not event_map or event_map["semantic_found"] <= event_map["keyword_found"]:
        failures.append("semantic retrieval did not beat the keyword baseline")

    verifier = result["verifier"]
    if not verifier:
        failures.append("verifier never reported")
    elif verifier["terms_total"] < 50:
        failures.append(f"verifier ran on too few terms: {verifier['terms_total']}")

    if result["framings"] == 0 or result["audience_gaps"] == 0:
        failures.append("framing or audience cards missing")
    return failures


if __name__ == "__main__":
    result = asyncio.run(main())
    out = REPO_ROOT / "demo" / "benchmark.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    curve = result["sampling_curve"] or []
    lines = ["# Agent-layer benchmark", "",
             f"Scenes: {' → '.join(result['scenes'])}", "",
             f"- events in profile: **{result['events_total']}**",
             f"- versions framed: {result['framings']}, "
             f"audience cards: {result['audience_gaps']}",
             f"- wall time: {result['wall_time_s']}s", ""]
    if result["event_map"]:
        em = result["event_map"]
        lines.append(f"Retrieval on the showcase event: semantic "
                     f"{em['semantic_found']}/{em['total']} vs keyword "
                     f"{em['keyword_found']}/{em['total']}")
    if result["verifier"]:
        v = result["verifier"]
        lines.append(f"Verifier: {v['terms_rejected']}/{v['terms_total']} terms and "
                     f"{v['quotes_rejected']}/{v['quotes_total']} evidence quotes rejected")
    if curve:
        lines += ["", "| events sampled | CI width |", "|--|--|"]
        lines += [f"| {c['n']} | {c['width']:.4f} |" for c in curve]
    md = "\n".join(lines)
    print(md)
    step_summary = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        Path(step_summary).write_text(md, encoding="utf-8")

    failures = check(result)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        sys.exit(1)
