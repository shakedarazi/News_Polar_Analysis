"""Self-improvement memory: corrections and confirmations accumulated across
rounds within one demo loop. Feeds (a) few-shot examples into live-mode LLM
prompts and (b) the cumulative vector index. Reset at the start of every loop
so each audience sees the same arc."""

from __future__ import annotations

from typing import Any


class Learnings:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, title: str, wrong: str | None, right: str, note_he: str) -> None:
        self.items.append({"title": title, "wrong": wrong, "right": right,
                           "note_he": note_he})

    def few_shot_block(self, limit: int = 6) -> str:
        if not self.items:
            return ""
        lines = ["דוגמאות שנלמדו מסבבים קודמים:"]
        for it in self.items[-limit:]:
            lines.append(f'- "{it["title"][:60]}" → {it["right"]} ({it["note_he"]})')
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self.items)
