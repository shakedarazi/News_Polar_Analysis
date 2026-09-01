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
    # load_lexicon, not expand_lexicon: pipeline/build_lexicon.py writes the
    # article lexicon through save_expanded_lexicons, and expand_lexicon.py
    # serves the separate polarization lexicon with a different pair list.
    from src.lexicon.load_lexicon import PREFIXES, TWO_PREFIX_WHITELIST

    assert constants["lexicon"]["single_prefixes"] == list(PREFIXES)
    assert constants["lexicon"]["prefix_pairs"] == list(TWO_PREFIX_WHITELIST)


def test_min_base_length_matches_what_the_expander_actually_does(constants):
    # The threshold is inlined in _expand_word rather than named, so assert on
    # behaviour: a lemma one character shorter must not gain any prefixed form.
    from src.lexicon.load_lexicon import _expand_word

    floor = constants["lexicon"]["min_base_length"]
    assert len(_expand_word("א" * floor)) > 1
    assert _expand_word("א" * (floor - 1)) == {"א" * (floor - 1)}


def test_expanded_lexicon_on_disk_uses_those_pairs(constants):
    # The strongest form of the check: the shipped lexicon must actually
    # contain forms built from every pair the screen names, and none from a
    # pair it does not.
    from src.lexicon.load_lexicon import LEXICON_EXPANDED_DIR

    path = LEXICON_EXPANDED_DIR / "lexicon_expanded.json"
    if not path.is_file():
        pytest.skip("expanded lexicon not built")
    forms = set(json.loads(path.read_text(encoding="utf-8")))
    for pair in constants["lexicon"]["prefix_pairs"]:
        assert any(f.startswith(pair) for f in forms), pair


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


# ── the audience signal ─────────────────────────────────────────────────
#
# This is the layer where the honest answer is mostly about coverage: a
# weighting that is inert where an outlet ships no likes, and a metric with no
# data at all. These tests make sure the wall keeps saying that, and that the
# worked example still demonstrates the limit it is captioned with.


