"""Headless benchmark of the agent layer on the fixed demo set.

    DEMO_MODE=offline DEMO_SPEED=0.02 PYTHONPATH=. python demo/benchmark.py

Runs one full loop (no UI), collects the metric/summary events, and writes
benchmark.json + a markdown summary (to $GITHUB_STEP_SUMMARY when set, so the
GitHub Actions run page shows the table). This is the "free CI benchmark":
accuracy arc, wall time, debates, and token cost on every run.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from demo.core.events import BROKER  # noqa: E402
from demo.runner import DemoLoop  # noqa: E402


async def main() -> dict:
    demo = DemoLoop()
    queue = BROKER.subscribe()
    t0 = time.monotonic()
    task = asyncio.create_task(demo.run_once())
    metrics, summary = [], None
    while not task.done():
        try:
            ev = json.loads(await asyncio.wait_for(queue.get(), timeout=10))
        except asyncio.TimeoutError:
            continue
        if ev["type"] == "metric":
            metrics.append(ev)
        elif ev["type"] == "run_summary":
            summary = ev
    await task
    return {
        "metrics": [{k: m[k] for k in ("round", "label_he", "accuracy", "n",
                                       "learned", "duration_s")} for m in metrics],
        "summary": {k: summary[k] for k in ("total_articles", "debates",
                                            "links_recovered", "total_cost_usd",
                                            "headline_he")} if summary else None,
        "wall_time_s": round(time.monotonic() - t0, 1),
        "mode": os.environ.get("DEMO_MODE", "auto"),
    }


if __name__ == "__main__":
    result = asyncio.run(main())
    out = REPO_ROOT / "demo" / "benchmark.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))

    lines = ["# Agent-layer benchmark", "",
             "| round | mode | accuracy | n | learned |", "|--|--|--|--|--|"]
    for m in result["metrics"]:
        lines.append(f"| {m['round']} | {m['label_he']} | "
                     f"{m['accuracy']:.0%} | {m['n']} | {m['learned']} |")
    if result["summary"]:
        s = result["summary"]
        lines += ["", f"**{s['headline_he']}** — {s['debates']} debates, "
                      f"{s['links_recovered']} links recovered, "
                      f"cost ${s['total_cost_usd']}"]
    md = "\n".join(lines)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        Path(step_summary).write_text(md, encoding="utf-8")

    arc = [m["accuracy"] for m in result["metrics"]]
    if not (len(arc) == 3 and arc[0] < arc[1] < arc[2]):
        print(f"WARNING: improvement arc not monotone: {arc}", file=sys.stderr)
        sys.exit(1)
