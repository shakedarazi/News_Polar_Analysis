"""Event broker: agents emit typed events → SSE subscribers + /state snapshot.

The schema is defined in demo/EVENTS.md — keep both in sync.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from typing import Any

# Latest-payload state, kept so a page refresh mid-scene recovers the current
# view from /state (kiosk resilience). Scene-scoped keys are cleared whenever a
# new scene starts, so nothing from the previous scene lingers on screen.
SINGLE_PAYLOADS = {"showcase": "showcase", "event_map": "event_map",
                   "contrast": "contrast", "verifier": "verifier",
                   "profile": "profile", "economy": "economy"}
LIST_PAYLOADS = {"framing": "framings", "audience_gap": "audience"}
SCENE_SCOPED = ("showcase", "event_map", "framings", "contrast", "verifier",
                "audience")


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[str]] = []
        self._feed: deque[dict[str, Any]] = deque(maxlen=50)
        self._phase: dict[str, Any] | None = None
        self._agent_states: dict[str, dict[str, Any]] = {}
        self._scene: dict[str, Any] | None = None
        self._gate: dict[str, Any] | None = None
        self._arch_steps: list[dict[str, Any]] = []
        self._llm_mode: dict[str, Any] | None = None
        self._payloads: dict[str, Any] = {}

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    def emit(self, type_: str, **fields: Any) -> None:
        event = {"type": type_, "ts": int(time.time() * 1000), **fields}
        if type_ == "reasoning":
            self._feed.append(event)
        elif type_ == "phase":
            self._phase = event
        elif type_ == "agent_status":
            self._agent_states[event.get("agent", "?")] = event
        elif type_ == "scene":
            self._scene = event
            self._arch_steps = []
            for key in SCENE_SCOPED:
                self._payloads.pop(key, None)
        elif type_ == "gate":
            self._gate = event
        elif type_ == "gate_cleared":
            self._gate = None
        elif type_ == "arch_step":
            self._arch_steps = [s for s in self._arch_steps
                                if s.get("step") != event.get("step")]
            self._arch_steps.append(event)
        elif type_ == "llm_mode":
            self._llm_mode = event
        elif type_ in SINGLE_PAYLOADS:
            self._payloads[SINGLE_PAYLOADS[type_]] = event
        elif type_ in LIST_PAYLOADS:
            self._payloads.setdefault(LIST_PAYLOADS[type_], []).append(event)
        elif type_ == "reset":
            self._feed.clear()
            self._phase = None
            self._agent_states = {}
            self._scene = None
            self._gate = None
            self._arch_steps = []
            self._payloads = {}
        payload = json.dumps(event, ensure_ascii=False)
        for q in list(self._subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                # Slow consumer (e.g. background tab) — drop it; the dashboard
                # recovers via /state on reconnect.
                self.unsubscribe(q)

    def state(self, agents: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "agents": agents,
            "phase": self._phase,
            "agent_states": self._agent_states,
            "feed": list(self._feed),
            "scene": self._scene,
            "gate": self._gate,
            "arch_steps": self._arch_steps,
            "showcase": self._payloads.get("showcase"),
            "event_map": self._payloads.get("event_map"),
            "framings": self._payloads.get("framings", []),
            "contrast": self._payloads.get("contrast"),
            "verifier": self._payloads.get("verifier"),
            "audience": self._payloads.get("audience", []),
            "profile": self._payloads.get("profile"),
            "economy": self._payloads.get("economy"),
            "llm_mode": self._llm_mode,
        }


BROKER = EventBroker()
