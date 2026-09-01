"""The golden set and the arithmetic that reads it.

The eval exists to make a claim sayable — that the retrieval threshold has a
measured precision and a bounded recall — so the failure mode worth testing
against is not a crash. It is a number that keeps printing after the thing
underneath it stopped being true: a stratum weight left stale when the
snapshot changed, a pair that slipped through unlabelled and quietly shrank a
denominator, or the honesty flag going true while a model's labels are still
in the file.
"""

from __future__ import annotations

import json

import pytest

from demo.evals import run_evals as ev


def _pair(band: str, cosine: float, label: str, jaccard: float = 0.0) -> dict:
    return {"pair_id": f"{band}-{cosine}-{label}-{jaccard}", "band": band,
            "cosine": cosine, "jaccard": jaccard, "label": label,
            "labelled_by": "human", "note": ""}


# ── the arithmetic ──────────────────────────────────────────────────

class TestPrecision:
    def test_counts_only_pairs_the_threshold_accepts(self):
        rows = [_pair("0.94-1.01", 0.95, "same"),
                _pair("0.94-1.01", 0.96, "not_same"),
                _pair("0.86-0.90", 0.87, "same")]
        result = ev.precision_at(rows, 0.94)
        assert result["labelled_accepted"] == 2
        assert result["precision"] == 0.5

    def test_a_same_pair_below_the_threshold_does_not_help_precision(self):
        """It is a miss, not a hit — the arrangement that makes recall a
        separate question instead of the complement of this one."""
        rows = [_pair("0.94-1.01", 0.95, "not_same"),
                _pair("0.86-0.90", 0.87, "same")]
        assert ev.precision_at(rows, 0.94)["precision"] == 0.0

    def test_interval_stays_inside_the_unit_range_at_the_edges(self):
        """Why Wilson and not the normal approximation: at 25/25 the normal
        interval runs past 1.0 and reports a precision that cannot exist."""
        low, high = ev.wilson(25, 25)
        assert 0.0 <= low <= 1.0 and high <= 1.0
        assert low < 1.0, "a perfect sample of 25 is not certainty"


class TestRecall:
    def test_strata_are_weighted_by_population_not_by_labels(self):
        """The whole point of the estimator. Both strata contributed one
        positive from equal labels, but one stands for 39 pairs and the other
        for 1,784 — counting labels would put them at parity."""
        rows = [_pair("0.94-1.01", 0.95, "same"), _pair("0.94-1.01", 0.95, "not_same"),
                _pair("0.86-0.90", 0.87, "same"), _pair("0.86-0.90", 0.87, "not_same")]
        bands = ev._by_band(rows)
        assert bands["0.94-1.01"]["estimated_same"] == pytest.approx(39 * 0.5)
        assert bands["0.86-0.90"]["estimated_same"] == pytest.approx(1784 * 0.5)

    def test_reported_only_at_stratum_edges(self):
        """0.88 sits inside the 0.86-0.90 stratum. Reporting recall there would
        credit the cut with resolving a stratum the sample never split."""
        assert 0.88 in ev.THRESHOLDS, "precision at 0.88 is still direct and worth printing"
        assert 0.88 not in ev.RECALL_THRESHOLDS

    def test_the_sparse_region_is_a_bound_and_never_a_rate(self):
        rows = [_pair("0.94-1.01", 0.95, "same"),
                *[_pair("0.82-0.86", 0.83, "not_same") for _ in range(20)]]
        below = ev.recall_report(rows)["below_region"]
        assert below["same_found"] == 0
        assert below["rate_upper_95"] == pytest.approx(3 / 20)
        assert "rate" not in below, "0 positives in 20 labels is not a rate of 0"

    def test_a_positive_in_the_sparse_region_withdraws_the_bound(self):
        """The bound is only meaningful while nothing was found. One positive
        there and the honest answer is that the region needs more labels."""
        rows = [_pair("0.94-1.01", 0.95, "same"), _pair("0.82-0.86", 0.83, "same")]
        assert ev.recall_report(rows)["below_region"]["rate_upper_95"] is None


