#!/usr/bin/env python3
"""Create PostgreSQL schema for articles."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db.config import get_database_url, is_db_enabled
from src.db.connection import init_schema
from src.db.migrations import apply_migrations


def main() -> int:
    if not is_db_enabled():
        print("ERROR: Set DATABASE_URL (see .env.example)")
        return 1

    schema_path = ROOT / "sql" / "schema.sql"
    init_schema(schema_path)
    apply_migrations()
    print(f"Schema applied: {schema_path}")
    print(f"Database: {get_database_url()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
