"""HITL pacing controller: the runner awaits a gate between scenes, and the
presenter advances it with a click/keypress (POST /control/advance).

Two modes:
- DEMO_AUTOPLAY=0 — the demo waits at every gate until advance() is called
  (presenter-controlled show; run_demo.sh default).
- DEMO_AUTOPLAY=1 — every gate also auto-clears after AUTOPLAY_GATE_S
  (scaled by DEMO_SPEED), so an unattended kiosk loop / CI benchmark never
  stalls. advance() still works and skips the wait.
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

    def advance(self) -> bool:
        """Called from the /control/advance endpoint. Returns True if a gate
        was actually open (False = nothing to advance, e.g. mid-scene)."""
        if self.current_gate is None:
            return False
        self._event.set()
        return True

    async def gate(self, gate_id: str, hint_he: str = "") -> None:
        """Pause here until the presenter advances (or autoplay times out)."""
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
