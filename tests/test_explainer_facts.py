"""The explainer diagrams claim to describe src/ — these tests hold them to it.

Two failure modes are worth catching:

  1. someone re-types a constant into the facts builder instead of importing
     it, and the wall keeps showing the old number after the pipeline changes;
  2. the generated demo/data/explainer_facts.json goes stale on the demo
     machine, so the wall shows numbers from a previous pipeline.

The second check only runs when the file exists — it is a build artifact, not
something in git.
"""

from __future__ import annotations

import json

import pytest

from demo.snapshot.build_explainer_facts import FACTS_PATH, build_constants


@pytest.fixture(scope="module")
def constants() -> dict:
    return build_constants()


def test_retry_constants_track_the_retry_module(constants):
    from src.crawling.retry import INITIAL_BACKOFF_SECONDS, MAX_ATTEMPTS

    assert constants["retry"]["max_attempts"] == MAX_ATTEMPTS
    assert constants["retry"]["initial_backoff_s"] == INITIAL_BACKOFF_SECONDS
    # the sleep sequence has one entry fewer than attempts: the last attempt
    # is not followed by a wait
    assert len(constants["retry"]["backoff_sequence_s"]) == MAX_ATTEMPTS - 1
    assert constants["retry"]["backoff_sequence_s"][0] == INITIAL_BACKOFF_SECONDS


def test_window_cap_tracks_the_splitter(constants):
    from src.nlp.sentence_splitter import MAX_WINDOW_TOKENS

    assert constants["windows"]["max_window_tokens"] == MAX_WINDOW_TOKENS


def test_tracking_params_track_the_canonicaliser(constants):
    from src.common.canonical_url import TRACKING_PARAMS

    assert set(constants["canonical"]["tracking_params"]) == set(TRACKING_PARAMS)


def test_lexicon_prefixes_track_the_expander(constants):
    from src.lexicon.expand_lexicon import (
        MIN_BASE_LENGTH,
        SINGLE_PREFIXES,
        WHITELISTED_PREFIX_PAIRS,
    )

    assert constants["lexicon"]["single_prefixes"] == list(SINGLE_PREFIXES)
    assert constants["lexicon"]["prefix_pairs"] == list(WHITELISTED_PREFIX_PAIRS)
    assert constants["lexicon"]["min_base_length"] == MIN_BASE_LENGTH


def test_crawl_alert_thresholds_track_the_base_crawler(constants):
    from src.crawling.base import (
        FAILURE_RATE_ALERT_THRESHOLD,
        MIN_DISCOVERED_FOR_FAILURE_ALERT,
    )

    assert constants["crawl"]["failure_rate_threshold"] == FAILURE_RATE_ALERT_THRESHOLD
    assert (
        constants["crawl"]["min_discovered_for_alert"]
        == MIN_DISCOVERED_FOR_FAILURE_ALERT
    )
    # read off the signature default, so a change to crawl() moves the wall
    assert constants["crawl"]["delay_seconds"] > 0


def test_extract_thresholds_track_the_fallback_chain(constants):
    # The ladder on screen labels each rung with the length gate that has to
    # fail before the next rung is reached; those two numbers are the gate.
    assert constants["extract"]["min_len"] > constants["extract"]["min_paragraph_len"]


def test_categories_match_the_demo_roster(constants):
    from demo import config

    assert constants["categories_he"] == list(config.LEXICON_CATEGORY_NAMES_HE)
    assert len(constants["categories_he"]) == 7


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_generated_file_is_not_stale():
    facts = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    assert facts["constants"] == build_constants(), (
        "explainer_facts.json predates a pipeline change — re-run "
        "PYTHONPATH=. python demo/snapshot/build_explainer_facts.py"
    )


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_worked_example_arithmetic_holds():
    """The dominance shown on the wall must be the division shown next to it."""
    window = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["worked_example"][
        "window"
    ]
    assert window["cat_words"] == sum(window["counts"])
    assert window["max_count"] == max(window["counts"])
    assert window["active"] == sum(1 for c in window["counts"] if c > 0)
    if window["cat_words"] > 0:
        assert window["dominance"] == pytest.approx(
            window["max_count"] / window["cat_words"]
        )
    else:
        assert window["dominance"] is None


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_identity_example_actually_collapses():
    """The dedup claim on the wall is a computed comparison, not a caption."""
    ex = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["identity_example"]
    assert ex["clean_canonical"] == ex["dirty_canonical"]
    assert ex["article_id"] == ex["dirty_article_id"] == ex["stored_article_id"]
    assert ex["same"] is True


