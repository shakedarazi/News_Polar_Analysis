"""OpenAI / OpenRouter client configuration.

Two providers, two credit pools:

  User-facing (summary / bias / Q&A, Render)
    OPENAI_API_KEY     real OpenAI key
    OPENAI_BASE_URL    unset → api.openai.com
    OPENAI_MODEL       default gpt-4o-mini

  Ingestion (classify, GitHub Actions)
    OPENAI_INGESTION_API_KEY    existing OpenRouter key
    OPENAI_INGESTION_BASE_URL   https://openrouter.ai/api/v1
    OPENAI_INGESTION_MODEL      openai/gpt-4o-mini

No key fallback between the two — they are different providers, so sending
the OpenAI key to OpenRouter (or the reverse) would just fail.
"""

from __future__ import annotations

import os

USER_KEY_ENV = "OPENAI_API_KEY"
INGESTION_KEY_ENV = "OPENAI_INGESTION_API_KEY"

DEFAULT_USER_MODEL = "gpt-4o-mini"
DEFAULT_INGESTION_MODEL = "openai/gpt-4o-mini"


def get_openai_api_key() -> str | None:
    """User-facing key (summary / bias / Q&A)."""
    return os.environ.get(USER_KEY_ENV)


def get_ingestion_openai_api_key() -> str | None:
    """Classify/ingestion key (OpenRouter). No fallback to OPENAI_API_KEY."""
    return os.environ.get(INGESTION_KEY_ENV)


def require_openai_api_key() -> str:
    key = get_openai_api_key()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add a real OpenAI key to .env "
            "(see .env.example)."
        )
    return key


def require_ingestion_openai_api_key() -> str:
    key = get_ingestion_openai_api_key()
    if not key:
        raise RuntimeError(
            "OPENAI_INGESTION_API_KEY is not set. Add the OpenRouter key to "
            ".env (see .env.example)."
        )
    return key


def get_user_model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_USER_MODEL)


def get_ingestion_model() -> str:
    return os.environ.get("OPENAI_INGESTION_MODEL", DEFAULT_INGESTION_MODEL)


def _build_client(api_key: str, base_url: str | None):
    """Build the OpenAI SDK client.

    api_key is passed explicitly so the SDK does not silently pick up
    OPENAI_API_KEY from the environment when we intend the ingestion key.
    """
    from openai import OpenAI

    # Bound every chat completion so a hung provider cannot block a Render
    # worker (and the assistant spinner) for the SDK default of 10 minutes.
    timeout = float(os.environ.get("OPENAI_TIMEOUT_SECONDS", "25"))
    kwargs: dict = {"api_key": api_key, "timeout": timeout}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def get_openai_client():
    """Client for user-facing AI — official OpenAI unless OPENAI_BASE_URL is set."""
    return _build_client(require_openai_api_key(), os.environ.get("OPENAI_BASE_URL"))


def get_ingestion_openai_client():
    """Client for scheduled/CLI classification — OpenRouter."""
    return _build_client(
        require_ingestion_openai_api_key(),
        os.environ.get("OPENAI_INGESTION_BASE_URL"),
    )
