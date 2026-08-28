"""Base agent: identity + event-emitting helpers + theatrical pacing."""

from __future__ import annotations

import asyncio

from demo import config
from demo.core.events import BROKER


async def nap(seconds: float) -> None:
    """Demo pacing sleep, scaled by DEMO_SPEED (set 0.15 in dev)."""
    await asyncio.sleep(seconds * config.DEMO_SPEED)


class Agent:
    id: str = ""

    def __init__(self) -> None:
        info = next(a for a in config.AGENTS if a["id"] == self.id)
        self.name_he = info["name_he"]
        self.tier = info["tier"]

    def status(self, state: str, task_he: str = "") -> None:
        BROKER.emit("agent_status", agent=self.id, state=state, task_he=task_he)

    def say(self, text_he: str, level: str = "info") -> None:
        BROKER.emit("reasoning", agent=self.id, level=level, text_he=text_he)

    def send(self, to: str, kind: str, summary_he: str) -> None:
        BROKER.emit("message", **{"from": self.id}, to=to, kind=kind,
                    summary_he=summary_he)
