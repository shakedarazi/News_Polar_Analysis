"""Greetings must not get the "no data" refusal — but real questions must.

Users opening with "היי מה נשמע?" were told the database had insufficient
information, which reads as a broken assistant. Small talk about the assistant
itself is now answered directly, without an LLM call.

The risk in doing that is over-matching: a real data question that merely opens
with a greeting-like phrase must still reach retrieval. These pin both sides.
"""

from src.nlp.qa import _CAPABILITIES, _conversational_reply


class TestHandledWithoutTheModel:
    def test_greeting(self):
        assert _conversational_reply("היי מה נשמע?") is not None

    def test_bare_greeting(self):
        assert _conversational_reply("שלום") is not None

    def test_english_greeting(self):
        assert _conversational_reply("Hello") is not None

    def test_thanks(self):
        assert _conversational_reply("תודה רבה") is not None

    def test_what_can_you_do(self):
        assert _conversational_reply("מה אתה יכול לעשות?") == _CAPABILITIES

    def test_what_do_you_mean(self):
        # The assistant is single-turn, so it cannot resolve this from history.
        # Explaining what it can answer beats claiming the data is insufficient.
        assert _conversational_reply("מה הכוונה?") == _CAPABILITIES

    def test_reply_lists_real_capabilities(self):
        assert "קיטוב" in _CAPABILITIES and "מקורות" in _CAPABILITIES

    def test_punctuation_and_case_are_ignored(self):
        assert _conversational_reply("  HI!!  ") is not None


class TestPassedThroughToRetrieval:
    def test_greeting_prefix_on_a_real_question_is_not_swallowed(self):
        assert _conversational_reply("מה קורה בתחום הביטחון?") is None

    def test_whats_new_about_a_topic_is_a_data_question(self):
        assert _conversational_reply("מה חדש בכתבות על נתניהו?") is None

    def test_ordinary_data_question(self):
        assert _conversational_reply("כמה כתבות יש במערכת?") is None

    def test_out_of_domain_question_still_reaches_the_model_to_refuse(self):
        # Weather is not small talk about the assistant — the model must be the
        # one to refuse it, so the refusal stays a single, consistent rule.
        assert _conversational_reply("מה מזג האוויר בתל אביב?") is None

    def test_empty(self):
        assert _conversational_reply("   ") is None
