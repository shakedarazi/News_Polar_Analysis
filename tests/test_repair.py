"""The repair loop is the one place a model gets a second try — these tests
are what stop that second try from being a way to launder a bad answer.

The loop is measured, not asserted: demo/data/repair_log.json is written by a
prepare-time run and read by the explainer module. So the checks come in two
kinds — unit tests on the rules themselves, which always run, and checks
against the recorded run, which are skipped when the artifact is absent.
"""

from __future__ import annotations

import json

import pytest

from demo.snapshot.build_explainer_facts import FACTS_PATH, REPAIR_LOG_PATH

VERSIONS = [
    ("ynet", "שר הביטחון הורה על סגירת המעבר",
     "ההחלטה התקבלה הבוקר לאחר התייעצות. גורמים במערכת אמרו כי אין שינוי."),
    ("mako", "המעבר ייסגר",
     "לפי הדיווח, ההחלטה תיכנס לתוקף מחר בבוקר."),
]


# ── the rules, tested directly ──────────────────────────────────────

def test_a_repair_may_not_touch_a_source_the_verifier_accepted():
    """The bug this guard exists for: the model answered `null` for quotes that
    were already grounded, and the violation count went down while good
    citations disappeared."""
    from demo.core.framing import _merge_evidence

    result = {"per_source": [
        {"source": "ynet", "evidence": "ההחלטה התקבלה הבוקר"},
        {"source": "mako", "evidence": "ציטוט שלא קיים בטקסט"},
    ]}
    patch = {"per_source": [
        {"source": "ynet", "evidence": None},
        {"source": "mako", "evidence": "לפי הדיווח"},
    ]}
    merged = _merge_evidence(result, patch, allowed={"mako"})
    by_source = {i["source"]: i["evidence"] for i in merged["per_source"]}
    assert by_source["ynet"] == "ההחלטה התקבלה הבוקר"
    assert by_source["mako"] == "לפי הדיווח"


def test_rejected_sources_are_exactly_the_ones_that_lost_a_quote():
    from demo.core.framing import _grounded_sources, _rejected_sources

    result = {"per_source": [
        {"source": "ynet", "evidence": "ההחלטה התקבלה הבוקר"},
        {"source": "mako", "evidence": "משפט שהומצא"},
    ]}
    assert _rejected_sources(result, VERSIONS) == {"mako"}
    assert _grounded_sources(result, VERSIONS) == {"ynet"}


def test_a_source_with_no_quote_is_not_a_rejection():
    """`evidence: null` is an honest answer, not a violation — otherwise the
    loop would chase items it has nothing to fix."""
    from demo.core.framing import _rejected_sources

    result = {"per_source": [{"source": "ynet", "evidence": None}]}
    assert _rejected_sources(result, VERSIONS) == set()


def test_the_loop_makes_no_call_when_the_network_is_off():
    """Showtime contract: a missing cache entry degrades to the pre-repair
    object, it does not reach for the network."""
    from demo.core.framing import Repairer

    repairer = Repairer(cache_path=FACTS_PATH.parent / "__no_such_cache.json")
    result = {"per_source": [{"source": "mako", "evidence": "משפט שהומצא"}]}
    out = repairer.repair_contrast("evt", result, VERSIONS, allow_network=False)
    assert out is result
    assert repairer.calls == 0


def test_the_production_cap_is_not_above_what_was_measured():
    from demo.core.framing import MAX_REPAIR_ATTEMPTS, REPAIR_ATTEMPTS_MEASURED

    assert 1 <= MAX_REPAIR_ATTEMPTS <= REPAIR_ATTEMPTS_MEASURED


# ── the recorded run ────────────────────────────────────────────────

