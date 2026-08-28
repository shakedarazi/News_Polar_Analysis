"""Event broker: agents emit typed events → SSE subscribers + /state snapshot.

The schema is defined in demo/EVENTS.md — keep both in sync.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from typing import Any


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[str]] = []
        self._feed: deque[dict[str, Any]] = deque(maxlen=50)
        self._metrics: list[dict[str, Any]] = []
        self._phase: dict[str, Any] | None = None
        self._agent_states: dict[str, dict[str, Any]] = {}
        # Latest per-scene payloads, kept so a page refresh mid-scene can
        # recover the current view from /state (kiosk resilience).
        self._scene: dict[str, Any] | None = None
        self._gate: dict[str, Any] | None = None
        self._arch_steps: list[dict[str, Any]] = []
        self._showcase: dict[str, Any] | None = None
        self._retrieval: dict[str, Any] | None = None
        self._economy: dict[str, Any] | None = None
        self._learned: list[dict[str, Any]] = []
        self._llm_mode: dict[str, Any] | None = None
        self.total_tokens = 0
        self.total_cost_usd = 0.0
        self.llm_calls = 0

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
        elif type_ == "metric":
            self._metrics.append(event)
        elif type_ == "phase":
            self._phase = event
        elif type_ == "agent_status":
            self._agent_states[event.get("agent", "?")] = event
        elif type_ == "scene":
            self._scene = event
            # scene-scoped payloads don't leak into the next scene
            self._arch_steps = []
            self._showcase = None
            self._retrieval = None
        elif type_ == "gate":
            self._gate = event
        elif type_ == "gate_cleared":
            self._gate = None
        elif type_ == "arch_step":
            self._arch_steps = [s for s in self._arch_steps
                                if s.get("step") != event.get("step")]
            self._arch_steps.append(event)
        elif type_ == "showcase":
            self._showcase = event
        elif type_ == "retrieval":
            self._retrieval = event
        elif type_ == "economy":
            self._economy = event
        elif type_ == "learn":
            self._learned.append(event)
        elif type_ == "llm_mode":
            self._llm_mode = event
        elif type_ == "reset":
            self._metrics = []
            self._feed.clear()
            self._phase = None
            self._agent_states = {}
            self._scene = None
            self._gate = None
            self._arch_steps = []
            self._showcase = None
            self._retrieval = None
            self._economy = None
            self._learned = []
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
            "metrics": self._metrics,
            "feed": list(self._feed),
            "scene": self._scene,
            "gate": self._gate,
            "arch_steps": self._arch_steps,
            "showcase": self._showcase,
            "retrieval": self._retrieval,
            "economy": self._economy,
            "learned": self._learned[-10:],
            "llm_mode": self._llm_mode,
            "tokens": {
                "total_tokens": self.total_tokens,
                "total_cost_usd": round(self.total_cost_usd, 6),
            },
        }


BROKER = EventBroker()
