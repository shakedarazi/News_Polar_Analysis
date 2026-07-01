"""Tests for OpenAI polarization token matcher."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from src.lexicon.ai_matcher import OpenAITokenMatcher


def test_openai_matcher_parses_structured_response() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "matches": {
                                "הממשלה": "issue",
                                "התנגדה": "affective",
                                "החליטה": None,
                            }
                        },
                        ensure_ascii=False,
                    )
                )
            )
        ]
    )

    matcher = OpenAITokenMatcher(model="gpt-4o-mini", client=mock_client)
    result = matcher.match_tokens(
        ["הממשלה", "התנגדה", "החליטה"],
        {"ממשלה": "issue", "התנגד": "affective"},
    )

    assert result == {
        "הממשלה": "issue",
        "התנגדה": "affective",
        "החליטה": None,
    }
    mock_client.chat.completions.create.assert_called_once()
