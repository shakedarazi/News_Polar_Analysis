"""OpenAI client configuration."""

from __future__ import annotations

import os


def get_openai_api_key() -> str | None:
    return os.environ.get("OPENAI_API_KEY")


def require_openai_api_key() -> str:
    key = get_openai_api_key()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env (see .env.example)."
        )
    return key
