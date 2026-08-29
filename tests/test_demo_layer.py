"""Unit tests for the demo agent layer's pure logic (no network, no data files)."""

import asyncio

from demo import config
from demo.core.control import DemoController
from demo.core.events import EventBroker
from demo.roles.agents import Scout, source_he


def test_broker_scene_payloads_accumulate_and_reset():
    broker = EventBroker()
    broker.emit("scene", scene="framing", idx=5, total=9, title_he="מסגור",
                subtitle_he="")
    broker.emit("framing", article_id="a", source="ynet")
    broker.emit("framing", article_id="b", source="mako")
    broker.emit("verifier", terms_total=250, terms_rejected=4)
    state = broker.state(agents=[])
    assert len(state["framings"]) == 2
    assert state["verifier"]["terms_total"] == 250
    broker.emit("reset")
    assert broker.state(agents=[])["framings"] == []


def test_broker_scene_change_clears_the_previous_scene():
    # A card from the framing scene must not still be on screen during the
    # audience scene — the dashboard renders straight from /state on refresh.
    broker = EventBroker()
    broker.emit("scene", scene="framing", idx=5, total=9, title_he="א", subtitle_he="")
    broker.emit("framing", article_id="a", source="ynet")
    broker.emit("event_map", event_id="e", semantic_found=2, keyword_found=0)
    broker.emit("scene", scene="audience", idx=6, total=9, title_he="ב", subtitle_he="")
    state = broker.state(agents=[])
    assert state["framings"] == [] and state["event_map"] is None
    assert state["scene"]["scene"] == "audience"


def test_broker_keeps_cross_scene_payloads():
    # The profile and economy payloads are built up across the closing scenes
    # and must survive the scene switch between them.
    broker = EventBroker()
    broker.emit("profile", events_total=69)
    broker.emit("scene", scene="economy", idx=8, total=9, title_he="", subtitle_he="")
    assert broker.state(agents=[])["profile"]["events_total"] == 69


def test_broker_state_tracks_gate_and_arch_steps():
    broker = EventBroker()
    broker.emit("scene", scene="arch", idx=1, total=9, title_he="א", subtitle_he="")
    broker.emit("arch_step", step="crawl", idx=0, status="active")
    broker.emit("arch_step", step="crawl", idx=0, status="done")
    broker.emit("gate", gate_id="s1-arch", hint_he="המשך", autoplay_ms=None)
    state = broker.state(agents=[])
    assert state["gate"]["gate_id"] == "s1-arch"
    assert len(state["arch_steps"]) == 1  # same step updated, not appended
    broker.emit("gate_cleared", gate_id="s1-arch")
    assert broker.state(agents=[])["gate"] is None


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


def test_source_labels_fall_back_to_the_raw_id():
    assert source_he("haaretz") == "הארץ"
    assert source_he("unknown_site") == "unknown_site"


def test_scout_exhausts_the_tree_before_giving_up(monkeypatch):
    # The theatrical sleeps are what the presenter narrates over; in a test
    # they are just wall time.
    monkeypatch.setattr(config, "DEMO_SPEED", 0.0)

    async def scenario():
        scout = Scout()
        article = {"title": "כותרת", "url": "http://x"}
        assert await scout.fetch(article, "broken_rss", quick=True) is True
        assert await scout.fetch(article, "broken_skip", quick=True) is False

    asyncio.run(scenario())


def test_every_scout_scenario_ends_in_a_terminal_state():
    # A scenario whose last step is still "trying" would leave the tracker
    # spinning on screen forever.
    for steps in Scout.STEPS.values():
        assert steps[-1][1] in ("success", "skipped")
