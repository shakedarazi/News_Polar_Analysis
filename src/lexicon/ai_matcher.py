"""OpenAI-based token matching against a polarization lexicon (optional)."""

from __future__ import annotations

import json
import os
from typing import Literal, Protocol

Component = Literal["issue", "affective"]

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[misc, assignment]

SYSTEM_PROMPT = """\
You match Hebrew news article tokens to a fixed polarization lexicon.

The lexicon follows Simchon et al. (2022) with two components:
- issue: ideological / policy polarization language
- affective: negative moral-emotional polarization language

Rules:
- The lexicon contains canonical Hebrew lemma forms only.
- Match tokens that are morphological variants of a lexicon lemma, including
  Hebrew prefixes and verb/noun inflections.
- A token matches at most one lemma and therefore at most one component.
- If a token does not match any lexicon lemma, return null.
- Return only "issue", "affective", or null.
- Be conservative: match only when reasonably confident.
"""


class TokenMatcher(Protocol):
    def match_tokens(
        self,
        tokens: list[str],
        lexicon_base: dict[str, str],
    ) -> dict[str, Component | None]:
        """Map each token to issue/affective or None if unmatched."""


class OpenAITokenMatcher:
    """Classify tokens against polarization lemmas using OpenAI (no caching)."""

    def __init__(
        self,
        *,
        model: str | None = None,
        client: object | None = None,
    ) -> None:
        if OpenAI is None:
            raise ImportError(
                "openai is not installed. Install with: pip install -e '.[openai]'"
            )
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.client = client or OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def match_tokens(
        self,
        tokens: list[str],
        lexicon_base: dict[str, str],
    ) -> dict[str, Component | None]:
        unique_tokens = sorted(set(tokens))
        if not unique_tokens:
            return {}
        if not lexicon_base:
            return dict.fromkeys(unique_tokens)

        lexicon_lines = [
            f"- {lemma} -> {component}"
            for lemma, component in sorted(lexicon_base.items())
        ]
        user_prompt = (
            "Polarization lexicon (canonical Hebrew lemmas):\n"
            f"{chr(10).join(lexicon_lines)}\n\n"
            "Tokens to classify:\n"
            f"{json.dumps(unique_tokens, ensure_ascii=False)}\n\n"
            "Return JSON with this exact shape:\n"
            '{"matches": {"<token>": "issue"|"affective"|null, ...}}\n'
            "Include every token from the list exactly once as a key."
        )

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned an empty response")

        payload = json.loads(content)
        raw_matches = payload.get("matches", {})
        return self._validate_matches(unique_tokens, raw_matches)

    def _validate_matches(
        self,
        tokens: list[str],
        raw_matches: dict[str, object],
    ) -> dict[str, Component | None]:
        validated: dict[str, Component | None] = {}

        for token in tokens:
            value = raw_matches.get(token)
            if value is None:
                validated[token] = None
                continue
            if value not in ("issue", "affective"):
                raise ValueError(
                    f"Invalid component {value!r} for token {token!r} from OpenAI"
                )
            validated[token] = value

        return validated