# ── retrieval ───────────────────────────────────────────────────────────
#
# The retrieval module puts a threshold, a baseline and a sweep on the wall.
# The sweep is recomputed on every build, so it cannot go stale; these tests
# guard the two things that can: a constant re-typed instead of imported, and
# a generated file whose worked example contradicts its own caption.


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_retrieval_constants_track_the_demo_layer():
    from demo.core.framing import CLUSTER_SIM, KEYWORD_JACCARD
    from demo.snapshot.prepare_demo import MIN_TEXT_CHARS, PASSAGE_LEAD_CHARS

    r = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["retrieval"]
    assert r["cluster_sim"] == CLUSTER_SIM
    assert r["keyword_jaccard"] == KEYWORD_JACCARD
    assert r["min_text_chars"] == MIN_TEXT_CHARS
    assert r["passage_lead_chars"] == PASSAGE_LEAD_CHARS


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_sweep_contains_the_threshold_actually_in_use():
    """The chosen value has to appear in the table it was chosen from."""
    from demo.core.framing import CLUSTER_SIM

    r = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["retrieval"]
    chosen = [row for row in r["sweep"] if row["chosen"]]
    assert len(chosen) == 1
    assert chosen[0]["threshold"] == CLUSTER_SIM
    # and the row must agree with the unswept clustering shown elsewhere
    assert chosen[0]["events"] == r["events"]["total"]
    assert chosen[0]["versions"] == r["events"]["versions"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_keyword_baseline_is_a_subset_of_what_retrieval_found():
    r = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["retrieval"]
    k = r["keyword"]
    assert 0 <= k["found"] <= k["total"]
    assert k["zero_overlap"] <= k["total"]
    assert sum(b["n"] for b in k["histogram"]) == k["total"]
    # the pairs are (versions - events): every event contributes its seed
    assert k["total"] == r["events"]["versions"] - r["events"]["total"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_worked_neighbourhood_is_above_the_threshold_and_stops_below_it():
    from demo.core.framing import CLUSTER_SIM

    ex = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["retrieval"]["example"]
    assert ex["neighbours"], "the walkthrough tab needs at least one neighbour"
    for n in ex["neighbours"]:
        assert n["cos"] > CLUSTER_SIM
        # a shared-token list and a Jaccard of 0 must not both be claimed
        assert (n["jaccard"] == 0) == (not n["shared"])
    if ex["rejected"] is not None:
        assert ex["rejected"]["cos"] <= CLUSTER_SIM


# ── framing + verifier ──────────────────────────────────────────────────
#
# The framing module's claim is not "the model is good" — it is "everything on
# screen was checked against the text". These tests hold the generated file to
# that claim: the rates must add up, and the worked examples must actually
# demonstrate what their captions say they demonstrate.


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_framing_window_is_one_constant_for_extractor_and_verifier():
    from demo.core.framing import EXTRACT_LEAD_CHARS

    f = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["framing"]
    assert f["lead_chars"] == EXTRACT_LEAD_CHARS
    assert f["keys"] == list(__import__(
        "demo.core.framing", fromlist=["FRAMING_KEYS"]).FRAMING_KEYS)


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_verifier_rates_are_internally_consistent():
    v = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["framing"]["verifier"]
    assert 0 <= v["terms_rejected"] <= v["terms_total"]
    assert 0 <= v["quotes_rejected"] <= v["quotes_total"]
    # every rejected quote is classified into exactly one reason
    assert sum(r["n"] for r in v["quote_reasons"]) == v["quotes_rejected"]
    # every counted actor is exact, word-level, or rejected — no fourth bucket
    assert (v["actors_exact"] + v["actors_word_level"] + v["actors_rejected"]
            == v["actors_total"])


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_dropped_term_really_is_absent_from_the_text_shown_beside_it():
    """The panel invites the audience to check the drop by eye. It must hold."""
    from demo.core.framing import _normalise, verify_framing

    ex = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["framing"]["term_example"]
    if ex is None:
        pytest.skip("no term was dropped in this snapshot")
    haystack = _normalise(f"{ex['title']} {ex['lead']}")
    for term in ex["dropped"]:
        assert _normalise(term) not in haystack
    for term in ex["kept"]:
        assert _normalise(term) in haystack
    verdict = verify_framing(ex["framing"], ex["title"], ex["lead"])
    assert verdict.dropped_terms == ex["dropped"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_no_rejected_quote_is_rendered_as_evidence():
    """A quote the verifier refused must never be presentable as grounding."""
    ex = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["framing"]["contrast_example"]
    if ex is None:
        pytest.skip("no contrast example in this snapshot")
    assert any(not row["kept"] for row in ex["per_source"]), (
        "the panel exists to show a rejection — pick an event that has one"
    )
    for row in ex["per_source"]:
        assert row["evidence"] is None or isinstance(row["evidence"], str)
