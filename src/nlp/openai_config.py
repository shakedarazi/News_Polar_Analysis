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


def get_openai_client():
    """Build the OpenAI SDK client used by every classify/summarize/bias/qa
    call site. Honors OPENAI_BASE_URL so the same OPENAI_API_KEY + code path
    can point at an OpenAI-compatible gateway (e.g. OpenRouter) instead of
    api.openai.com — set OPENAI_MODEL too in that case, since provider ids
    differ (OpenRouter wants "openai/gpt-4o-mini", not "gpt-4o-mini")."""
    from openai import OpenAI

    base_url = os.environ.get("OPENAI_BASE_URL")
    return OpenAI(base_url=base_url) if base_url else OpenAI()
