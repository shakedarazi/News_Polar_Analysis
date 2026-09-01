"""Unit tests for the demo agent layer's pure logic (no network, no data files)."""

import asyncio
import pathlib

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


def test_a_press_mid_scene_cuts_the_current_pause_short():
    """The gap the presenter actually hits: gates sit between scenes, but the
    architecture scene alone holds ~50s of pauses inside one gate."""

    async def scenario():
        ctrl = DemoController()
        ctrl.autoplay = False
        task = asyncio.create_task(ctrl.sleep(30))
        await asyncio.sleep(0)
        assert ctrl.advance() is False  # no gate — but not a no-op
        await asyncio.wait_for(task, timeout=1)

    asyncio.run(scenario())


def test_a_press_between_two_pauses_is_not_swallowed():
    """A tap that lands while the runner is emitting, rather than sleeping,
    has to shorten the next pause instead of disappearing."""

    async def scenario():
        ctrl = DemoController()
        ctrl.autoplay = False
        assert ctrl.advance() is False  # banked while nothing is sleeping
        await asyncio.wait_for(ctrl.sleep(30), timeout=1)

    asyncio.run(scenario())


def test_one_press_skips_one_step_and_three_skip_three():
    """Pacing stays authored: a skip buys the next step, not the rest of the
    scene, so the presenter chooses when to leave each one."""

    async def scenario():
        ctrl = DemoController()
        ctrl.autoplay = False
        for _ in range(3):
            ctrl.advance()
        for _ in range(3):
            await asyncio.wait_for(ctrl.sleep(30), timeout=1)
        # the fourth pause is a real pause again
        slow = asyncio.create_task(ctrl.sleep(30))
        await asyncio.sleep(0.05)
        assert not slow.done()
        slow.cancel()

    asyncio.run(scenario())


def test_a_banked_skip_does_not_cross_a_gate():
    """Otherwise a tap aimed at the last step of a scene silently eats the
    first step of the next one."""

    async def scenario():
        ctrl = DemoController()
        ctrl.autoplay = False
        assert ctrl.advance() is False  # banked mid-scene
        gate = asyncio.create_task(ctrl.gate("g1", ""))
        await asyncio.sleep(0)
        assert ctrl.advance() is True
        await asyncio.wait_for(gate, timeout=1)
        slow = asyncio.create_task(ctrl.sleep(30))
        await asyncio.sleep(0.05)
        assert not slow.done(), "the banked skip leaked past the gate"
        slow.cancel()

    asyncio.run(scenario())


def test_every_theatrical_pause_goes_through_the_controller():
    """One place to interrupt. A bare asyncio.sleep in a scene would be a
    stretch of the show the spacebar cannot reach."""
    import re

    for path in pathlib.Path("demo").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert not re.search(r"\basyncio\.sleep\(", source), (
            f"{path} sleeps directly instead of via nap()/CONTROLLER.sleep")


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
