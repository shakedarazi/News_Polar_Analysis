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
        self.total_tokens = 0
        self.total_cost_usd = 0.0

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
        elif type_ == "reset":
            self._metrics = []
            self._feed.clear()
            self._phase = None
            self._agent_states = {}
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
            "tokens": {
                "total_tokens": self.total_tokens,
                "total_cost_usd": round(self.total_cost_usd, 6),
            },
        }


BROKER = EventBroker()
