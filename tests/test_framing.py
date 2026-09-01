"""Framing extraction parsing and the grounding verifier (src/nlp/framing.py).

No network: every test feeds `parse_framing` a response body the model could
plausibly have returned. What is pinned here is the verifier's promise — that
nothing reaches a screen unless it occurs in the text the model was given.
"""

from __future__ import annotations

import json

from src.nlp.framing import EXTRACT_LEAD_CHARS, parse_framing, verify_framing

TITLE = "השר הכריז על הצעד המבורך בישיבת הממשלה"
LEAD = "שר האוצר הודיע היום כי התוכנית תיכנס לתוקף בחודש הבא, לאחר דיון ממושך."


def response(**fields) -> str:
    body = {
        "actor": None,
        "responsibility": None,
        "loaded_terms": [],
        "voice": "active",
        "lead_perspective": None,
    }
    body.update(fields)
    return json.dumps(body, ensure_ascii=False)


def parse(**fields):
    return parse_framing(response(**fields), title=TITLE, text=LEAD, model="test-model")


def test_a_loaded_term_that_is_in_the_headline_is_kept():
    result = parse(loaded_terms=["המבורך"])
    assert result.loaded_terms == ["המבורך"]
    assert result.dropped_terms == []
    assert result.violations == []


def test_a_term_the_model_invented_is_dropped_not_shown():
    result = parse(loaded_terms=["שערורייתי"])
    assert result.loaded_terms == []
    assert result.dropped_terms == ["שערורייתי"]
    assert "שערורייתי" in result.violations[0]


def test_a_correct_term_in_the_wrong_inflection_is_also_dropped():
    """The verifier compares strings, not morphology. It rejects some right
    answers, and both of its errors put less on screen rather than more —
    that asymmetry is the reason it is worth keeping."""
    result = parse(loaded_terms=["מברכת"])
    assert result.loaded_terms == []
    assert result.dropped_terms == ["מברכת"]


def test_quote_marks_do_not_break_a_match():
    result = parse_framing(
        response(loaded_terms=['"המבורך"']),
        title=TITLE,
        text=LEAD,
        model="test-model",
    )
    assert result.loaded_terms == ['"המבורך"']


def test_an_actor_named_by_surname_alone_still_counts_as_grounded():
    result = parse(actor="שר האוצר")
    assert result.actor == "שר האוצר"
    assert result.actor_grounded is True


def test_an_actor_absent_from_the_text_is_flagged_rather_than_shown():
    result = parse(actor="ראש הממשלה נתניהו")
    assert result.actor_grounded is False
    assert result.violations


def test_the_verifier_window_is_the_same_slice_the_model_read():
    """When extraction read 500 characters and verification searched 600, a
    term appearing only in 500-600 passed while the model never saw it. One
    constant serves both, and this test fails if they are ever split."""
    padding = "מילה " * 200
    text = padding[:EXTRACT_LEAD_CHARS - 10] + "צהוב " + "זנב " * 50
    inside = verify_framing(actor=None, loaded_terms=["צהוב"], title="", text=text)
    assert inside[2] == ["צהוב"]

    outside_text = padding[:EXTRACT_LEAD_CHARS + 40] + "צהוב"
    outside = verify_framing(actor=None, loaded_terms=["צהוב"], title="", text=outside_text)
    assert outside[3] == ["צהוב"]


def test_the_string_null_is_read_as_no_value():
    result = parse(actor="null", responsibility="None", lead_perspective="")
    assert result.actor is None
    assert result.responsibility is None
    assert result.lead_perspective is None


def test_an_unrecognised_voice_is_dropped_rather_than_stored():
    assert parse(voice="middle").voice is None
    assert parse(voice="passive").voice == "passive"


def test_loaded_terms_that_are_not_a_list_degrade_to_empty():
    result = parse_framing(
        json.dumps({"loaded_terms": "המבורך", "voice": "active"}, ensure_ascii=False),
        title=TITLE,
        text=LEAD,
        model="test-model",
    )
    assert result.loaded_terms == []


def test_an_unescaped_hebrew_acronym_quote_is_repaired():
    """Hebrew acronyms carry a quote inside the word (צה"ל, ח"כ). A model not
    held to JSON emits it raw, which breaks the string it sits in."""
    raw = '{"actor": "צה"ל", "responsibility": null, "loaded_terms": [], "voice": "active", "lead_perspective": null}'
    result = parse_framing(raw, title='צה"ל תקף הלילה', text="", model="test-model")
    assert result.actor == 'צה"ל'
    assert result.actor_grounded is True


def test_an_empty_extraction_is_a_valid_result_not_a_failure():
    result = parse()
    assert result.actor is None
    assert result.loaded_terms == []
    assert result.violations == []
    assert result.model == "test-model"


def test_a_generic_word_alone_does_not_ground_an_invented_name():
    """"ראש הממשלה נתניהו" must not pass merely because "הממשלה" appears in the
    headline. One matching word out of three is not the name being present."""
    result = parse(actor="ראש הממשלה נתניהו")
    assert result.actor_grounded is False


def test_half_a_two_word_name_is_enough():
    """The case the majority rule exists to keep: a full name in the headline,
    the surname alone in the extraction."""
    result = parse_framing(
        response(actor="טום באראק"),
        title="באראק נפגש עם השר",
        text="",
        model="test-model",
    )
    assert result.actor_grounded is True