@pytest.fixture(scope="module")
def log() -> dict:
    if not REPAIR_LOG_PATH.exists():
        pytest.skip("repair log not built yet")
    return json.loads(REPAIR_LOG_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def repair_facts() -> dict:
    if not FACTS_PATH.exists():
        pytest.skip("facts not built yet")
    return json.loads(FACTS_PATH.read_text(encoding="utf-8"))["repair"]


def test_no_valid_quote_survived_the_loop_as_a_deletion(log):
    """The number the guard exists to keep at zero."""
    assert log["valid_quotes_destroyed"] == 0


def test_recovered_and_refused_are_counted_apart(log):
    """Both outcomes clear the violation, and only one is a recovery. Reporting
    them as one number would overstate what the loop does."""
    assert log["quotes_regrounded"] > 0
    assert log["quotes_nulled_honestly"] > 0
    assert (log["quotes_regrounded"] + log["quotes_nulled_honestly"]
            <= log["violations_before"])


def test_the_extra_attempt_earned_nothing(log):
    """The finding that set the production cap. If a later run ever makes the
    second attempt pay, this test is the thing that says so."""
    from demo.core.framing import MAX_REPAIR_ATTEMPTS

    beyond = {int(k): v for k, v in log["accepted_by_attempt"].items()
              if int(k) > MAX_REPAIR_ATTEMPTS}
    assert sum(beyond.values()) == 0


def test_every_attempt_is_in_the_log(log):
    """Including the rejected ones — a loop that logs only its successes is a
    demo, not a measurement."""
    assert len(log["attempts"]) == log["calls"]
    assert len({a["key"] for a in log["attempts"]}) == log["items_entered"]
    assert log["calls"] >= log["items_entered"]


def test_violations_only_went_down(log):
    assert log["violations_after"] <= log["violations_before"]


def test_the_facts_do_not_re_type_the_constants(repair_facts):
    from demo.core.framing import (CONTRAST_LEAD_CHARS, EXTRACT_LEAD_CHARS,
                                   MAX_REPAIR_ATTEMPTS,
                                   REPAIR_ATTEMPTS_MEASURED,
                                   REPAIR_MAX_TOKENS)

    c = repair_facts["constants"]
    assert c["max_attempts"] == MAX_REPAIR_ATTEMPTS
    assert c["max_attempts_measured"] == REPAIR_ATTEMPTS_MEASURED
    assert c["max_tokens"] == REPAIR_MAX_TOKENS
    assert c["lead_chars"] == EXTRACT_LEAD_CHARS
    assert c["contrast_lead_chars"] == CONTRAST_LEAD_CHARS


def test_the_repair_bill_is_a_share_of_the_layer_it_adds_to(repair_facts):
    bill = repair_facts["bill"]
    assert bill["total_usd"] == pytest.approx(bill["layer_usd"] + bill["usd"],
                                              abs=1e-6)
    assert bill["share_of_layer"] == pytest.approx(bill["usd"] / bill["layer_usd"],
                                                   abs=1e-4)


def test_the_example_on_screen_is_a_quote_that_now_grounds(repair_facts):
    """The one before/after the wall shows has to be real in both directions:
    the rejected quote must genuinely fail the check, and the repaired one must
    genuinely pass it."""
    example = repair_facts["example"]
    if example is None:
        pytest.skip("no repaired example in this snapshot")

    from demo.core.framing import (EXTRACT_LEAD_CHARS, Snapshot, _normalise,
                                   build_event_clusters)

    snap = Snapshot()
    articles = snap.articles()
    haystack = None
    for event in build_event_clusters(snap):
        if event.headline != example["headline"]:
            continue
        for version in event.versions:
            if version.source == example["source"]:
                text = articles[version.article_id]["text"] or ""
                haystack = _normalise(f"{version.title} "
                                      f"{text[:EXTRACT_LEAD_CHARS]}")
    assert haystack is not None, "the example's source is not in the snapshot"
    assert _normalise(example["after"]) in haystack
    assert _normalise(example["before"]) not in haystack


def test_what_reaches_the_stage_is_a_subset_of_what_the_loop_fixed(repair_facts):
    stage, loop = repair_facts["stage"], repair_facts["loop"]
    assert 0 <= stage["recovered"] <= loop["regrounded"]
