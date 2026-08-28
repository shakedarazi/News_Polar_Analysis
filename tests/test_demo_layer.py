"""Unit tests for the demo agent layer's pure logic (no network, no data files)."""

from demo.core.classify import (MAJORITY_PRIOR, classify_baseline,
                                critic_verdict)
from demo.core.events import EventBroker
from demo.core.memory import Learnings


def test_baseline_keyword_hit():
    cat, conf, _ = classify_baseline("מכבי חיפה זכתה באליפות", "שער בדקה ה-90")
    assert cat == "ספורט"
    assert 0.3 < conf <= 0.6


def test_baseline_falls_back_to_majority_prior():
    cat, conf, reason = classify_baseline("כותרת נייטרלית לגמרי", "טקסט ללא רמזים")
    assert cat == MAJORITY_PRIOR
    assert conf == 0.3


def test_critic_keeps_confident_prediction_despite_lexicon():
    # conf >= 0.6 → the lexicon conflict opens a debate but does not override
    final, reason = critic_verdict("ביטחון", 0.8, [9, 0, 0, 0, 0, 0, 0])
    assert reason is not None
    assert final == "ביטחון"


def test_critic_adopts_lexicon_when_unsure():
    final, reason = critic_verdict("ביטחון", 0.45, [9, 0, 0, 0, 0, 0, 0])
    assert reason is not None
    assert final == "פוליטיקה"


def test_critic_silent_on_confident_agreement():
    final, reason = critic_verdict("פוליטיקה", 0.9, [9, 0, 0, 0, 0, 0, 0])
    assert reason is None
    assert final == "פוליטיקה"


def test_broker_state_tracks_metrics_and_reset():
    broker = EventBroker()
    broker.emit("metric", round=1, accuracy=0.5)
    broker.emit("reasoning", agent="nova", level="info", text_he="שלום")
    state = broker.state(agents=[])
    assert len(state["metrics"]) == 1 and len(state["feed"]) == 1
    broker.emit("reset")
    state = broker.state(agents=[])
    assert state["metrics"] == [] and state["feed"] == []


def test_learnings_few_shot_block():
    mem = Learnings()
    assert mem.few_shot_block() == ""
    mem.add("כותרת", "ביטחון", "פוליטיקה", "תוקן בדיון")
    assert "פוליטיקה" in mem.few_shot_block()
    assert len(mem) == 1
