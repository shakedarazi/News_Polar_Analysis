"""Tests for split OpenAI (user-facing) vs OpenRouter (ingestion) clients."""

from pathlib import Path

import openai
import pytest

from src.nlp.openai_config import (
    get_ingestion_model,
    get_ingestion_openai_api_key,
    get_ingestion_openai_client,
    get_openai_api_key,
    get_openai_client,
    get_user_model,
    require_ingestion_openai_api_key,
    require_openai_api_key,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "ingestion.yml").read_text(encoding="utf-8")


def test_user_key_does_not_see_ingestion_key(monkeypatch):
    monkeypatch.setenv("OPENAI_INGESTION_API_KEY", "sk-or-ing")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_openai_api_key() is None
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        require_openai_api_key()


def test_ingestion_key_does_not_fall_back_to_user_key(monkeypatch):
    monkeypatch.delenv("OPENAI_INGESTION_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-user")
    assert get_ingestion_openai_api_key() is None
    with pytest.raises(RuntimeError, match="OPENAI_INGESTION_API_KEY is not set"):
        require_ingestion_openai_api_key()


def test_keys_are_independent(monkeypatch):
    monkeypatch.setenv("OPENAI_INGESTION_API_KEY", "sk-or-ing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-user")
    assert get_ingestion_openai_api_key() == "sk-or-ing"
    assert get_openai_api_key() == "sk-user"


def test_clients_use_matching_key_and_gateway(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-user")
    monkeypatch.setenv("OPENAI_INGESTION_API_KEY", "sk-or-ing")
    monkeypatch.setenv("OPENAI_INGESTION_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    seen: list[dict] = []

    def fake_openai(**kwargs):
        seen.append(kwargs)
        return object()

    monkeypatch.setattr(openai, "OpenAI", fake_openai)

    get_openai_client()
    get_ingestion_openai_client()

    assert seen[0]["api_key"] == "sk-user"
    assert "base_url" not in seen[0]
    assert seen[1]["api_key"] == "sk-or-ing"
    assert seen[1]["base_url"] == "https://openrouter.ai/api/v1"


def test_model_ids_differ_by_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_INGESTION_MODEL", raising=False)
    assert get_user_model() == "gpt-4o-mini"
    assert get_ingestion_model() == "openai/gpt-4o-mini"


def test_ingestion_workflow_uses_openrouter_only():
    assert "OPENAI_INGESTION_API_KEY:" in WORKFLOW
    assert "OPENAI_INGESTION_BASE_URL:" in WORKFLOW
    assert "secrets.OPENAI_API_KEY" in WORKFLOW
    for line in WORKFLOW.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert not stripped.startswith("OPENAI_API_KEY:"), (
            "ingestion.yml must not inject OPENAI_API_KEY into the runner"
        )
        assert not stripped.startswith("OPENAI_BASE_URL:"), (
            "ingestion.yml must not inject the user-facing OPENAI_BASE_URL"
        )
