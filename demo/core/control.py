"""HITL pacing controller: the runner awaits a gate between scenes, and the
presenter advances it with a click/keypress (POST /control/advance).

Two modes:
- DEMO_AUTOPLAY=0 — the demo waits at every gate until advance() is called
  (presenter-controlled show; run_demo.sh default).
- DEMO_AUTOPLAY=1 — every gate also auto-clears after AUTOPLAY_GATE_S
  (scaled by DEMO_SPEED), so an unattended kiosk loop / CI benchmark never
  stalls. advance() still works and skips the wait.

The same keypress also works *inside* a scene. Gates sit between scenes, but a
scene is itself a sequence of timed steps — the architecture scene alone holds
~50 seconds of deliberate pauses — and a presenter who has finished talking
about the step on screen had no way to move on. So every theatrical pause in
the demo goes through `sleep()` here, and an advance with no gate open cuts the
current pause short instead of doing nothing.
"""

from __future__ import annotations

import asyncio

from demo import config
from demo.core.events import BROKER


class DemoController:
    def __init__(self) -> None:
        self.autoplay = config.DEMO_AUTOPLAY
        self._event: asyncio.Event = asyncio.Event()
        self.current_gate: str | None = None
        # Mid-scene skips are counted, not flagged: three taps during one long
        # pause mean three steps on, and a tap that lands in the gap between
        # two pauses has to survive until the next one starts rather than
        # being cleared unnoticed.
        self._skips = 0
        self._skip_event: asyncio.Event = asyncio.Event()

    def advance(self) -> bool:
        """Called from the /control/advance endpoint.

        Returns True if a gate was actually open. False means the demo was
        mid-scene — which is no longer a no-op: it banks a skip that shortens
        the current (or next) pause. The two are still reported separately,
        because "the scene moved on" and "a pause got cut" are different
        things to see in a log.
        """
        if self.current_gate is not None:
            self._event.set()
            return True
        self._skips += 1
        self._skip_event.set()
        return False

    async def sleep(self, seconds: float) -> None:
        """A theatrical pause the presenter can cut short.

        Every pause in the demo goes through here (demo.core.agent.nap), so
        one skip advances exactly one step — the pacing stays authored, and
        the presenter only chooses when to leave each step.
        """
        if self._take_skip():
            return
        try:
            await asyncio.wait_for(self._skip_event.wait(), seconds)
        except asyncio.TimeoutError:
            return
        self._take_skip()

    def _take_skip(self) -> bool:
        if self._skips <= 0:
            return False
        self._skips -= 1
        if self._skips == 0:
            self._skip_event.clear()
        return True

    async def gate(self, gate_id: str, hint_he: str = "") -> None:
        """Pause here until the presenter advances (or autoplay times out)."""
        # A tap aimed at the last step of a scene must not silently skip the
        # first step of the next one: banked skips do not cross a gate.
        self._skips = 0
        self._skip_event.clear()
        self._event = asyncio.Event()
        self.current_gate = gate_id
        timeout_s = (config.AUTOPLAY_GATE_S * config.DEMO_SPEED
                     if self.autoplay else None)
        BROKER.emit("gate", gate_id=gate_id, hint_he=hint_he,
                    autoplay_ms=int(timeout_s * 1000) if timeout_s else None)
        try:
            if timeout_s is not None:
                try:
                    await asyncio.wait_for(self._event.wait(), timeout_s)
                except asyncio.TimeoutError:
                    pass
            else:
                await self._event.wait()
        finally:
            self.current_gate = None
            BROKER.emit("gate_cleared", gate_id=gate_id)


CONTROLLER = DemoController()
