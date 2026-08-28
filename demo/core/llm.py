"""LLM access for the demo agents — OpenRouter via the repo's existing config,
with a hard kiosk rule: one failure/timeout in "auto" mode degrades the whole
run to offline (kNN + templates) instead of ever hanging in front of a crowd.
"""

from __future__ import annotations

import asyncio
import os

from demo import config
from demo.core.events import BROKER

# Reuses the pipeline's .env loading side effect (OPENAI_* keys) — read-only.
import src.db.config  # noqa: F401
from src.nlp.openai_config import get_openai_client


class LLMGateway:
    def __init__(self) -> None:
        self.mode = config.DEMO_MODE  # live | offline | auto
        self._client = None
        self.last_finish_reason: str | None = None

    @property
    def available(self) -> bool:
        return self.mode in ("live", "auto") and bool(os.environ.get("OPENAI_API_KEY"))

    def emit_mode(self) -> None:
        """Publish the LIVE/local indicator (also mirrored in /state)."""
        live = self.available
        BROKER.emit("llm_mode", mode="live" if live else "offline",
                    label_he="מודל ענן חי" if live else "מקומי · דטרמיניסטי")

    def _get_client(self):
        if self._client is None:
            self._client = get_openai_client()
        return self._client

    async def chat(self, agent_id: str, system: str, user: str,
                   max_tokens: int = 220) -> str | None:
        """Returns the completion text, or None (caller must fall back)."""
        if not self.available:
            return None
        try:
            resp = await asyncio.wait_for(
                asyncio.to_thread(self._call, system, user, max_tokens),
                timeout=config.LLM_TIMEOUT_S,
            )
        except Exception:
            if self.mode == "auto":
                self.mode = "offline"
                BROKER.emit(
                    "reasoning", agent="amit", level="warn",
                    text_he="אין תקשורת יציבה למודל הענן — עוברים למצב מקומי (kNN דטרמיניסטי)",
                )
                self.emit_mode()
            return None
        text, prompt_toks, completion_toks, finish_reason = resp
        self.last_finish_reason = finish_reason
        cost = (prompt_toks * config.PRICE_PROMPT_PER_M
                + completion_toks * config.PRICE_COMPLETION_PER_M) / 1_000_000
        BROKER.total_tokens += prompt_toks + completion_toks
        BROKER.total_cost_usd += cost
        BROKER.llm_calls += 1
        BROKER.emit(
            "tokens", agent=agent_id, prompt=prompt_toks, completion=completion_toks,
            cost_usd=round(cost, 6),
            total_tokens=BROKER.total_tokens,
            total_cost_usd=round(BROKER.total_cost_usd, 6),
        )
        return text

    def _call(self, system: str, user: str, max_tokens: int):
        client = self._get_client()
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=0,
            timeout=config.LLM_TIMEOUT_S,
        )
        usage = resp.usage
        return (
            (resp.choices[0].message.content or "").strip(),
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
            resp.choices[0].finish_reason,
        )


GATEWAY = LLMGateway()
