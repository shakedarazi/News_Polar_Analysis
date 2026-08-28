"""The five demo agents. Personalities live in the Hebrew reasoning strings.

Honesty ledger (also in demo/README.md):
- Scout "fetches" from the local snapshot with pre-scripted failure scenarios —
  no live network scraping at showtime. The fallback decision tree itself runs
  for real (it just gets deterministic outcomes).
- In offline mode, debate turns are TEMPLATED but grounded in real numbers
  (real neighbor votes, real lexicon counts). In live mode they are real LLM
  turns.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import numpy as np

from demo import config
from demo.core import store
from demo.core.agent import Agent, nap
from demo.core.classify import (LEXI_TO_NEWS, classify_baseline, classify_knn,
                                critic_verdict)
from demo.core.events import BROKER
from demo.core.index import Embedder, VectorIndex
from demo.core.llm import GATEWAY
from demo.core.memory import Learnings

class Scout(Agent):
    id = "scout"

    STEPS = {
        "ok": [("direct", "success", "נטען מהמקור")],
        "broken_archive": [
            ("direct", "failed", "‏404 — הכתובת השתנתה"),
            ("alt_selector", "failed", "מבנה הדף שונה, ה־selector לא מצא טקסט"),
            ("archive_org", "success", "נמצא עותק בארכיון האינטרנט"),
        ],
        "broken_rss": [
            ("direct", "failed", "פסק זמן — האתר לא מגיב"),
            ("alt_selector", "failed", "אין JSON-LD בדף"),
            ("archive_org", "failed", "אין עותק בארכיון"),
            ("rss", "success", "שוחזר מפריט ה־RSS"),
        ],
        "broken_skip": [
            ("direct", "failed", "‏404"),
            ("alt_selector", "failed", "הדף ריק"),
            ("archive_org", "failed", "אין עותק"),
            ("rss", "failed", "הפריט כבר לא בפיד"),
            ("skip", "skipped", "מתועד ומדולג — לא עוצרים את הנחיל"),
        ],
    }

    async def fetch(self, article: dict[str, Any], scenario: str) -> bool:
        title = article["title"]
        self.status("working", f"מושך: {title[:40]}…")
        steps = self.STEPS[scenario]
        if scenario != "ok":
            self.say(f"קישור בעייתי — מפעיל עץ החלטות ({len(steps)} שלבים)", "warn")
        ok = False
        for i, (strategy, status, note) in enumerate(steps):
            BROKER.emit("scrape_step", url=article["canonical_url"],
                        article_title=title, step_idx=i, strategy=strategy,
                        status="trying", note_he="")
            await nap(1.1 if scenario != "ok" else 0.5)
            BROKER.emit("scrape_step", url=article["canonical_url"],
                        article_title=title, step_idx=i, strategy=strategy,
                        status=status, note_he=note)
            ok = status == "success"
        if ok:
            self.send("nova", "data", f"כתבה נטענה: {title[:30]}…")
            if scenario != "ok":
                self.say("שוחזר בהצלחה — אף כתבה לא הולכת לאיבוד", "decision")
        else:
            self.say(f"ויתרתי על {title[:30]}… אחרי מיצוי כל המסלולים", "warn")
        self.status("idle")
        return ok


class Librarian(Agent):
    id = "librarian"

    def __init__(self, index: VectorIndex) -> None:
        super().__init__()
        self.index = index

    async def retrieve(self, title: str, vec: np.ndarray) -> list[dict[str, Any]]:
        self.status("working", f"מאחזרת הקשר: {title[:35]}…")
        await nap(1.2)
        neighbors = self.index.query(vec, k=6)
        top = neighbors[0] if neighbors else None
        if top:
            self.say(f"נמצאו {len(neighbors)} מקבילות; הקרובה ביותר "
                     f"(דמיון {top['score']:.2f}): \"{top['title'][:40]}…\"")
            self.send("nova", "data", f"{len(neighbors)} שכנים סמנטיים")
        self.status("idle")
        return neighbors


class Lexi(Agent):
    id = "lexi"

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self.conn = conn

    async def analyze(self, article: dict[str, Any]) -> dict[str, Any]:
        self.status("working", f"מריץ לקסיקון: {article['title'][:35]}…")
        await nap(1.0)
        counts = store.lexicon_counts(self.conn, article["article_id"])
        stats = store.polarity_stats(self.conn, article["article_id"])
        top_i = int(np.argmax(counts)) if any(counts) else None
        result = {"counts": counts, "stats": stats,
                  "top_lexicon": (config.LEXICON_CATEGORY_NAMES_HE[top_i]
                                  if top_i is not None else None),
                  "top_i": top_i}
        dom = stats["mean_dominance"]
        self.say(f"‏{stats['windows']} חלונות, דומיננטיות ממוצעת "
                 f"{dom:.2f}" if dom is not None else "אין מילות לקסיקון בכתבה")
        if top_i is not None and counts[top_i] >= 3:
            self.say(f"הלקסיקון (מחקר בן שמחון) מצביע חזק על "
                     f"{result['top_lexicon']} ({counts[top_i]} מופעים)", "decision")
        self.status("idle")
        return result


class Nova(Agent):
    id = "nova"

    def __init__(self, index: VectorIndex, learnings: Learnings) -> None:
        super().__init__()
        self.index = index
        self.learnings = learnings

    async def classify(self, article: dict[str, Any], text: str, round_no: int,
                       vec: np.ndarray,
                       neighbors: list[dict[str, Any]]) -> dict[str, Any]:
        title = article["title"]
        self.status("working", f"מסווגת: {title[:35]}…")
        await nap(1.4)
        # Capability ladder, one rung per round: rules → retrieval-only →
        # retrieval + LLM + accumulated memory. (Keeps the improvement arc
        # honest in live mode too — the LLM only enters at round 3.)
        if round_no == 1:
            pred, conf, reason = classify_baseline(title, text)
            method = "baseline"
            self.say(f"בלי RAG יש לי רק חוקי אצבע: {reason} → {pred}")
        else:
            llm_answer = None
            if round_no >= 3:
                llm_answer = await self._try_llm(title, text, neighbors)
            if llm_answer is not None:
                pred, conf, method = llm_answer, 0.85, "llm"
                self.say(f"מודל שפה + הקשר מהספרנית + {len(self.learnings)} "
                         f"תיקונים בזיכרון → {pred}", "decision")
            else:
                pred, conf, neighbors = classify_knn(self.index, vec)
                method = "knn"
                votes = f"{conf:.0%} מהשכנים מסכימים"
                self.say(f"הצבעת שכנים סמנטיים: {pred} ({votes})", "decision")
        BROKER.emit(
            "classification", article_id=article["article_id"], title=title,
            predicted=pred, reference=article["reference"],
            correct=(pred == article["reference"]),
            confidence=round(conf, 2), method=method,
            neighbors=[{"title": n["title"], "category": n["category"],
                        "score": round(n["score"], 2)} for n in neighbors[:3]],
        )
        self.status("idle")
        return {"predicted": pred, "confidence": conf, "method": method,
                "neighbors": neighbors, "vec": vec}

    async def _try_llm(self, title: str, text: str,
                       neighbors: list[dict[str, Any]]) -> str | None:
        if not GATEWAY.available:
            return None
        context = "\n".join(f'- "{n["title"][:60]}" → {n["category"]}'
                            for n in neighbors[:5])
        few_shots = self.learnings.few_shot_block()
        user = (f"סווג את הכתבה לאחת מהקטגוריות: {', '.join(config.CATEGORIES_HE)}.\n"
                f"כתבות דומות מהמאגר:\n{context}\n{few_shots}\n"
                f"כותרת: {title}\nתחילת הכתבה: {text[:350]}\n"
                f"ענה במילה אחת בלבד — שם הקטגוריה.")
        answer = await GATEWAY.chat(
            "nova", "אתה מסווג חדשות בעברית. ענה במילה אחת.", user, max_tokens=10)
        if answer:
            answer = answer.strip().strip('."')
            if answer in config.CATEGORIES_HE:
                return answer
        return None


class Amit(Agent):
    id = "amit"

    def __init__(self, index: VectorIndex, learnings: Learnings) -> None:
        super().__init__()
        self.index = index
        self.learnings = learnings
        self._debate_seq = 0
        self._round_budget = 1

    def new_round(self, budget: int = 1) -> None:
        """One debate per round keeps the 5-minute pacing; the rest of the
        low-confidence cases get a spoken reservation instead of a full debate."""
        self._round_budget = budget

    async def debate(self, article: dict[str, Any], result: dict[str, Any],
                     lexi: dict[str, Any], reason_he: str,
                     final: str) -> dict[str, Any]:
        self._round_budget -= 1
        self._debate_seq += 1
        debate_id = f"d{self._debate_seq}"
        title = article["title"]
        for aid in ("amit", "nova"):
            BROKER.emit("agent_status", agent=aid, state="debating",
                        task_he=f"דיון: {title[:30]}…")
        BROKER.emit("debate_start", debate_id=debate_id,
                    article_id=article["article_id"], title=title,
                    participants=["nova", "amit"], reason_he=reason_he)
        self.send("nova", "challenge", "אני לא משוכנע")

        top_i = lexi.get("top_i")
        mapped = LEXI_TO_NEWS.get(top_i) if top_i is not None else None
        counts = lexi.get("counts") or [0] * 7
        pred = result["predicted"]
        nb = result["neighbors"][:2]

        turns = await self._llm_turns(title, pred, mapped, counts, top_i, nb, reason_he)
        if turns is None:
            # Offline: templated turns, but every number in them is real.
            nb_txt = (f'למשל "{nb[0]["title"][:35]}…" (דמיון {nb[0]["score"]:.2f})'
                      if nb else "אין לי שכנים חזקים")
            turns = [
                ("amit", f"נובה, סיווגת \"{title[:35]}…\" כ־{pred}, אבל {reason_he}."),
                ("nova", f"השכנים הסמנטיים תומכים בי — {nb_txt}."),
                ("amit", (f"הלקסיקון הדטרמיניסטי מצא {counts[top_i]} מופעי "
                          f"{mapped} — ראיה קשה, לא ניחוש.") if mapped else
                         "רמת הביטחון שלך פשוט לא מספיקה לפרסום."),
                ("nova", "מקבלת — עדיף לתקן עכשיו מאשר לטעות במאגר."),
            ]
        for agent_id, text in turns:
            await nap(2.2)
            BROKER.emit("debate_turn", debate_id=debate_id, agent=agent_id,
                        text_he=text)

        changed = final != pred
        verdict = (f"מאמצים את אות הלקסיקון: {final}" if changed
                   else f"הסיווג {pred} אושר, בהסתייגות")
        await nap(1.5)
        BROKER.emit("debate_end", debate_id=debate_id, verdict_he=verdict,
                    final_category=final, changed=changed)
        if changed:
            self.learnings.add(title, pred, final,
                               "תוקן בדיון מול אות הלקסיקון")
            BROKER.emit("learn", agent="nova",
                        text_he=f"נלמד: \"{title[:40]}…\" → {final}",
                        memory_size=len(self.learnings))
        for aid in ("amit", "nova"):
            BROKER.emit("agent_status", agent=aid, state="idle", task_he="")
        return {**result, "predicted": final, "confidence": max(result["confidence"], 0.7)}

    async def _llm_turns(self, title, pred, mapped, counts, top_i, nb, reason_he):
        if not GATEWAY.available:
            return None
        evidence = (f"לקסיקון: {counts[top_i]} מופעי {mapped}" if mapped
                    else "אין אות לקסיקון חזק")
        nb_txt = "; ".join(f'"{n["title"][:40]}"→{n["category"]}' for n in nb)
        user = (f'כתבה: "{title}". נובה סיווגה: {pred}. סיבת הערעור: {reason_he}. '
                f"ראיות: {evidence}. שכנים: {nb_txt}.\n"
                "כתוב דיון קצר של 4 תורות בין עמית (מבקר) לנובה (מסווגת), "
                "כל תורה משפט אחד בעברית. פורמט: כל שורה 'amit: ...' או 'nova: ...'")
        out = await GATEWAY.chat("amit", "אתה כותב דיון ענייני קצר בין שני סוכני AI.",
                                 user, max_tokens=260)
        if not out:
            return None
        turns = []
        for line in out.splitlines():
            line = line.strip()
            if line.lower().startswith(("amit:", "nova:")):
                aid, _, text = line.partition(":")
                turns.append((aid.strip().lower(), text.strip()))
        return turns[:4] if len(turns) >= 2 else None

    async def review(self, article: dict[str, Any], result: dict[str, Any],
                     lexi: dict[str, Any]) -> dict[str, Any]:
        final, reason = critic_verdict(result["predicted"], result["confidence"],
                                       lexi.get("counts") or [0] * 7)
        if reason and self._round_budget > 0:
            self.say(f"מערער על הסיווג: {reason}", "warn")
            return await self.debate(article, result, lexi, reason, final)
        if reason:
            # Debate budget for this round is spent — reservation only, so the
            # 5-minute pacing holds. Keeps Nova's answer (mirrored in prep sim).
            self.say(f"מסתייג ({reason}) אבל מאשר — נחזור לזה בסבב הבא", "warn")
            return result
        if result["confidence"] >= 0.75:
            self.say(f"מאשר את {result['predicted']} "
                     f"({result['confidence']:.0%} ביטחון)")
        return result