class TestBaselineComparison:
    def test_both_methods_are_scored_on_the_same_pairs(self):
        """demo/README.md item 16: the 77-pair figure compares the two on a set
        the embedding retriever defined, so it wins by construction. These two
        read the same denominator."""
        rows = [_pair("0.94-1.01", 0.95, "same", jaccard=0.4),
                _pair("0.94-1.01", 0.95, "same", jaccard=0.0),
                _pair("0.82-0.86", 0.83, "not_same", jaccard=0.0)]
        keyword = ev.keyword_baseline(rows)
        embedding = ev.embedding_on_sample(rows)
        assert keyword["recall_on_sample"] == pytest.approx(0.5)
        assert embedding["recall_on_sample"] == pytest.approx(1.0)
        assert keyword["zero_overlap_positives"] == 1


# ── the file itself ─────────────────────────────────────────────────

@pytest.fixture(scope="module")
def golden() -> list[dict]:
    return ev.load_golden()


class TestGoldenSet:
    def test_every_pair_is_labelled(self, golden):
        # load_golden() raises otherwise; this pins that it is the loader's job
        # and not something a caller has to remember.
        assert all(r["label"] in ("same", "not_same") for r in golden)

    def test_no_pair_appears_twice(self, golden):
        ids = [r["pair_id"] for r in golden]
        assert len(ids) == len(set(ids))

    def test_every_cosine_falls_inside_its_own_band(self, golden):
        for row in golden:
            low, high = (float(x) for x in row["band"].split("-"))
            assert low <= row["cosine"] < high, row["pair_id"]

    def test_pairs_are_cross_source(self, golden):
        """A same-outlet pair is a follow-up, not a second version of the
        story, and it is not the population the comparison runs on."""
        assert all(r["a"]["source"] != r["b"]["source"] for r in golden)

    def test_every_band_has_a_population_weight(self, golden):
        """A band present in the file but missing from BAND_POPULATION would
        raise; a band whose weight went stale after a resample would not, which
        is why sample_pairs.py prints the counts it drew from."""
        assert {r["band"] for r in golden} <= set(ev.BAND_POPULATION)

    def test_borderline_calls_carry_their_reasoning(self, golden):
        """The definition in golden/README.md cannot settle every pair. The
        ones it did not settle say so, so a reviewer can disagree with a stated
        line instead of re-deriving one."""
        notes = [r for r in golden if r["note"]]
        assert len(notes) >= 5

    def test_no_comments_in_the_tracked_file(self, golden):
        """Unlike demo/data/, this file is in git. Headlines and leads of
        published articles are public; audience comments are not."""
        fields = set().union(*(set(r["a"]) | set(r["b"]) for r in golden))
        assert not {"comments", "comment", "top_comment"} & fields


class TestHonestyFlag:
    """`human_reviewed` is what any wording on screen has to be gated on, so it
    is tested as a claim rather than as a field."""

    def test_a_full_file_of_model_labels_is_not_reviewed(self, monkeypatch):
        rows = [_pair("0.94-1.01", 0.95, "same"), _pair("0.86-0.90", 0.87, "not_same")]
        for row in rows:
            row["labelled_by"] = "claude-opus-5"
        monkeypatch.setattr(ev, "load_golden", lambda: rows)
        assert ev.build()["golden_set"]["human_reviewed"] is False

    def test_one_unreviewed_row_is_enough_to_hold_the_flag_down(self, monkeypatch):
        rows = [_pair("0.94-1.01", 0.95, "same"), _pair("0.86-0.90", 0.87, "not_same")]
        rows[1]["labelled_by"] = "claude-opus-5"
        monkeypatch.setattr(ev, "load_golden", lambda: rows)
        assert ev.build()["golden_set"]["human_reviewed"] is False

    def test_it_goes_true_only_when_every_row_is_human(self, monkeypatch):
        rows = [_pair("0.94-1.01", 0.95, "same"), _pair("0.86-0.90", 0.87, "not_same")]
        monkeypatch.setattr(ev, "load_golden", lambda: rows)
        assert ev.build()["golden_set"]["human_reviewed"] is True

    def test_the_current_file_reports_its_labeller(self, golden):
        assert all(r.get("labelled_by") for r in golden), "a label with no source is not evidence"


