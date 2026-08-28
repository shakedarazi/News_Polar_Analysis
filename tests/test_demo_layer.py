"""Unit tests for the demo agent layer's pure logic (no network, no data files)."""

import asyncio

from demo.core.classify import (MAJORITY_PRIOR, classify_baseline,
                                critic_verdict)
from demo.core.control import DemoController
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


def test_broker_state_tracks_scene_and_gate():
    broker = EventBroker()
    broker.emit("scene", scene="arch", idx=1, total=8, title_he="א", subtitle_he="")
    broker.emit("arch_step", step="crawl", idx=0, status="active")
    broker.emit("gate", gate_id="s1-arch", hint_he="המשך", autoplay_ms=None)
    state = broker.state(agents=[])
    assert state["scene"]["scene"] == "arch"
    assert state["gate"]["gate_id"] == "s1-arch"
    assert len(state["arch_steps"]) == 1
    broker.emit("gate_cleared", gate_id="s1-arch")
    # a new scene clears the previous scene's payloads
    broker.emit("showcase", article_id="x", title="כותרת")
    broker.emit("scene", scene="rag", idx=4, total=8, title_he="ב", subtitle_he="")
    state = broker.state(agents=[])
    assert state["gate"] is None
    assert state["arch_steps"] == [] and state["showcase"] is None
    broker.emit("reset")
    assert broker.state(agents=[])["scene"] is None


def test_controller_gate_waits_for_advance():
    async def scenario():
        ctrl = DemoController()
        ctrl.autoplay = False
        assert ctrl.advance() is False  # no gate open yet
        task = asyncio.create_task(ctrl.gate("g1", "המשך"))
        await asyncio.sleep(0)  # let the gate open
        assert ctrl.current_gate == "g1"
        assert ctrl.advance() is True
        await asyncio.wait_for(task, timeout=1)
        assert ctrl.current_gate is None

    asyncio.run(scenario())


def test_learnings_few_shot_block():
    mem = Learnings()
    assert mem.few_shot_block() == ""
    mem.add("כותרת", "ביטחון", "פוליטיקה", "תוקן בדיון")
    assert "פוליטיקה" in mem.few_shot_block()
    assert len(mem) == 1