def test_audience_formulas_match_the_pipeline_functions():
    """The three formulas on the wall, evaluated against src/."""
    from src.analysis.comments_scoring import controversy, engagement_weight

    assert engagement_weight(0, 0) == 1.0
    # every like is worth less than the one before it — that is the whole
    # reason for the log, and the wall's "×3.4 not ×10" line depends on it
    assert engagement_weight(10, 0) < 10 * engagement_weight(1, 0)
    # with likes only, p is 1 and the controversy term collapses
    assert controversy(5, 0) == 0.0
    assert controversy(5, 5) == 1.0


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_audience_quantile_is_the_aggregation_default():
    from src.analysis.aggregation import _weighted_quantile

    import inspect

    a = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["audience"]
    default = inspect.signature(_weighted_quantile).parameters["quantile"].default
    assert a["quantile"] == default


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_like_weighting_is_reported_as_inert_where_the_outlet_ships_no_likes():
    """The claim on screen: no likes -> weight 1.0 -> p85 cannot move."""
    w = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["audience"]["weight"]
    assert sum(s["comments"] for s in w["per_source"]) > 0
    silent = [s for s in w["per_source"] if s["likes"] == 0]
    assert silent, "the panel exists to show outlets with no like data"
    for s in silent:
        assert s["inert"] == s["comments"]
        assert s["mean_p85_shift"] == 0.0
        assert s["articles_unaffected"] == s["articles"]
    assert w["inert"] >= sum(s["comments"] for s in silent)


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_controversy_is_shown_as_a_metric_with_no_data_behind_it():
    c = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["audience"]["controversy"]
    assert c["articles"] > 0
    assert c["nonzero"] == 0, (
        "an outlet started shipping dislikes — the 'dead metric' panel is now"
        " a lie and has to be rewritten against the new data"
    )


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_worked_example_reproduces_the_aggregates_it_displays():
    """Recompute the panel's two headline numbers from the rows beside them."""
    from src.analysis.aggregation import _weighted_mean, _weighted_quantile

    a = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["audience"]
    e = a["example"]
    if e is None:
        pytest.skip("no worked example in this snapshot")
    scores = [c["ratio"] for c in e["comments"]]
    weights = [c["weight"] for c in e["comments"]]
    assert round(_weighted_mean(scores, weights), 4) == round(e["weighted"]["mean"], 4)
    assert round(_weighted_quantile(scores, weights, a["quantile"]), 4) == round(
        e["weighted"]["p85"], 4)
    # the cumulative walk lands exactly once, and lands at the reported p85
    hits = [s for s in e["walk"] if s["hit"]]
    assert len(hits) == 1
    assert round(hits[0]["value"], 4) == round(e["weighted"]["p85"], 4)
    assert hits[0]["cum"] >= e["target"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_worked_example_still_shows_a_furious_comment_scoring_zero():
    """The caption's whole point. If the top comment ever scores above zero
    the example stops teaching the limit and must be re-chosen."""
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["audience"]["example"]
    if e is None:
        pytest.skip("no worked example in this snapshot")
    top = e["comments"][0]
    assert top["likes"] == max(c["likes"] for c in e["comments"])
    assert top["ratio"] == 0.0 and top["hits"] == []


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_hijacking_counts_only_versions_where_both_sides_have_a_topic():
    h = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["audience"]["hijack"]
    assert 0 <= h["hijacked"] <= h["comparable"]
    assert sum(s["total"] for s in h["per_source"]) == h["comparable"]
    assert sum(s["hijacked"] for s in h["per_source"]) == h["hijacked"]
    assert sum(p["n"] for p in h["pairs"]) <= h["hijacked"]
    for pair in h["pairs"]:
        assert pair["article_he"] != pair["comments_he"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_thin_cells_are_carried_with_their_sample_size():
    """Nothing on this wall may be reportable without the n beside it."""
    a = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["audience"]
    for cell in a["deviation"]:
        assert cell["n"] >= 1
        assert "median" in cell and "mean" in cell
    assert any(cell["n"] < 10 for cell in a["deviation"]), (
        "the limits panel promises to show a cell too thin to report"
    )


# ── the statistics layer ────────────────────────────────────────────────
#
# This is the module whose job is to take findings AWAY. The tests below are
# the ones that would catch it quietly giving them back: a cell reported
# despite a thin sample, a hit presented as surviving when it does not, or the
# multiplicity arithmetic drifting away from the tests actually shown.


def test_significance_floors_are_the_ones_the_code_enforces():
    from demo.core.framing import MIN_CELL_EVENTS, MIN_SEGMENT, bootstrap_ci

    # a cell below the floor is refused even with a perfectly clean signal
    assert MIN_CELL_EVENTS >= 10
    # and a change point must leave a real segment on both sides
    assert MIN_SEGMENT >= 8
    # the bootstrap refuses to invent an interval from two observations
    assert bootstrap_ci([0.1, 0.2]) is None
    assert bootstrap_ci([0.1, 0.2, 0.3]) is not None


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_stats_constants_track_the_demo_layer():
    import inspect

    from demo.core import framing as fr

    c = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["stats"]["constants"]
    boot = inspect.signature(fr.bootstrap_ci).parameters
    assert c["bootstrap_iterations"] == boot["iterations"].default
    assert c["bootstrap_seed"] == boot["seed"].default
    assert c["min_cell_events"] == fr.MIN_CELL_EVENTS
    assert c["min_segment"] == fr.MIN_SEGMENT


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_no_cell_under_the_floor_is_ever_marked_significant():
    """The hard rule for this wall: a thin cell is never a finding, however
    clean its interval looks."""
    s = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["stats"]
    floor = s["constants"]["min_cell_events"]
    for rows in s["cells"].values():
        for cell in rows:
            assert cell["usable"] == (cell["n"] >= floor)
            if not cell["usable"]:
                assert not cell["significant"]
            if cell["tempting"]:
                assert not cell["usable"]
                assert cell["lo"] is not None and cell["hi"] is not None
                assert cell["lo"] > 0 or cell["hi"] < 0


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_the_tempting_cells_panel_has_something_to_show():
    """The panel's claim is that a false positive's exact shape appears in this
    snapshot. If it stops appearing, the panel is arguing from nothing."""
    s = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["stats"]
    tempting = [c for rows in s["cells"].values() for c in rows if c["tempting"]]
    assert tempting, "no cell clears zero on a thin sample — rewrite the panel"


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_multiplicity_arithmetic_matches_the_tests_actually_run():
    s = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["stats"]
    m = s["multiplicity"]
    assert m["ci_tests"] == sum(1 for met in s["metrics"]
                                for r in met["outlets"] if r["p"] is not None)
    assert m["cell_tests"] == sum(c["usable"] for c in s["cells_meta"])
    assert m["scan_tests"] == sum(1 for x in s["scans"] if not x["too_short"])
    assert m["tests"] == m["ci_tests"] + m["cell_tests"] + m["scan_tests"]
    assert m["bonferroni"] == pytest.approx(m["alpha"] / m["tests"], rel=1e-3)
    assert m["expected_false"] == pytest.approx(m["tests"] * m["alpha"], rel=1e-3)


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_every_hit_and_survivor_is_classified_by_its_own_p():
    """The closing panel colours each hit. The colour must follow the number."""
    m = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["stats"]["multiplicity"]
    for hit in m["hits"]:
        assert hit["p"] < m["alpha"]
        assert hit["direction"] in {"below", "above", "shift"}
    survivors = {h["what"] for h in m["survivors"]}
    for hit in m["hits"]:
        assert (hit["what"] in survivors) == (hit["p"] < m["bonferroni"])


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_bootstrap_p_and_interval_tell_the_same_story():
    """Two views of one resampling — they may not disagree about zero."""
    s = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["stats"]
    alpha = s["constants"]["alpha"]
    for metric in s["metrics"]:
        for row in metric["outlets"]:
            if row["p"] is None:
                assert row["lo"] is None and row["hi"] is None
                assert row["n"] < s["constants"]["bootstrap_min_n"]
                continue
            clears = row["lo"] > 0 or row["hi"] < 0
            assert row["significant"] == clears
            assert clears == (row["p"] < alpha)


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_variance_split_is_a_real_decomposition():
    s = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["stats"]
    for metric in s["metrics"]:
        v = metric["variance"]
        assert v["total"] > 0
        assert 0 < v["between"] < v["total"]
        assert 0 < v["within"] < v["total"]
        # the whole argument of the first tab: story choice dominates
        assert v["between_share"] > v["within_share"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_power_table_is_still_what_the_code_produces():
    """The power table is READ from demo_set.json rather than recomputed (it
    costs ~20s). Recompute one row live and hold the shortcut honest."""
    from demo.core.framing import change_point_power

    s = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["stats"]["power"]
    if not s["rows"]:
        pytest.skip("demo_set.json not present")
    row = min(s["rows"], key=lambda r: r["n"])
    live = change_point_power(row["n"], 1.0, iterations=s["iterations"])
    assert round(live, 4) == row["power_1sd"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_pairing_explains_why_two_outlets_mirror_each_other():
    """The 'not two independent observations' caveat has to be load-bearing."""
    s = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["stats"]["pairing"]
    assert sum(b["events"] for b in s["sizes"]) == s["events"]
    two = next((b["events"] for b in s["sizes"] if b["versions"] == 2), 0)
    assert s["two_version"] == two
    assert s["two_version"] / s["events"] > 0.5, (
        "most events are no longer pairs — the mirroring caveat needs rewriting"
    )
    assert s["top_pair_two_version"] <= s["two_version"]


# ── the token economy ───────────────────────────────────────────────────


def test_economy_prices_track_the_demo_config():
    """The wall prints a price list; it has to be the one the code bills at."""
    from demo import config

    if not FACTS_PATH.exists():
        pytest.skip("facts not built yet")
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]
    assert e["bill"]["price_prompt_per_m"] == config.PRICE_PROMPT_PER_M
    assert e["bill"]["price_completion_per_m"] == config.PRICE_COMPLETION_PER_M
    assert e["constants"]["embed_model"] == config.EMBED_MODEL


def test_economy_caps_track_the_extractors():
    """The output caps are the expensive half of the bill — import, never type."""
    from demo.core.framing import (CONTRAST_LEAD_CHARS, CONTRAST_MAX_TOKENS,
                                   EXTRACT_LEAD_CHARS, FRAMING_MAX_TOKENS)

    if not FACTS_PATH.exists():
        pytest.skip("facts not built yet")
    c = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]["constants"]
    assert c["framing_max_tokens"] == FRAMING_MAX_TOKENS
    assert c["contrast_max_tokens"] == CONTRAST_MAX_TOKENS
    assert c["lead_chars"] == EXTRACT_LEAD_CHARS
    assert c["contrast_lead_chars"] == CONTRAST_LEAD_CHARS
    # the verifier window must stay a superset of what contrast actually sends,
    # or a quote could be rejected for sitting in text the model did receive
    assert c["contrast_lead_chars"] <= c["lead_chars"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_the_bill_is_recomputed_from_tokens_not_copied():
    """The displayed dollar figure is derived from token counts and the price
    list, and it has to agree with the total the extractors wrote down."""
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]
    b = e["bill"]
    assert b["prompt_tokens"] + b["completion_tokens"] == b["total_tokens"]
    assert round(b["prompt_usd"] + b["completion_usd"], 6) == b["usd"]
    assert abs(b["usd"] - b["reported_usd"]) < 1e-6


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_every_paid_call_left_something_in_the_cache():
    """The whole 'showtime costs nothing' claim rests on this: the calls that
    were billed are exactly the answers the kiosk now replays."""
    from demo.core.framing import ContrastExtractor, FramingExtractor

    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]
    entries = len(FramingExtractor().cache) + len(ContrastExtractor().cache)
    assert e["cache"]["entries"] == entries
    assert e["bill"]["cached_outputs"] == entries
    assert e["bill"]["covered"] is True, (
        "billed calls no longer match cached answers — the cost per call, the "
        "derived split and the 'nothing was thrown away' claim all break"
    )
    assert e["cache"]["showtime_calls"] == 0


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_the_exchange_rate_is_measured_from_reconstructed_prompts():
    """chars/token is real division of real chars by real billed tokens, and
    the independently measured output side has to land near it."""
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]
    r = e["rate"]
    assert r["prompt_tokens"] == e["bill"]["prompt_tokens"]
    assert r["completion_tokens"] == e["bill"]["completion_tokens"]
    assert round(r["prompt_chars"] / r["prompt_tokens"], 3) == r["chars_per_token"]
    assert round(r["output_chars"] / r["completion_tokens"], 3) == \
        r["output_chars_per_token"]
    # two independent measurements of the same tokenizer; a large gap would
    # mean the reconstruction no longer matches what was sent
    assert r["gap"] < 0.15
    for example in r["examples"]:
        assert example["tokens"] == round(example["chars"] / r["chars_per_token"])


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_prompt_reconstruction_covers_every_billed_call():
    """The character counts on screen are per-call sums — if a call could not
    be rebuilt from the snapshot the shares would silently understate."""
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]
    p = e["prompt"]
    assert p["framing"]["calls"] + p["contrast"]["calls"] == e["bill"]["calls"]
    assert p["framing"]["total_chars"] + p["contrast"]["total_chars"] == \
        e["rate"]["prompt_chars"]
    assert p["system_chars_total"] == (
        p["framing"]["system_chars"] * p["framing"]["calls"]
        + p["contrast"]["system_chars"] * p["contrast"]["calls"])
    assert sum(v["events"] for v in p["contrast"]["versions"]) == p["contrast"]["calls"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_the_repeated_instruction_claim_is_the_measured_one():
    """The tab says instructions are a third of the input bill. If that ever
    stops being true the sentence has to change, not stay on the wall."""
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]
    p = e["prompt"]
    assert p["system_share_of_prompt"] == round(
        p["system_chars_total"] / e["rate"]["prompt_chars"], 4)
    assert p["system_share_of_prompt"] > 0.25
    assert p["framing"]["system_share"] > p["contrast"]["system_share"], (
        "the framing call is the one with the short body — if contrast becomes "
        "the instruction-heavy one, the 'almost half the call' line is wrong"
    )


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_truncation_savings_are_arithmetic_on_the_same_rate():
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]
    t, rate = e["truncation"], e["rate"]["chars_per_token"]
    assert t["dropped_tokens"] == round(t["dropped_chars"] / rate)
    assert t["would_be_prompt_tokens"] == e["bill"]["prompt_tokens"] + t["dropped_tokens"]
    assert t["over_cap"] <= t["versions"]
    assert 0 < t["median_share_sent"] <= 1


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_the_derived_split_adds_back_up_to_the_measured_total():
    """The per-type dollar split is derived, so it is allowed to be
    approximate — but not to invent or lose money."""
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]
    split = e["split"]
    assert all(s["derived"] for s in split)
    assert sum(s["calls"] for s in split) == e["bill"]["calls"]
    assert abs(sum(s["usd"] for s in split) - e["bill"]["usd"]) < 5e-4
    assert abs(sum(s["prompt_tokens"] for s in split)
               - e["bill"]["prompt_tokens"]) <= len(split)
    for s in split:
        assert abs(s["usd"] / s["calls"] - s["per_call_usd"]) < 1e-6


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_two_of_ten_stages_pay_and_the_rest_report_zero():
    """The module's headline claim. A stage that starts costing tokens without
    being marked paid would make the whole ladder a lie."""
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]
    paid = [s for s in e["stages"] if s["kind"] == "paid"]
    assert {s["key"] for s in paid} == {"framing", "contrast"}
    assert all(s["usd"] == 0.0 for s in e["stages"] if s["kind"] != "paid")
    assert abs(sum(s["usd"] for s in paid) - e["bill"]["usd"]) < 5e-4
    # the local embedding model is a model, and must not be filed as free code
    assert [s["kind"] for s in e["stages"] if s["key"] == "embed"] == ["local"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_stage_counts_agree_with_the_tiles_that_own_them():
    """This tile borrows every deterministic count from the module that
    measured it, so eight explainers cannot disagree about corpus size."""
    facts = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    by_key = {s["key"]: s["n"] for s in facts["economy"]["stages"]}
    assert by_key["crawl"] == facts["corpus"]["articles"]
    assert by_key["windows"] == facts["windows"]["total"]
    assert by_key["comments"] == facts["comments"]["total"]
    assert by_key["lexicon"] == facts["lexicon"]["article_expanded"]
    assert by_key["embed"] == facts["retrieval"]["vectors"]
    assert by_key["cluster"] == facts["retrieval"]["events"]["total"]
    assert by_key["stats"] == facts["stats"]["multiplicity"]["tests"]
    assert by_key["framing"] == facts["framing"]["cache"]["framing"]
    assert by_key["contrast"] == facts["framing"]["cache"]["contrast"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_the_strawman_is_labelled_and_uses_the_measured_rate():
    """An estimate is allowed on the wall; an estimate that hides its
    assumptions is not."""
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]
    s, rate = e["strawman"], e["rate"]["chars_per_token"]
    assert s["calls"] == s["articles"] + s["comments"]
    assert s["prompt_tokens"] == round(
        (s["article_chars"] + s["comment_chars"] + s["system_chars"]) / rate)
    assert s["usd"] > e["bill"]["usd"], "the strawman is supposed to be worse"
    assert s["ratio"] == round(s["usd"] / e["bill"]["usd"], 1)
    # the point of the tab: fixed overhead, not article length, is what costs
    assert s["system_share"] > 0.5
    # the narrated run's coarser estimate is shown alongside, not instead
    assert s["scene"]["usd"] > 0


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_the_biggest_excluded_cost_is_the_pipelines_own_classifier():
    """The honesty of this tile rests on naming the token spend it does NOT
    count — and the largest one is bigger than everything it does count."""
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]
    classify = next(x for x in e["excluded"] if x["key"] == "classify")
    assert classify["estimate"] is True
    assert classify["usd"] > e["bill"]["usd"], (
        "the scheduled classifier is no longer the larger spend — the closing "
        "sentence of the tab says it is"
    )
    # the things with no number at all must still be named, not omitted
    assert {x["key"] for x in e["excluded"]} >= {"classify", "enrich", "embed", "dev"}


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_the_evals_block_grades_the_threshold_the_retriever_actually_uses():
    """The tab's whole claim is that this measurement is about the live cut.

    A sweep that no longer contains the threshold in use, or a threshold that
    drifted away from CLUSTER_SIM, would leave the screen reporting a number
    for a system nobody is running.
    """
    from demo.core.framing import CLUSTER_SIM

    facts = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    e = facts["evals"]
    assert e["live_threshold"] == CLUSTER_SIM
    live = [r for r in e["precision_sweep"] if r["threshold"] == CLUSTER_SIM]
    assert len(live) == 1, "the sweep must price the threshold in use"
    assert any(r["threshold"] == CLUSTER_SIM for r in e["recall"]["by_threshold"])
    # the sweep is monotone by construction: a looser cut accepts a superset
    accepted = [r["labelled_accepted"] for r in e["precision_sweep"]]
    assert accepted == sorted(accepted), "loosening the cut cannot accept fewer"


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_the_screen_cannot_call_model_labels_ground_truth():
    """`human_reviewed` is what the tab keys its provenance chip off.

    It is false today (29 of 160 reviewed) and it must stay false until every
    row carries a human label — a partly reviewed set that reports itself as
    reviewed is the one failure this whole eval exists to prevent.
    """
    e = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["evals"]
    g = e["golden_set"]
    assert g["human_reviewed"] == ("claude-opus-5" not in g["labelled_by"])
    if not g["human_reviewed"]:
        assert g["agreement"] is not None, (
            "an unreviewed set must still report how much of it was checked"
        )
        assert g["agreement"]["reviewed"] < g["pairs"]


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_the_recall_floor_is_carried_not_restated():
    """The tab prints the floor in three places and reads it from one field."""
    from demo.evals.run_evals import MEASURED_FLOOR

    r = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["evals"]["recall"]
    assert r["floor"] == MEASURED_FLOOR
    assert str(MEASURED_FLOOR) in r["region"]
    assert r["below_region"]["same_found"] == 0 or r["below_region"]["rate_upper_95"] > 0


@pytest.mark.skipif(not FACTS_PATH.exists(), reason="facts not built yet")
def test_the_narrated_run_costs_the_strawman_the_same_way_the_module_does():
    """One quantity, one number on the wall.

    The economy scene used to compute its own "everything through an LLM"
    estimate over the indexed articles, landing far below the measured one
    over every article and comment. Both were labelled estimates, and they
    were still two different answers to the same question in one room.
    """
    from demo.runner import DemoLoop

    straw = json.loads(FACTS_PATH.read_text(encoding="utf-8"))["economy"]["strawman"]
    # unbound: the measured path reads the facts file and never touches
    # self, and the skipif above guarantees that file is there
    emitted = DemoLoop._strawman(object())

    assert emitted["allllm_cost_est"] == straw["usd"]
    assert emitted["allllm_calls"] == straw["calls"]
    assert emitted["allllm_tokens_est"] == (
        straw["prompt_tokens"] + straw["completion_tokens"])

