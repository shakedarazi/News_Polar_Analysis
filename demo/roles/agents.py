"""The five demo agents. Personalities live in the Hebrew reasoning strings.

Honesty ledger (also in demo/README.md):
- Scout "fetches" from the local snapshot with pre-scripted failure scenarios —
  no live network scraping at showtime. The fallback decision tree itself runs
  for real (it just gets deterministic outcomes).
- Librarian's retrieval is NOT replayed: the cosine query runs live at showtime
  against the real index, and the keyword baseline it is compared to is
  computed live too. This is the one place the AI is load-bearing, so it is
  also the one place nothing is precomputed.
- Nova replays framing that a real model produced once at prepare time. The
  output is real; the call is not live, because a kiosk must not depend on the
  network. Nothing else about it is simulated.
- Amit is not a second model opinion. He is deterministic string grounding,
  re-run live against the same text the extractor was given, and he is the only
  agent whose verdict removes something from the screen.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import numpy as np

from demo import config
from demo.core import store
from demo.core.agent import Agent, nap
from demo.core.events import BROKER
from demo.core.framing import (keyword_jaccard, verify_contrast,
                               verify_framing)
from demo.core.index import VectorIndex

SOURCE_LABELS_HE = {"ynet": "ynet", "mako": "mako", "haaretz": "הארץ",
                    "news12": "חדשות 12", "channel14": "ערוץ 14",
                    "reshet13": "רשת 13"}


def source_he(source: str) -> str:
    return SOURCE_LABELS_HE.get(source, source)


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

    async def fetch(self, article: dict[str, Any], scenario: str,
                    quick: bool = False) -> bool:
        title = article["title"]
        self.status("working", f"מושך: {title[:40]}…")
        steps = self.STEPS[scenario]
        if scenario != "ok" and not quick:
            self.say(f"קישור בעייתי — מפעיל עץ החלטות ({len(steps)} שלבים)", "warn")
        pace = 0.15 if quick else 1.0
        ok = False
        for i, (strategy, status, note) in enumerate(steps):
            BROKER.emit("scrape_step", url=article["url"],
                        article_title=title, step_idx=i, strategy=strategy,
                        status="trying", note_he="")
            await nap((2.6 if scenario != "ok" else 1.6) * pace)
            BROKER.emit("scrape_step", url=article["url"],
                        article_title=title, step_idx=i, strategy=strategy,
                        status=status, note_he=note)
            ok = status == "success"
        if ok and scenario != "ok":
            self.say("שוחזר בהצלחה — אף כתבה לא הולכת לאיבוד", "decision")
        elif not ok:
            self.say(f"ויתרתי על {title[:30]}… אחרי מיצוי כל המסלולים", "warn")
        self.status("idle")
        return ok


class Lexi(Agent):
    id = "lexi"

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self.conn = conn

    async def analyze(self, article: dict[str, Any],
                      verbose: bool = True) -> dict[str, Any]:
        """verbose=False — quiet quick pass, so only one focus point talks."""
        self.status("working", f"מריץ לקסיקון: {article['title'][:35]}…")
        await nap(3.5 if verbose else 1.3)
        counts = store.lexicon_counts(self.conn, article["article_id"])
        stats = store.polarity_stats(self.conn, article["article_id"])
        top_i = int(np.argmax(counts)) if any(counts) else None
        result = {"counts": counts, "stats": stats,
                  "top_lexicon": (config.LEXICON_CATEGORY_NAMES_HE[top_i]
                                  if top_i is not None else None),
                  "top_i": top_i}
        dom = stats["mean_dominance"]
        if verbose:
            self.say(f"‏{stats['windows']} חלונות, דומיננטיות ממוצעת "
                     f"{dom:.2f}" if dom is not None else "אין מילות לקסיקון בכתבה")
            if top_i is not None and counts[top_i] >= 3:
                self.say(f"הלקסיקון (מחקר בן שמחון) מצביע חזק על "
                         f"{result['top_lexicon']} ({counts[top_i]} מופעים)",
                         "decision")
        self.status("idle")
        return result


class Librarian(Agent):
    id = "librarian"

    def __init__(self, index: VectorIndex) -> None:
        super().__init__()
        self.index = index

    async def map_event(self, seed: dict[str, Any], seed_vec: np.ndarray,
                        event: dict[str, Any]) -> None:
        """Find the other outlets' versions of one story, live.

        Both halves run here and now: the cosine query against the real index,
        and the keyword baseline it is measured against. The baseline is the
        whole point — in Hebrew, two outlets covering the same event share
        almost no headline words, so a word-matching search misses versions
        that are plainly the same story to any reader.
        """
        self.status("working", f"מחפשת את אותו סיפור: {seed['title'][:32]}…")
        self.say("שאלה אחת: מי עוד סיקר בדיוק את האירוע הזה?")
        await nap(6)

        wanted = {v["article_id"] for v in event["versions"]
                  if v["article_id"] != seed["article_id"]}
        neighbors = self.index.query(seed_vec, k=12)
        found = [n for n in neighbors if n["article_id"] in wanted]
        by_keyword = [n for n in neighbors
                      if n["article_id"] in wanted
                      and keyword_jaccard(seed["title"], n["title"]) >= 0.25]

        self.say(f"חיפוש מילולי על הכותרות מוצא {len(by_keyword)} מתוך "
                 f"{len(wanted)} — הכותרות פשוט לא חולקות מילים", "warn")
        await nap(7)
        self.say(f"אחזור סמנטי מוצא {len(found)} מתוך {len(wanted)}: "
                 + ", ".join(f"{source_he(n['source'])} ({n['score']:.2f})"
                             for n in found), "decision")
        BROKER.emit(
            "event_map", event_id=event["event_id"], seed_title=seed["title"],
            seed_source=seed["source"], topic_he=event["topic_he"],
            keyword_found=len(by_keyword), semantic_found=len(found),
            total=len(wanted),
            versions=[{"source": n["source"], "source_he": source_he(n["source"]),
                       "title": n["title"], "score": round(n["score"], 3),
                       "keyword_overlap": round(
                           keyword_jaccard(seed["title"], n["title"]), 3)}
                      for n in found],
        )
        self.send("nova", "data", f"{len(found)} גרסאות של אותו אירוע")
        self.status("idle")


class Nova(Agent):
    id = "nova"

    async def frame(self, version: dict[str, Any]) -> None:
        """Emit the verified framing variables for one version."""
        framing = version.get("framing")
        if not framing:
            return
        self.status("working", f"מנתחת מסגור: {source_he(version['source'])}")
        await nap(3.5)
        BROKER.emit(
            "framing", article_id=version["article_id"],
            source=version["source"], source_he=source_he(version["source"]),
            title=version["title"], url=version["url"],
            actor=framing.get("actor"),
            responsibility=framing.get("responsibility"),
            voice=framing.get("voice"),
            lead_perspective=framing.get("lead_perspective"),
            loaded_terms=framing.get("loaded_terms") or [],
            lex_top_he=version["lex_top_he"],
        )
        self.status("idle")

    async def contrast(self, event: dict[str, Any]) -> None:
        """The retrieval-AUGMENTED step: what is unique about each version
        GIVEN the others. Unanswerable from a single article, which is exactly
        why the retrieval has to come first."""
        contrast = event.get("contrast")
        if not contrast:
            return
        self.status("working", "משווה את הגרסאות זו מול זו")
        self.say("עכשיו אני מקבלת את כל הגרסאות יחד — ושואלת מה ייחודי בכל אחת "
                 "ביחס לאחרות. את זה אי אפשר לענות מכתבה בודדת", "decision")
        await nap(7)
        BROKER.emit(
            "contrast", event_id=event["event_id"],
            shared_he=contrast.get("shared"),
            per_source=[{"source": i["source"],
                         "source_he": source_he(i["source"]),
                         "distinctive_he": i.get("distinctive"),
                         "evidence_he": i.get("evidence")}
                        for i in contrast.get("per_source") or []],
        )
        self.status("idle")


class Amit(Agent):
    id = "amit"

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self.conn = conn

    async def verify(self, event: dict[str, Any],
                     stats: dict[str, Any]) -> None:
        """Re-run the grounding check live, then report the rate over the
        whole snapshot — not just the story on screen."""
        self.status("working", "מאמת כל ביטוי מול הטקסט")
        self.say("אני לא דעה שנייה של מודל. אני בדיקה דטרמיניסטית: כל ביטוי "
                 "שנובה מחזירה חייב להימצא באותו טקסט שהיא קראה", "decision")
        await nap(7)

        checked, dropped = 0, []
        for version in event["versions"]:
            raw = version.get("framing_raw")
            if not raw:
                continue
            text = (store.get_article(self.conn, version["article_id"]) or {}).get("text", "")
            verdict = verify_framing(raw, version["title"], text)
            checked += len(verdict.kept_terms) + len(verdict.dropped_terms)
            dropped += [{"source_he": source_he(version["source"]), "term": t}
                        for t in verdict.dropped_terms]

        rejected_quotes = self._rejected_quotes(event)
        if rejected_quotes:
            self.say(f"פסלתי ציטוט: \"{rejected_quotes[0]['quote'][:50]}…\" — "
                     f"פרפרזה, לא ציטוט מהטקסט של "
                     f"{rejected_quotes[0]['source_he']}", "warn")
        BROKER.emit(
            "verifier", checked_terms=checked, dropped_terms=dropped,
            rejected_quotes=rejected_quotes,
            terms_total=stats["terms_total"], terms_rejected=stats["terms_rejected"],
            actors_total=stats["actors_total"],
            actors_rejected=stats["actors_rejected"],
            quotes_total=stats["quotes_total"],
            quotes_rejected=stats["quotes_rejected"],
            lead_chars=stats["lead_chars"],
        )
        await nap(6)
        self.say(f"על כל הסנאפשוט: {stats['terms_rejected']} מתוך "
                 f"{stats['terms_total']} ביטויים נפסלו, ו־{stats['quotes_rejected']} "
                 f"מתוך {stats['quotes_total']} ציטוטים. מה שנפסל לא עולה למסך",
                 "decision")
        self.status("idle")

    def _rejected_quotes(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        raw = event.get("contrast_raw")
        if not raw:
            return []
        versions = [(v["source"], v["title"],
                     (store.get_article(self.conn, v["article_id"]) or {}).get("text", ""))
                    for v in event["versions"]]
        kept, _ = verify_contrast(raw, versions)
        good = {(i["source"], i.get("evidence")) for i in kept["per_source"]}
        out = []
        for item in raw.get("per_source") or []:
            evidence = item.get("evidence")
            if evidence and (item["source"], evidence) not in good:
                out.append({"source_he": source_he(item["source"]),
                            "quote": evidence})
        return out