# ── the review pass ─────────────────────────────────────────────────

from demo.evals import review as rv  # noqa: E402


def _reviewable(band: str, label: str, proposed: str, by: str = "claude-opus-5") -> dict:
    row = _pair(band, float(band.split("-")[0]) + 0.005, label)
    row["proposed_label"] = proposed
    row["proposed_by"] = "claude-opus-5"
    row["labelled_by"] = by
    return row


class TestAgreement:
    def test_undefined_until_a_human_has_seen_something(self):
        rows = [_reviewable("0.94-1.01", "same", "same")]
        assert ev.agreement(rows) is None

    def test_counts_only_rows_a_human_reviewed(self):
        rows = [
            _reviewable("0.94-1.01", "same", "same", by="human"),
            _reviewable("0.90-0.92", "not_same", "same", by="human"),
            _reviewable("0.86-0.90", "same", "not_same"),  # still the model's
        ]
        result = ev.agreement(rows)
        assert result["reviewed"] == 2
        assert result["agreed"] == 1
        assert result["rate"] == 0.5

    def test_reports_which_way_the_reviewer_moved(self):
        """Direction matters: a reviewer who only ever flips toward not_same is
        reading the definition more strictly than the labels were written, and
        that is a fact about the definition, not about the retriever."""
        rows = [
            _reviewable("0.90-0.92", "not_same", "same", by="human"),
            _reviewable("0.86-0.90", "same", "not_same", by="human"),
            _reviewable("0.92-0.94", "not_same", "same", by="human"),
        ]
        result = ev.agreement(rows)
        assert result["flipped_to_not_same"] == 2
        assert result["flipped_to_same"] == 1


class TestReviewQueue:
    def test_unreviewed_pairs_come_first(self):
        rows = [
            _reviewable("0.90-0.92", "same", "same", by="human"),
            _reviewable("0.86-0.90", "same", "same"),
        ]
        assert rv.queue_order(rows)[0]["labelled_by"] != "human"

    def test_ordered_by_what_a_label_buys(self):
        """The bands at and above 0.90 decide precision and 0.86-0.90 decides
        recall; the sparse ones only widen a bound. A reviewer who stops early
        should have spent the time on the two headline numbers."""
        rows = [_reviewable(b, "same", "same") for b in reversed(rv.BAND_ORDER)]
        assert [r["band"] for r in rv.queue_order(rows)] == rv.BAND_ORDER

    def test_every_band_in_the_file_can_be_ordered(self, golden):
        """A band the queue cannot place raises ValueError inside the server,
        where nobody is watching the log."""
        assert {r["band"] for r in golden} <= set(rv.BAND_ORDER)

    def test_the_model_answer_survives_the_review(self, golden):
        """`label` is overwritten by the reviewer, so the model's answer needs
        its own field or the agreement number cannot be computed afterwards."""
        assert all(r.get("proposed_label") in ("same", "not_same") for r in golden)
        assert all(r.get("proposed_by") for r in golden)

    def test_a_write_replaces_the_file_whole(self, tmp_path, monkeypatch):
        """Rewritten through a temp file and os.replace: a half-written golden
        set would still load and still score, and be wrong in a way no check
        here would catch."""
        target = tmp_path / "event_pairs.jsonl"
        target.write_text("", encoding="utf-8")
        monkeypatch.setattr(rv, "GOLDEN_PATH", target)
        rv.save_rows([_reviewable("0.94-1.01", "same", "same", by="human")])
        written = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
        assert len(written) == 1 and written[0]["labelled_by"] == "human"
        assert not list(tmp_path.glob("tmp*")), "the temp file must not survive"
