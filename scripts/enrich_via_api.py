#!/usr/bin/env python3
"""Backfill AI summaries and bias estimates by driving the deployed API.

Summary and bias are on-demand enrichment (see CLAUDE.md step 6): there is no
pipeline script for them, so in practice almost no article has them. That is
fine for normal browsing — the page generates one when you open it — and bad
when you need a corpus that already looks complete.

Why this calls the deployed API instead of importing src.nlp.summarize
directly: the real OpenAI key lives only in Render's environment. The local
.env holds an OpenRouter key (sk-or-...) pointed at openrouter.ai, which is the
same credit pool the scheduled ingestion classification spends. Going through
Render uses the key that is already provisioned for exactly this purpose, and
means this script needs no credentials at all — it never sees a key.

Both endpoints cache into articles.summary_* / articles.bias_*, so this is
idempotent: an article that already has the field is skipped, and re-running
after an interrupt resumes where it stopped.

Usage:
  scripts/enrich_via_api.py --what summary --limit 200
  scripts/enrich_via_api.py --what both --limit 0        # 0 = everything
  scripts/enrich_via_api.py --what bias --workers 6
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_env() -> None:
    """Minimal .env loader — python-dotenv is not in requirements."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Z_]+)\s*=\s*(.*?)\s*$", line)
        if match:
            os.environ.setdefault(match.group(1), match.group(2).strip("\"'"))


# Newest first: if this is interrupted or runs out of time, the articles a demo
# is most likely to open are the ones already done.
PENDING_SQL = {
    "summary": """
        SELECT article_id FROM articles
        WHERE summary_text IS NULL AND text IS NOT NULL AND length(text) > 400
        ORDER BY first_seen_at DESC
    """,
    "bias": """
        SELECT article_id FROM articles
        WHERE bias_label IS NULL AND text IS NOT NULL AND length(text) > 400
        ORDER BY first_seen_at DESC
    """,
}


def pending_ids(kind: str, limit: int) -> list[str]:
    from src.db.connection import get_connection

    sql = PENDING_SQL[kind]
    if limit:
        sql += f" LIMIT {int(limit)}"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return [row[0] for row in cur.fetchall()]


class Progress:
    def __init__(self, total: int, label: str) -> None:
        self.total = total
        self.label = label
        self.done = 0
        self.failed = 0
        self.started = time.monotonic()
        self._lock = threading.Lock()

    def tick(self, ok: bool) -> None:
        with self._lock:
            self.done += 1
            if not ok:
                self.failed += 1
            elapsed = time.monotonic() - self.started
            rate = self.done / elapsed if elapsed else 0
            eta = (self.total - self.done) / rate if rate else 0
            print(
                f"  [{self.label}] {self.done}/{self.total} "
                f"failed={self.failed} "
                f"{rate * 60:.1f}/min ETA {eta / 60:.0f}m",
                flush=True,
            )


def enrich_one(session, base_url: str, article_id: str, kind: str, timeout: float) -> bool:
    url = f"{base_url}/api/articles/{article_id}/{kind}/generate"
    try:
        response = session.post(url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - network errors are expected in bulk
        print(f"    {article_id[:12]} {kind}: {type(exc).__name__}", flush=True)
        return False
    if response.status_code != 200:
        print(f"    {article_id[:12]} {kind}: HTTP {response.status_code}", flush=True)
        return False
    return True


def run_kind(kind: str, limit: int, workers: int, base_url: str, timeout: float) -> int:
    import requests

    ids = pending_ids(kind, limit)
    if not ids:
        print(f"== {kind}: nothing pending ==")
        return 0
    print(f"== {kind}: {len(ids)} articles, {workers} workers ==")
    progress = Progress(len(ids), kind)

    # One Session per worker: requests.Session is not documented as thread-safe,
    # and per-thread sessions still get connection reuse against Render.
    local = threading.local()

    def worker(article_id: str) -> bool:
        if not hasattr(local, "session"):
            local.session = requests.Session()
        ok = enrich_one(local.session, base_url, article_id, kind, timeout)
        progress.tick(ok)
        return ok

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(worker, article_id) for article_id in ids]
        for future in as_completed(futures):
            future.result()

    print(f"== {kind}: done={progress.done - progress.failed} failed={progress.failed} ==")
    return progress.failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--what", choices=["summary", "bias", "both"], default="both")
    parser.add_argument("--limit", type=int, default=0, help="Max articles per kind (0 = all)")
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent requests. Render's free tier is single-instance; "
        "raising this too far just queues on their side.",
    )
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument(
        "--base-url",
        default=None,
        help="Defaults to RENDER_URL from .env.",
    )
    args = parser.parse_args()

    load_env()
    base_url = (args.base_url or os.environ.get("RENDER_URL") or "").rstrip("/")
    if not base_url:
        print("ERROR: no --base-url and RENDER_URL is not set in .env", file=sys.stderr)
        return 2

    print(f"Target: {base_url}")
    kinds = ["summary", "bias"] if args.what == "both" else [args.what]
    failed = 0
    for kind in kinds:
        failed += run_kind(kind, args.limit, args.workers, base_url, args.timeout)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
