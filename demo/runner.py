"""The demo as a scene machine: nine focused scenes, with a HITL gate between
each so the presenter sets the pace.

    architecture → intake → lexicon core → event map → framing → audience
    → outlet profile → token economy → summary

Scenes 1–3 are the deterministic pipeline, before any AI. Scenes 4–6 follow ONE
story through the AI layer: which outlets covered it, how each framed it, and
what each outlet's readers did with it. Scene 7 zooms out to every event in the
snapshot. Everything on screen is either computed live here or replayed from
model output captured once at prepare time — never invented.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from demo import config
from demo.core import store
from demo.core.agent import nap
from demo.core.control import CONTROLLER
from demo.core.events import BROKER
from demo.core.index import VectorIndex
from demo.roles.agents import Amit, Lexi, Librarian, Nova, Scout, source_he


class DemoLoop:
    def __init__(self) -> None:
        demo_set = json.loads(config.DEMO_SET_PATH.read_text(encoding="utf-8"))
        self.showcases = demo_set["showcase_events"]
        self.profile = demo_set["profile"]
        self.verifier_stats = demo_set["verifier"]
        self.usage = demo_set.get("usage", {})
        self.conn = store.connect()
        self.index = VectorIndex.load()
        # Query vectors come straight out of the index: the embeddings were
        # computed offline at prepare time, so showtime loads no model at all
        # and the retrieval itself is a dot product.
        self.vec_by_id = {m["article_id"]: self.index.vectors[i]
                          for i, m in enumerate(self.index.meta)}
        self.loop_no = 0

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

    def _text(self, article_id: str) -> str:
        return (store.get_article(self.conn, article_id) or {}).get("text") or ""

    async def run_once(self) -> None:
        # One story per loop, rotating, so a kiosk running all day does not
        # replay the same three headlines every five minutes.
        event = self.showcases[self.loop_no % len(self.showcases)]
        self.loop_no += 1

        scout = Scout()
        lexi = Lexi(self.conn)
        librarian = Librarian(self.index)
        nova = Nova()
        amit = Amit(self.conn)
        for agent in (scout, lexi, librarian, nova, amit):
            agent.status("idle")
        BROKER.emit("llm_mode", mode="cached",
                    label_he="פלט מודל אמיתי, מוקלט מראש — הקיוסק לא תלוי רשת")

        self.links_recovered = 0
        self.dropped = 0

        await self._scene_arch()
        await self._scene_intake(scout, event)
        await self._scene_lexicon(lexi, event)
        await self._scene_event_map(librarian, event)
        await self._scene_framing(nova, amit, event)
        await self._scene_audience(event)
        await self._scene_profile()
        await self._scene_economy(amit)
        await self._scene_summary(event)

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

    async def _scene_intake(self, scout: Scout, event: dict[str, Any]) -> None:
        self._scene(1)
        BROKER.emit("phase", phase="intake", label_he="איסוף כתבות")
        scout.say("נחיל הסוכנים מתעורר — מושכים את המנה הבאה מהמקורות")
        await nap(4)
        batch = event["intake"]
        for article in batch:
            ok = await scout.fetch(article, article["scenario"])
            if ok and article["scenario"] != "ok":
                self.links_recovered += 1
            if not ok:
                self.dropped += 1
            await nap(1.5)
        scout.say(f"נאספו {len(batch) - self.dropped}/{len(batch)} כתבות מ־"
                  f"{len({a['source'] for a in batch})} מקורות. מה מהן קשור למה — "
                  "עוד לא יודעים", "decision")
        await self._gate(1, "אל הליבה הדטרמיניסטית — הלקסיקון")

    # ── scene 3: the lexicon core + how it looks in the product ──────────

    async def _scene_lexicon(self, lexi: Lexi, event: dict[str, Any]) -> None:
        self._scene(2)
        # Deep-dive the version with the strongest lexicon signal, then a quick
        # pass over the rest — one focus point, not seven.
        showcase = max(event["versions"], key=lambda v: sum(v["lex_counts"]))
        for version in event["versions"]:
            verbose = version is showcase
            result = await lexi.analyze(version, verbose=verbose)
            if verbose:
                self._emit_showcase(version, result)
                # The product-fields panel is the heart of the scene — leave it
                # on screen long enough to walk through every field.
                await nap(18)
        lexi.say("ספירה דטרמיניסטית, אפס קריאות למודל שפה — וזה כבר ממלא את "
                 "השדות שרואים באתר", "decision")
        await self._gate(2, "ומי עוד סיקר את הסיפור הזה? — אחזור סמנטי")

    def _emit_showcase(self, version: dict[str, Any],
                       lexi_res: dict[str, Any]) -> None:
        stats = lexi_res["stats"]
        audience = stats.get("audience") or {}
        BROKER.emit(
            "showcase",
            article_id=version["article_id"], title=version["title"],
            source=version["source"], source_he=source_he(version["source"]),
            url=version["url"],
            published_at=(version.get("first_seen_at") or "")[:10],
            excerpt=version["excerpt"],
            windows=stats["windows"], mean_dominance=stats["mean_dominance"],
            max_dominance=stats["max_dominance"], comments=stats["comments"],
            audience_mean=audience.get("audience_mean"),
            audience_p85=audience.get("audience_p85"),
            top_category_he=lexi_res["top_lexicon"],
            top_count=(lexi_res["counts"][lexi_res["top_i"]]
                       if lexi_res["top_i"] is not None else 0),
        )

    # ── scene 4: semantic retrieval finds the same story elsewhere ───────

    async def _scene_event_map(self, librarian: Librarian,
                               event: dict[str, Any]) -> None:
        self._scene(3)
        BROKER.emit("phase", phase="retrieve", label_he="אחזור סמנטי")
        seed = max(event["versions"], key=lambda v: v["num_comments"] or 0)
        vec = self.vec_by_id.get(seed["article_id"])
        if vec is not None:
            await librarian.map_event(seed, vec, event)
            await nap(12)
        # "exactly the same event" is what this step is FOR, not what it
        # achieves: the golden set puts precision at the live 0.90 cut at 66%.
        # The screen carries the measured number; the line stops claiming a
        # certainty the measurement does not support.
        librarian.say("מכאן ההשוואה רצה על אותו אירוע — וזה מה שמאפשר להשוות "
                      "מערכות בלי להשוות אילו סיפורים הן בחרו לסקר. כמה "
                      "מהחיבורים האלה באמת נכונים נמדד בנפרד, מול ערכת זהב",
                      "decision")
        await self._gate(3, "איך כל אחת מספרת את זה? — מסגור")

    # ── scene 5: framing extraction, then the verifier ───────────────────

    async def _scene_framing(self, nova: Nova, amit: Amit,
                             event: dict[str, Any]) -> None:
        self._scene(4)
        BROKER.emit("phase", phase="framing", label_he="חילוץ מסגור · אימות")
        nova.say("הלקסיקון סופר מילים. הוא לא יודע לומר מי מוצג כמבצע הפעולה "
                 "ולמי מיוחסת האחריות — את זה אני מחלצת", "decision")
        await nap(7)
        for version in event["versions"]:
            await nova.frame(version)
            await nap(6)
        await nova.contrast(event)
        await nap(14)
        await amit.verify(event, self.verifier_stats)
        await self._gate(4, "ומה הקוראים עשו מזה? — הקהל")

    # ── scene 6: the audience half of the same event ─────────────────────

    async def _scene_audience(self, event: dict[str, Any]) -> None:
        self._scene(5)
        BROKER.emit("phase", phase="audience", label_he="פערי קהל")
        for version in event["versions"]:
            BROKER.emit(
                "audience_gap", article_id=version["article_id"],
                source=version["source"], source_he=source_he(version["source"]),
                title=version["title"],
                mean_dominance=version["mean_dominance"],
                num_comments=version["num_comments"],
                audience_mean=version["audience_mean"],
                audience_p85=version["audience_p85"],
                article_topic_he=version["lex_top_he"],
                comment_topic_he=version["comment_top_he"],
                hijacked=version["audience_hijacked"],
                top_comment=version["top_comment"],
            )
            await nap(7)
        hijacked = [v for v in event["versions"] if v["audience_hijacked"]]
        if hijacked:
            BROKER.emit(
                "insight",
                question_he="על מה הקוראים בעצם דיברו?",
                text_he=(f"ב־{len(hijacked)} מתוך {len(event['versions'])} הגרסאות "
                         "הנושא שהקוראים דיברו עליו שונה מהנושא של הכתבה עצמה — "
                         f"{', '.join(source_he(v['source']) + ': ' + str(v['lex_top_he']) + ' → ' + str(v['comment_top_he']) for v in hijacked)}"),
                source_he="ספירת לקסיקון על טקסט התגובות, אותו מילון בדיוק",
            )
            await nap(10)
        await self._gate(5, "ומה זה אומר על הערוץ עצמו? — פרופיל")

    # ── scene 7: zoom out to every event in the snapshot ─────────────────

    async def _scene_profile(self) -> None:
        self._scene(6)
        BROKER.emit("phase", phase="profile", label_he="פרופיל מצטבר")
        profile = self.profile
        significant = [o for o in profile["outlets"] if o["significant"]]
        BROKER.emit(
            "profile",
            events_total=profile["events_total"],
            outlets=profile["outlets"],
            curve_source=profile["curve_source"],
            curve_source_he=source_he(profile["curve_source"]),
            sampling_curve=profile["sampling_curve"],
            topic_cells=profile["topic_cells"],
            change_scans=profile["change_scans"],
            power_table=profile["power_table"],
            coverage=profile["coverage"],
            min_cell_events=10,
        )
        await nap(16)
        BROKER.emit(
            "insight",
            question_he="מה אפשר כבר לומר, ומה עוד לא?",
            text_he=(
                f"על {profile['events_total']} אירועים משותפים: "
                + " · ".join(f"{source_he(o['source'])} {o['mean']:+.3f}"
                             for o in significant)
                + f". פילוח לפי תחום עדיין לא מובהק באף תא — "
                + f"{sum(1 for c in profile['topic_cells'] if c['usable'])} "
                + "תאים מגיעים לסף הגודל, ואף אחד מהם לא לרווח סמך שאינו חוצה אפס."),
            source_he="השוואה תוך־אירועית + רווחי סמך bootstrap — סטטיסטיקה, לא AI",
        )
        await nap(10)
        await self._gate(6, "וכמה כל זה עלה? — כלכלת טוקנים")

    # ── scene 8: token economy ───────────────────────────────────────────

    def _strawman(self) -> dict[str, Any]:
        """What this architecture would have cost as one model call per item.

        Read from explainer_facts.json, which measures it over every article
        AND every comment in the snapshot at their real character counts. The
        scene used to estimate it itself, at 900+150 tokens over the 752
        indexed articles — a self-consistent number that landed ~24x below the
        measured one and made the same argument the economy module makes, only
        much weaker. Two numbers for one quantity is the thing to avoid on a
        wall, so the scene now reads the module's.

        Falls back to the old estimate if the facts file is absent: the kiosk
        does not stop for a missing enrichment file.
        """
        try:
            facts = json.loads(
                (config.DATA_DIR / "explainer_facts.json").read_text(encoding="utf-8"))
            straw = facts["economy"]["strawman"]
            return {
                "corpus_articles": straw["articles"],
                "allllm_tokens_est": straw["prompt_tokens"] + straw["completion_tokens"],
                "allllm_cost_est": straw["usd"],
                "allllm_calls": straw["calls"],
                "note_he": (f"נמדד: כל כתבה וכל תגובה כקריאת מודל נפרדת — "
                            f"{straw['calls']:,} קריאות, פי {straw['ratio']:g} "
                            "מהחשבון שמשמאל"),
            }
        except (OSError, KeyError, ValueError):
            n_articles = len(self.index.meta)
            prompt, completion = n_articles * 900, n_articles * 150
            cost = (prompt * config.PRICE_PROMPT_PER_M
                    + completion * config.PRICE_COMPLETION_PER_M) / 1_000_000
            return {
                "corpus_articles": n_articles,
                "allllm_tokens_est": prompt + completion,
                "allllm_cost_est": round(cost, 4),
                "allllm_calls": n_articles,
                "note_he": "אומדן: אותן כתבות אילו כל שלב היה קריאת מודל על הטקסט המלא",
            }

    async def _scene_economy(self, amit: Amit) -> None:
        self._scene(7)
        usage = self.usage
        BROKER.emit(
            "economy",
            model_calls=usage.get("calls", 0),
            cached_outputs=usage.get("cached_outputs", 0),
            total_tokens=usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0),
            total_cost_usd=usage.get("usd", 0.0),
            showtime_calls=0,
            **self._strawman(),
        )
        await nap(8)
        amit.say(f"כל שכבת ה־AI של המערכת הזאת עלתה "
                 f"${usage.get('usd', 0):.4f} — {usage.get('calls', 0)} קריאות, "
                 "פעם אחת, אופליין. הריצה שעל המסך עלתה 0$", "decision")
        await nap(6)
        amit.say("הליבה הדטרמיניסטית עושה את רוב העבודה; המודל נכנס רק לשאלה "
                 "שאין לה תשובה דטרמיניסטית")
        await self._gate(7, "לסיכום")

    # ── scene 9: summary ─────────────────────────────────────────────────

    async def _scene_summary(self, event: dict[str, Any]) -> None:
        self._scene(8)
        profile = self.profile
        stats = self.verifier_stats
        BROKER.emit(
            "run_summary",
            headline_he=f"אותו אירוע, {len(event['versions'])} מערכות, "
                        f"{len(event['versions'])} מסגורים שונים",
            event_headline=event["headline"],
            topic_he=event["topic_he"],
            keyword_found=event["keyword_found"],
            keyword_total=event["keyword_total"],
            events_total=profile["events_total"],
            outlets=[{"source_he": source_he(o["source"]), "n": o["n"],
                      "mean": o["mean"], "significant": o["significant"]}
                     for o in profile["outlets"] if o["mean"] is not None],
            terms_total=stats["terms_total"], terms_rejected=stats["terms_rejected"],
            quotes_total=stats["quotes_total"], quotes_rejected=stats["quotes_rejected"],
            links_recovered=self.links_recovered, dropped=self.dropped,
            total_cost_usd=self.usage.get("usd", 0.0),
        )
        await self._gate(8, "ריצה חדשה — סיפור אחר")
