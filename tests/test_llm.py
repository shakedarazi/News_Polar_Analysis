"""The one place a JSON completion is requested and unwrapped (src/nlp/llm.py).

Two things are pinned here. The first is the seam's own behaviour: it must send
the request every AI step used to build by hand, and it must decode Hebrew the
provider mangled. The second is the split that keeps the two credit pools apart
— `user_json` must never reach for the ingestion client, or a visitor asking a
question would spend the ingestion balance.

No network: the OpenAI client is replaced with a recorder.
"""

from __future__ import annotations

import json

import pytest

from src.nlp import llm
from src.nlp.llm import Message, ingestion_json, loads, user_json


class _Recorder:
    """Stands in for the OpenAI SDK client, capturing the request."""

    def __init__(self, content: str | None):
        self._content = content
        self.calls: list[dict] = []
        self.chat = self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = type("M", (), {"content": self._content})
        choice = type("C", (), {"message": message})
        return type("R", (), {"choices": [choice]})


@pytest.fixture
def recorder(monkeypatch):
    def install(content: str | None, *, target: str = "get_openai_client"):
        rec = _Recorder(content)
        monkeypatch.setattr(llm, target, lambda: rec)
        return rec

    return install


class TestTheRequestItSends:
    def test_json_mode_and_temperature_zero_are_not_per_call_decisions(self, recorder):
        rec = recorder('{"ok": true}')
        user_json(system="S", user="U", model="m")
        sent = rec.calls[0]
        assert sent["temperature"] == 0
        assert sent["response_format"] == {"type": "json_object"}
        assert sent["model"] == "m"

    def test_system_then_user_in_that_order(self, recorder):
        rec = recorder('{"ok": true}')
        user_json(system="S", user="U", model="m")
        assert rec.calls[0]["messages"] == [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "U"},
        ]

    def test_history_sits_between_the_system_prompt_and_the_new_question(self, recorder):
        rec = recorder('{"ok": true}')
        user_json(
            system="S",
            user="ומה לגבי הארץ?",
            history=[Message("user", "כמה כתבות יש ב-ynet?"), Message("assistant", "291")],
            model="m",
        )
        assert [m["role"] for m in rec.calls[0]["messages"]] == [
            "system",
            "user",
            "assistant",
            "user",
        ]
        assert rec.calls[0]["messages"][-1]["content"] == "ומה לגבי הארץ?"

    def test_max_tokens_is_omitted_unless_asked_for(self, recorder):
        rec = recorder('{"ok": true}')
        user_json(system="S", user="U", model="m")
        assert "max_tokens" not in rec.calls[0]
        user_json(system="S", user="U", model="m", max_tokens=300)
        assert rec.calls[1]["max_tokens"] == 300

    def test_an_unknown_history_role_is_refused(self, recorder):
        recorder('{"ok": true}')
        with pytest.raises(ValueError, match="Unsupported history role"):
            user_json(system="S", user="U", history=[Message("system", "sneaky")], model="m")

    def test_the_model_resolves_at_call_time_not_import_time(self, recorder, monkeypatch):
        """DEFAULT_MODEL was a module constant read from the environment once,
        so setting OPENAI_MODEL after import had no effect."""
        rec = recorder('{"ok": true}')
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
        user_json(system="S", user="U")
        assert rec.calls[0]["model"] == "gpt-4o"


class TestWhatItDoesWithTheAnswer:
    def test_an_empty_body_is_an_error_not_an_empty_answer(self, recorder):
        recorder(None)
        with pytest.raises(RuntimeError, match="empty response"):
            user_json(system="S", user="U", model="m")

    def test_a_json_array_is_refused(self, recorder):
        recorder("[1, 2, 3]")
        with pytest.raises(RuntimeError, match="expected an object"):
            user_json(system="S", user="U", model="m")

    def test_unparseable_output_names_itself_rather_than_being_returned(self, recorder):
        """One call site used to hand the raw string back as if it were the
        answer, so a broken response reached the screen looking like content."""
        recorder("I'm afraid I can't do that")
        with pytest.raises(RuntimeError, match="malformed JSON"):
            user_json(system="S", user="U", model="m")


class TestHebrewTheProviderMangled:
    def test_an_unescaped_acronym_quote_is_repaired(self):
        """Hebrew acronyms carry a quote inside the word (צה"ל, ח"כ, ארה"ב).
        A model not held to JSON emits it raw, breaking the string it sits in.
        Moved here from framing, which owned the repair and was one of five
        Hebrew-answering call sites that could be handed a צה"ל."""
        raw = '{"actor": "צה"ל", "voice": "active"}'
        assert loads(raw)["actor"] == 'צה"ל'

    def test_the_repair_reaches_every_caller_not_just_framing(self, recorder):
        recorder('{"summary": "ארה"ב הודיעה"}')
        assert user_json(system="S", user="U", model="m")["summary"] == 'ארה"ב הודיעה'

    def test_a_quote_that_really_is_a_delimiter_is_left_alone(self):
        """The repair only escapes a quote with a Hebrew letter on both sides,
        so an ordinary closing quote is not swallowed."""
        assert loads(json.dumps({"a": "שלום", "b": "עולם"}, ensure_ascii=False)) == {
            "a": "שלום",
            "b": "עולם",
        }


class TestTheTwoCreditPoolsStayApart:
    def test_user_json_spends_the_user_key(self, recorder):
        rec = recorder('{"ok": true}', target="get_openai_client")
        user_json(system="S", user="U", model="m")
        assert len(rec.calls) == 1

    def test_ingestion_json_spends_the_ingestion_key(self, recorder):
        rec = recorder('{"ok": true}', target="get_ingestion_openai_client")
        ingestion_json(system="S", user="U", model="m")
        assert len(rec.calls) == 1

    def test_the_two_entry_points_do_not_share_a_client(self, monkeypatch):
        """If either name were wired to the other's client, a visitor's question
        would draw down the ingestion balance (or the reverse). Neither client
        is installed here, so whichever one is reached raises — and the test
        proves which one that was."""
        monkeypatch.setattr(
            llm, "get_ingestion_openai_client", lambda: pytest.fail("user_json used ingestion")
        )
        monkeypatch.setattr(llm, "get_openai_client", lambda: _Recorder('{"ok": true}'))
        user_json(system="S", user="U", model="m")

        monkeypatch.setattr(
            llm, "get_openai_client", lambda: pytest.fail("ingestion_json used the user key")
        )
        monkeypatch.setattr(llm, "get_ingestion_openai_client", lambda: _Recorder('{"ok": true}'))
        ingestion_json(system="S", user="U", model="m")
