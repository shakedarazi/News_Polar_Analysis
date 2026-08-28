"""The 5-minute demo loop: three rounds of the agent swarm processing a fixed
demo set, with a visible improvement arc, then a summary — forever."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from demo import config
from demo.core import store
from demo.core.agent import nap
from demo.core.events import BROKER
from demo.core.index import Embedder, VectorIndex
from demo.core.memory import Learnings
from demo.roles.agents import Amit, Lexi, Librarian, Nova, Scout


class DemoLoop:
    def __init__(self) -> None:
        self.demo_set = json.loads(config.DEMO_SET_PATH.read_text(encoding="utf-8"))
        self.conn = store.connect()
        self.index = VectorIndex.load()
        # Pre-embed every demo article once at startup (model is loaded anyway) —
        # retrieval at showtime is then pure math, nothing heavy mid-demo.
        all_articles = [a for r in self.demo_set["rounds"] for a in r["articles"]]
        texts = {}
        for a in all_articles:
            row = store.get_article(self.conn, a["article_id"])
            texts[a["article_id"]] = row["text"] if row else ""
        self.texts = texts
        vecs = Embedder.embed_passages(
            [f"{a['title']}. {texts[a['article_id']][:400]}" for a in all_articles])
        self.vecs = {a["article_id"]: v for a, v in zip(all_articles, vecs)}

    async def run_forever(self) -> None:
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # kiosk rule: never die, reset and go again
                BROKER.emit("reasoning", agent="amit", level="warn",
                            text_he=f"תקלה בלולאה — מתאפסים ({type(exc).__name__})")
                await nap(3)
            BROKER.emit("reset")
            await nap(6)

    async def run_once(self) -> None:
        learnings = Learnings()
        self.index.reset_to_base()
        scout = Scout()
        librarian = Librarian(self.index)
        lexi = Lexi(self.conn)
        nova = Nova(self.index, learnings)
        amit = Amit(self.index, learnings)

        for a in (scout, librarian, lexi, nova, amit):
            a.status("idle")
        scout.say("נחיל הסוכנים מתעורר — מתחילים סבב עיבוד חדש")
        await nap(3)

        metrics: list[dict[str, Any]] = []
        links_recovered = 0
        debates = 0

        for round_spec in self.demo_set["rounds"]:
            round_no = round_spec["round"]
            label = round_spec["label_he"]
            t0 = time.monotonic()
            amit.new_round(budget=1)
            round_results: list[dict[str, Any]] = []
            lexi_results: list[dict[str, Any]] = []

            BROKER.emit("phase", phase="intake", label_he="איסוף כתבות",
                        round=round_no, total_rounds=config.TOTAL_ROUNDS,
                        round_label_he=f"סבב {round_no} — {label}")
            fetched: list[dict[str, Any]] = []
            for art in round_spec["articles"]:
                ok = await scout.fetch(art, art["scenario"])
                if ok:
                    fetched.append(art)
                    if art["scenario"] != "ok":
                        links_recovered += 1
                await nap(0.4)

            BROKER.emit("phase", phase="classify", label_he="אחזור · סיווג · ניתוח",
                        round=round_no, total_rounds=config.TOTAL_ROUNDS,
                        round_label_he=f"סבב {round_no} — {label}")
            if round_no == 1:
                nova.say("בסבב הזה אני עובדת עיוורת — בלי מאגר ובלי הקשר", "warn")
            elif round_no == 2:
                librarian.say("מהסבב הזה אני בתמונה: כל כתבה מקבלת הקשר מהמאגר",
                              "decision")
            else:
                nova.say(f"יש לי כבר {len(learnings)} תיקונים בזיכרון + "
                         "מאגר שגדל מהסבבים הקודמים", "decision")

            for art in fetched:
                vec = self.vecs[art["article_id"]]
                text = self.texts[art["article_id"]]
                neighbors = []
                if round_no >= 2:
                    nova.send("librarian", "request", "צריכה הקשר")
                    neighbors = await librarian.retrieve(art["title"], vec)
                result = await nova.classify(art, text, round_no, vec, neighbors)
                nova.send("lexi", "request", "מה אומר הלקסיקון?")
                lexi_res = await lexi.analyze(art)
                lexi_results.append(lexi_res)
                lexi.send("amit", "data", "ממצאי לקסיקון")
                result = await amit.review(art, result, lexi_res)
                debates = amit._debate_seq
                # Cumulative RAG: confident final labels join the index
                if result["confidence"] >= 0.5:
                    self.index.add(vec, {"article_id": art["article_id"],
                                         "title": art["title"],
                                         "category": result["predicted"],
                                         "source": art["source"]})
                round_results.append({**result, "reference": art["reference"]})
                await nap(0.5)

            BROKER.emit("phase", phase="learn", label_he="למידה ומדידה",
                        round=round_no, total_rounds=config.TOTAL_ROUNDS,
                        round_label_he=f"סבב {round_no} — {label}")
            n = len(round_results)
            correct = sum(1 for r in round_results
                          if r["predicted"] == r["reference"])
            accuracy = correct / max(n, 1)
            metric = {"round": round_no, "label_he": label,
                      "accuracy": round(accuracy, 3), "n": n,
                      "learned": len(learnings),
                      "duration_s": round(time.monotonic() - t0, 1)}
            metrics.append(metric)
            BROKER.emit("metric", **metric)
            amit.say(f"דיוק הסבב: {accuracy:.0%} ({correct}/{n})", "decision")
            if round_no >= 2:
                grown = len(self.index.meta) - self.index.base_size
                librarian.say(f"המאגר גדל ב־{grown} כתבות מאומתות — "
                              "הסבב הבא יידע יותר")
            await nap(2)
            await self._insight(round_results, lexi_results)
            await nap(3)

        first, last = metrics[0]["accuracy"], metrics[-1]["accuracy"]
        BROKER.emit(
            "run_summary", rounds=metrics,
            total_articles=sum(m["n"] for m in metrics),
            debates=debates, links_recovered=links_recovered,
            total_cost_usd=round(BROKER.total_cost_usd, 4),
            headline_he=f"הדיוק עלה מ־{first:.0%} ל־{last:.0%} בשלושה סבבים",
        )
        await nap(14)

    async def _insight(self, results: list[dict[str, Any]],
                       lexi_results: list[dict[str, Any]]) -> None:
        totals = [0] * 7
        doms = []
        for lr in lexi_results:
            for i, c in enumerate(lr["counts"]):
                totals[i] += c
            if lr["stats"]["mean_dominance"] is not None:
                doms.append(lr["stats"]["mean_dominance"])
        if not any(totals):
            return
        top_i = max(range(7), key=lambda i: totals[i])
        top_name = config.LEXICON_CATEGORY_NAMES_HE[top_i]
        mean_dom = sum(doms) / len(doms) if doms else 0.0
        text = (f"מוקד הקיטוב בסבב: {top_name} — {totals[top_i]} מופעים לקסיקליים, "
                f"דומיננטיות ממוצעת {mean_dom:.2f}")
        BROKER.emit("insight",
                    question_he="מה מוקד הקיטוב בסבב הזה?",
                    text_he=text,
                    source_he="מחושב מנתוני הלקסיקון בלבד (מחקר בן שמחון)")
