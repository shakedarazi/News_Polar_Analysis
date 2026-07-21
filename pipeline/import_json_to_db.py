#!/usr/bin/env python3
"""One-time import of legacy JSON articles into PostgreSQL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db.articles import save_article
from src.db.config import require_database_url


def iter_json_records(raw_root: Path):
    if not raw_root.exists():
        return
    for path in sorted(raw_root.glob("*/*/*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"SKIP (invalid): {path} — {exc}")
            continue
        if "article_id" not in record:
            print(f"SKIP (no article_id): {path}")
            continue
        yield path, record


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import legacy raw JSON articles to PostgreSQL (one-time migration)",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=ROOT / "data" / "raw",
        help="Legacy JSON directory (default: data/raw)",
    )
    args = parser.parse_args()

    try:
        require_database_url()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    inserted = skipped = 0
    for path, record in iter_json_records(args.raw_root):
        if save_article(record):
            inserted += 1
            print(f"INSERT: {record['article_id'][:16]}… ({record.get('source')})")
        else:
            skipped += 1

    print(f"\nDone. inserted={inserted} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
