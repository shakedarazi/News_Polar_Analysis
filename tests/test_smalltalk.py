"""Greetings must not get the "no data" refusal — but real questions must.

Users opening with "היי מה נשמע?" were told the database had insufficient
information, which reads as a broken assistant. Small talk about the assistant
itself is now answered directly, without an LLM call.

The risk in doing that is over-matching: a real data question that merely opens
with a greeting-like phrase must still reach retrieval. These pin both sides.
"""

from src.rag.smalltalk import CAPABILITIES, reply_for


class TestHandledWithoutTheModel:
    def test_greeting(self):
        assert reply_for("היי מה נשמע?") is not None

    def test_bare_greeting(self):
        assert reply_for("שלום") is not None

    def test_english_greeting(self):
        assert reply_for("Hello") is not None

    def test_thanks(self):
        assert reply_for("תודה רבה") is not None

    def test_what_can_you_do(self):
        assert reply_for("מה אתה יכול לעשות?") == CAPABILITIES

    def test_what_do_you_mean_opening_a_thread(self):
        # Nothing has been said yet, so there is nothing to explain: the
        # capabilities blurb beats claiming the data is insufficient.
        assert reply_for("מה הכוונה?") == CAPABILITIES

    def test_what_do_you_mean_mid_thread_is_a_real_follow_up(self):
        # The assistant used to be single-turn and answered this with the
        # blurb, which was the only thing it could do. It has the history now,
        # so the question belongs to the model.
        assert reply_for("מה הכוונה?", has_history=True) is None

    def test_reply_lists_real_capabilities(self):
        assert "קיטוב" in CAPABILITIES and "מקורות" in CAPABILITIES

    def test_punctuation_and_case_are_ignored(self):
        assert reply_for("  HI!!  ") is not None


class TestPassedThroughToRetrieval:
    def test_greeting_prefix_on_a_real_question_is_not_swallowed(self):
        assert reply_for("מה קורה בתחום הביטחון?") is None

    def test_whats_new_about_a_topic_is_a_data_question(self):
        assert reply_for("מה חדש בכתבות על נתניהו?") is None

    def test_ordinary_data_question(self):
        assert reply_for("כמה כתבות יש במערכת?") is None

    def test_out_of_domain_question_still_reaches_the_model_to_refuse(self):
        # Weather is not small talk about the assistant — the model must be the
        # one to refuse it, so the refusal stays a single, consistent rule.
        assert reply_for("מה מזג האוויר בתל אביב?") is None

    def test_empty(self):
        assert reply_for("   ") is None
