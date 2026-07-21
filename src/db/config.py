"""Database configuration."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DATABASE_URL = "postgresql://news:news@localhost:5432/news_polar"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


_load_dotenv()


def get_database_url() -> str | None:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


def is_db_enabled() -> bool:
    return bool(get_database_url())


def require_database_url() -> str:
    url = get_database_url()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and start PostgreSQL."
        )
    return url

