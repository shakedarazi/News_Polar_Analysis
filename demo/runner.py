"""The demo as a scene machine: eight focused scenes (architecture → intake →
lexicon core → RAG → three classification rounds → learning → token economy →
summary), with a HITL gate between scenes so the presenter sets the pace.

The classification sequence inside the rounds is byte-for-byte the same logic
that snapshot/prepare_demo.py simulates when it calibrates the accuracy arc —
scene wrapping must never change it.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from demo import config
from demo.core import store
from demo.core.agent import nap
from demo.core.control import CONTROLLER
from demo.core.events import BROKER
from demo.core.index import Embedder, VectorIndex
from demo.core.llm import GATEWAY
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

    def _scene(self, idx: int) -> dict[str, Any]:
        spec = config.SCENES[idx]
        BROKER.emit("scene", scene=spec["id"], idx=idx + 1,
                    total=len(config.SCENES), title_he=spec["title_he"],
                    subtitle_he=spec["subtitle_he"])
        return spec

    async def _gate(self, idx: int, hint_he: str) -> None:
        await CONTROLLER.gate(f"s{idx + 1}-{config.SCENES[idx]['id']}", hint_he)

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
        GATEWAY.emit_mode()

        self.metrics: list[dict[str, Any]] = []
        self.links_recovered = 0
        self.debates = 0

        await self._scene_arch()
        fetched_r1 = await self._scene_intake(scout)
        lexi_cache = await self._scene_lexicon(lexi, fetched_r1)
        await self._scene_rag(librarian, fetched_r1)
        await self._scene_rounds(scout, librarian, lexi, nova, amit,
                                 fetched_r1, lexi_cache, learnings)
        await self._scene_learning(librarian, nova, amit, learnings)
        await self._scene_economy(amit)
        await self._scene_summary()

    # ── scene 1: the deterministic pipeline, before any agent ────────────

    async def _scene_arch(self) -> None:
        self._scene(0)
        await nap(4)
        for i, step in enumerate(config.ARCH_STEPS):
            BROKER.emit("arch_step", step=step["step"], idx=i,
                        label_he=step["label_he"], detail_he=step["detail_he"],
                        status="active")
            await nap(9 if step["step"] == "agents" else 7)
            BROKER.emit("arch_step", step=step["step"], idx=i,
                        label_he=step["label_he"], detail_he=step["detail_he"],
                        status="done")
        await self._gate(0, "נכיר את הסוכנים — איסוף")

    # ── scene 2: intake, scout's decision tree at human pace ─────────────

    async def _scene_intake(self, scout: Scout) -> list[dict[str, Any]]:
        self._scene(1)
        round_spec = self.demo_set["rounds"][0]
        BROKER.emit("phase", phase="intake", label_he="איסוף כתבות",
                    round=1, total_rounds=config.TOTAL_ROUNDS,
                    round_label_he=f"סבב 1 — {round_spec['label_he']}")
        scout.say("נחיל הסוכנים מתעורר — מתחילים סבב עיבוד חדש")
        await nap(4)
        fetched: list[dict[str, Any]] = []
        for art in round_spec["articles"]:
            ok = await scout.fetch(art, art["scenario"])
            if ok:
                fetched.append(art)
                if art["scenario"] != "ok":
                    self.links_recovered += 1
            await nap(1.5)
        scout.say(f"נאספו {len(fetched)}/{len(round_spec['articles'])} כתבות — "
                  "מוכנות לניתוח", "decision")
        await self._gate(1, "אל הליבה הדטרמיניסטית — הלקסיקון")
        return fetched

    # ── scene 3: the lexicon core + how it looks in the product ──────────

    async def _scene_lexicon(self, lexi: Lexi,
                             fetched: list[dict[str, Any]]) -> dict[str, Any]:
        self._scene(2)
        cache: dict[str, dict[str, Any]] = {}
        # Deep-dive on the article with the strongest lexicon signal, then a
        # quick pass over the rest — one focus point, not eight.
        scored = [(sum(store.lexicon_counts(self.conn, a["article_id"])), a)
                  for a in fetched]
        showcase_art = max(scored, key=lambda p: p[0])[1] if scored else None
        for art in fetched:
            verbose = art is showcase_art
            cache[art["article_id"]] = await lexi.analyze(art, verbose=verbose)
            if verbose:
                self._emit_showcase(art, cache[art["article_id"]])
                # The product-fields panel is the heart of the scene — leave
                # it front and center long enough to walk through every field.
                await nap(18)
        lexi.say(f"נותחו {len(fetched)} כתבות — ספירה דטרמיניסטית, "
                 "אפס קריאות למודל שפה", "decision")
        await self._gate(2, "ומאיפה מגיע ההקשר? — אחזור")
        return cache

    def _emit_showcase(self, art: dict[str, Any], lexi_res: dict[str, Any]) -> None:
        """Real raw material + the exact fields the product shows, so the
        audience sees this is a real article filling the real site."""
        row = store.get_article(self.conn, art["article_id"]) or {}
        stats = lexi_res["stats"]
        audience = stats.get("audience") or {}
        BROKER.emit(
            "showcase",
            article_id=art["article_id"], title=art["title"],
            source=art["source"], url=art["canonical_url"],
            published_at=(row.get("first_seen_at") or "")[:10],
            excerpt=(row.get("text") or "")[:300],
            windows=stats["windows"],
            mean_dominance=stats["mean_dominance"],
            max_dominance=stats["max_dominance"],
            comments=stats["comments"],
            audience_mean=audience.get("audience_mean"),
            audience_p85=audience.get("audience_p85"),
            top_category_he=lexi_res["top_lexicon"],
            top_count=(lexi_res["counts"][lexi_res["top_i"]]
                       if lexi_res["top_i"] is not None else 0),
            reference=art["reference"],
        )

    # ── scene 4: RAG — precise context instead of the whole article ──────

    async def _scene_rag(self, librarian: Librarian,
                         fetched: list[dict[str, Any]]) -> None:
        self._scene(3)
        art = fetched[0] if fetched else None
        if art is None:
            await self._gate(3, "אל הסבבים")
            return
        librarian.say(f"במאגר {self.index.base_size:,} כתבות שכבר תויגו בעבר — "
                      "הן ישמשו תקדימים לכתבות החדשות")
        await nap(8)
        librarian.say("הרעיון: לא מנחשים על כתבה חדשה — בודקים איך תויגו "
                      "הכתבות הכי דומות לה, כמו שופט שמצטט פסיקה קודמת",
                      "decision")
        await nap(8)
        neighbors = await librarian.retrieve(art["title"], self.vecs[art["article_id"]])
        text = self.texts[art["article_id"]]
        # Rough token estimates for the on-screen comparison (Hebrew ≈ 3 chars
        # per token) — labeled as an estimate in the UI.
        full_est = len(text) // 3 + 250
        ctx_est = (len(art["title"]) + sum(len(n["title"][:60]) for n in neighbors[:5])) // 3 + 60
        BROKER.emit("retrieval", title=art["title"],
                    neighbors=[{"title": n["title"], "category": n["category"],
                                "score": round(n["score"], 2)}
                               for n in neighbors[:5]],
                    tokens_full_est=full_est, tokens_context_est=ctx_est,
                    note_he="אומדן טוקנים להמחשה — כותרת + שכנים במקום הכתבה המלאה")
        await nap(14)
        librarian.say("זה כל הרעיון: הקשר קטן ומדויק במקום להזרים את הכתבה "
                      "המלאה למודל — פחות טוקנים, פחות רעש", "decision")
        await self._gate(3, "אל שלושת הסבבים — הקשת עולה")

    # ── scene 5: the three rounds (the calibrated improvement arc) ───────

    async def _scene_rounds(self, scout: Scout, librarian: Librarian,
                            lexi: Lexi, nova: Nova, amit: Amit,
                            fetched_r1: list[dict[str, Any]],
                            lexi_cache: dict[str, dict[str, Any]],
                            learnings: Learnings) -> None:
        self._scene(4)
        for round_spec in self.demo_set["rounds"]:
            round_no = round_spec["round"]
            label = round_spec["label_he"]
            t0 = time.monotonic()
            amit.new_round(budget=1)
            round_results: list[dict[str, Any]] = []
            lexi_results: list[dict[str, Any]] = []

            if round_no == 1:
                fetched = fetched_r1
            else:
                BROKER.emit("phase", phase="intake", label_he="איסוף כתבות",
                            round=round_no, total_rounds=config.TOTAL_ROUNDS,
                            round_label_he=f"סבב {round_no} — {label}")
                fetched = []
                for art in round_spec["articles"]:
                    ok = await scout.fetch(art, art["scenario"], quick=True)
                    if ok:
                        fetched.append(art)
                        if art["scenario"] != "ok":
                            self.links_recovered += 1
                    await nap(0.4)

            BROKER.emit("phase", phase="classify", label_he="אחזור · סיווג · ביקורת",
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
                if round_no == 1 and art["article_id"] in lexi_cache:
                    lexi_res = lexi_cache[art["article_id"]]
                else:
                    nova.send("lexi", "request", "מה אומר הלקסיקון?")
                    lexi_res = await lexi.analyze(art, verbose=False)
                lexi_results.append(lexi_res)
                lexi.send("amit", "data", "ממצאי לקסיקון")
                result = await amit.review(art, result, lexi_res)
                self.debates = amit._debate_seq
                # Cumulative RAG: confident final labels join the index
                if result["confidence"] >= 0.5:
                    self.index.add(vec, {"article_id": art["article_id"],
                                         "title": art["title"],
                                         "category": result["predicted"],
                                         "source": art["source"]})
                round_results.append({**result, "reference": art["reference"]})
                # Breathing room: the classification card must finish its
                # on-screen life before the next one opens (presenter feedback:
                # slow and flowing — the presenter narrates over this).
                await nap(4.5)

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
            self.metrics.append(metric)
            BROKER.emit("metric", **metric)
            amit.say(f"דיוק הסבב: {accuracy:.0%} ({correct}/{n})", "decision")
            if round_no >= 2:
                grown = len(self.index.meta) - self.index.base_size
                librarian.say(f"המאגר גדל ב־{grown} כתבות מאומתות — "
                              "הסבב הבא יידע יותר")
            await nap(5)
            await self._insight(round_results, lexi_results)
            hint = ("אל סבב 2 — מדליקים את ה־RAG" if round_no == 1 else
                    "אל סבב 3 — מוסיפים זיכרון" if round_no == 2 else
                    "מה נלמד? — סצנת הלמידה")
            await self._gate(4, hint)

    # ── scene 6: what was learned ────────────────────────────────────────

    async def _scene_learning(self, librarian: Librarian, nova: Nova,
                              amit: Amit, learnings: Learnings) -> None:
        self._scene(5)
        first = self.metrics[0]["accuracy"] if self.metrics else 0
        last = self.metrics[-1]["accuracy"] if self.metrics else 0
        nova.say(f"בזיכרון שלי {len(learnings)} דוגמאות מתוקנות מהדיבייטים — "
                 "הן נשלפות בכל סיווג חדש", "decision")
        await nap(7)
        grown = len(self.index.meta) - self.index.base_size
        librarian.say(f"והאינדקס גדל ב־{grown} כתבות מאומתות בתוך הריצה הזו")
        await nap(7)
        amit.say(f"בלי לאמן אף מודל: {first:.0%} ← {last:.0%}. "
                 "זו למידה מהצטברות ראיות, לא backprop", "decision")
        await self._gate(5, "וכמה כל זה עלה? — כלכלת טוקנים")

    # ── scene 7: token economy ───────────────────────────────────────────

    async def _scene_economy(self, amit: Amit) -> None:
        self._scene(6)
        # Estimate the same 24 articles with every step as a full-text LLM
        # call (classification + lexicon judgement + critique) — the
        # "everything-LLM" strawman the architecture avoids. Estimate only.
        n_articles = sum(len(r["articles"]) for r in self.demo_set["rounds"])
        prompt_est = sum(len(t) // 3 + 250 for t in self.texts.values()) * 2
        completion_est = n_articles * 150 + 3 * 400
        allllm_cost = (prompt_est * config.PRICE_PROMPT_PER_M
                       + completion_est * config.PRICE_COMPLETION_PER_M) / 1_000_000
        BROKER.emit("economy",
                    total_tokens=BROKER.total_tokens,
                    total_cost_usd=round(BROKER.total_cost_usd, 6),
                    llm_calls=BROKER.llm_calls,
                    allllm_tokens_est=prompt_est + completion_est,
                    allllm_cost_est=round(allllm_cost, 4),
                    note_he="אומדן: אותן 24 כתבות אילו כל שלב היה קריאת LLM על הטקסט המלא")
        await nap(8)
        if BROKER.llm_calls == 0:
            amit.say("הריצה הזו עלתה 0$ — הליבה דטרמיניסטית, וה־LLM נכנס רק "
                     "כשבאמת צריך אותו", "decision")
        else:
            amit.say(f"{BROKER.llm_calls} קריאות מודל בלבד, "
                     f"‏${BROKER.total_cost_usd:.4f} — כי הדטרמיניסטי עשה את רוב העבודה",
                     "decision")
        await nap(5)
        amit.say("אותו בנצ'מרק רץ חינם ב־CI על כל שינוי — אם הקשת נשברת, הבנייה נכשלת")
        await self._gate(6, "לסיכום")

    # ── scene 8: summary ─────────────────────────────────────────────────

    async def _scene_summary(self) -> None:
        self._scene(7)
        first = self.metrics[0]["accuracy"] if self.metrics else 0
        last = self.metrics[-1]["accuracy"] if self.metrics else 0
        BROKER.emit(
            "run_summary", rounds=self.metrics,
            total_articles=sum(m["n"] for m in self.metrics),
            debates=self.debates, links_recovered=self.links_recovered,
            total_cost_usd=round(BROKER.total_cost_usd, 4),
            headline_he=f"הדיוק עלה מ־{first:.0%} ל־{last:.0%} בשלושה סבבים",
        )
        await self._gate(7, "ריצה חדשה מההתחלה")

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
