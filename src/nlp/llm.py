"""One place where a JSON completion is requested and unwrapped.

Five call sites — classify, summarize, bias, framing and the assistant — each
built the same request by hand: temperature 0, `response_format=json_object`, a
system message and a user message; then read `choices[0].message.content`,
raised on an empty body, and called `json.loads` on it. The same twelve lines,
five times, drifting apart in small ways (one passed `max_tokens`, one swallowed
a parse error and returned the raw string). This is that block, once.

What deliberately does **not** collapse into one function is the choice of
credit pool. `user_json` spends Render's real OpenAI key on things a visitor
triggered; `ingestion_json` spends the OpenRouter key on GitHub Actions. They
are different providers with different balances, and
`src/nlp/openai_config.py` has no fallback between them on purpose — a single
`json_completion(pool=...)` would put that decision behind an argument that is
easy to default and easy to get wrong. Two named doors, so a reader of any call
site can see which balance it draws down.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass

from src.nlp.openai_config import (
    get_ingestion_model,
    get_ingestion_openai_client,
    get_openai_client,
    get_user_model,
)


@dataclass(frozen=True)
class Message:
    """One prior conversational turn. `role` is "user" or "assistant"."""

    role: str
    content: str


# Hebrew acronyms carry a quote mark inside the word (צה"ל, ח"כ, ארה"ב) and a
# model that is not constrained to JSON emits it unescaped, breaking the string
# it sits in. A quote with a Hebrew letter on both sides is never a delimiter,
# so escaping it is always safe and the acronym survives verbatim. With
# response_format=json_object this never fires; it is the fallback for when the
# provider does not honour that — which OpenRouter, on the ingestion path, does
# not always do.
#
# This lived in src/nlp/framing.py and applied to one of five Hebrew-answering
# call sites. Every one of them can be handed a צה"ל; the repair belongs where
# the parsing happens.
_ACRONYM_QUOTE = re.compile(r'(?<=[֐-׿])"(?=[֐-׿])')


def loads(content: str) -> dict:
    """Parse a model's JSON object, repairing unescaped Hebrew acronym quotes."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        try:
            data = json.loads(_ACRONYM_QUOTE.sub(r'\\"', content))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OpenAI returned malformed JSON: {content[:200]}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"OpenAI returned {type(data).__name__}, expected an object")
    return data


def _messages(system: str, user: str, history: Sequence[Message]) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": system}]
    for turn in history:
        if turn.role not in ("user", "assistant"):
            raise ValueError(f"Unsupported history role: {turn.role!r}")
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": user})
    return messages


def _complete_json(
    client,
    *,
    model: str,
    system: str,
    user: str,
    history: Sequence[Message],
    max_tokens: int | None,
) -> dict:
    kwargs: dict = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": _messages(system, user, history),
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned empty response")
    return loads(content)


def user_json(
    *,
    system: str,
    user: str,
    history: Sequence[Message] = (),
    model: str | None = None,
    max_tokens: int | None = None,
) -> dict:
    """A JSON completion on the user-facing key (summary / bias / framing / chat).

    `model` resolves at call time rather than at import, which is what lets a
    test set OPENAI_MODEL and be believed.
    """
    return _complete_json(
        get_openai_client(),
        model=model or get_user_model(),
        system=system,
        user=user,
        history=history,
        max_tokens=max_tokens,
    )


def ingestion_json(
    *,
    system: str,
    user: str,
    history: Sequence[Message] = (),
    model: str | None = None,
    max_tokens: int | None = None,
) -> dict:
    """A JSON completion on the ingestion key (classify, on GitHub Actions)."""
    return _complete_json(
        get_ingestion_openai_client(),
        model=model or get_ingestion_model(),
        system=system,
        user=user,
        history=history,
        max_tokens=max_tokens,
    )
