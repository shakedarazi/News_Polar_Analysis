"""Cross-source event mapping and outlet framing profiles.

This is the analytical core of the "same event, different audiences" demo. It
reads only the local snapshot (never the live pipeline) and is deterministic
except for the optional LLM framing extraction, which is cached to disk.

Three layers, deliberately kept separate because they have very different
epistemic weight (see demo/README.md honesty ledger):

1. `build_event_clusters` — semantic retrieval. THIS is where the AI earns its
   place: headlines of the same event share almost no words in Hebrew, so
   keyword matching finds ~5% of the versions that embeddings find. Measured by
   `keyword_recall`, which is shown on screen next to the real headlines.
2. `outlet_deviation` / `bootstrap_ci` — plain statistics, no AI. Every outlet
   is compared to the MEDIAN OF THE SAME EVENT, which controls for what
   actually happened in the world; comparing raw outlet averages would only
   measure which stories each outlet chooses to cover.
3. `FramingExtractor` — LLM. Produces the media-research framing variables a
   lexicon cannot see (who is named as the actor, to whom responsibility is
   attributed, active/passive voice, loaded terms).
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from demo import config

# The 7 lexicon categories (c1..c7) — same order as config.LEXICON_CATEGORY_NAMES_HE.
LEX_CATEGORIES_HE = config.LEXICON_CATEGORY_NAMES_HE
HEBREW_TOKEN = re.compile(r"[֐-׿']+")

# Cluster membership threshold on cosine similarity between article embeddings.
# 0.88 keeps 80 cross-source events in the snapshot; at 0.92 only near-verbatim
# wire copies survive and the framing contrast disappears.
CLUSTER_SIM = 0.88
# Jaccard threshold for the keyword baseline we compare retrieval against.
KEYWORD_JACCARD = 0.25


@dataclass
class Version:
    """One outlet's version of a shared event."""

    article_id: str
    source: str
    title: str
    url: str
    first_seen_at: str | None
    windows: int
    mean_dominance: float | None
    lex_counts: list[int]
    num_comments: int | None
    audience_mean: float | None
    audience_p85: float | None
    comment_counts: list[int] = field(default_factory=lambda: [0] * 7)
    framing: dict[str, Any] | None = None

    @property
    def lex_top_he(self) -> str | None:
        return _top_category(self.lex_counts)

    @property
    def comment_top_he(self) -> str | None:
        return _top_category(self.comment_counts)

    @property
    def audience_hijacked(self) -> bool:
        """The readers' dominant lexicon topic differs from the article's."""
        a, c = self.lex_top_he, self.comment_top_he
        return bool(a and c and a != c)


@dataclass
class Event:
    """A story covered by more than one outlet."""

    event_id: str
    versions: list[Version]

    @property
    def sources(self) -> list[str]:
        seen: list[str] = []
        for v in self.versions:
            if v.source not in seen:
                seen.append(v.source)
        return seen

    @property
    def total_comments(self) -> int:
        return sum(v.num_comments or 0 for v in self.versions)

    @property
    def headline(self) -> str:
        return self.versions[0].title

    @property
    def first_seen_at(self) -> str:
        """Earliest sighting across versions — the event's position in time."""
        stamps = [v.first_seen_at for v in self.versions if v.first_seen_at]
        return min(stamps) if stamps else ""

    @property
    def topic_he(self) -> str | None:
        """The event's own topic, from the MEDIAN lexicon profile of its
        versions. Taking the median rather than any single version keeps the
        label independent of the outlet whose deviation we then measure."""
        profiles = []
        for version in self.versions:
            vec = np.asarray(version.lex_counts, dtype=float)
            if vec.sum() > 0:
                profiles.append(vec / vec.sum())
        if len(profiles) < 2:
            return None
        return LEX_CATEGORIES_HE[int(np.argmax(np.median(np.stack(profiles), axis=0)))]


def _top_category(counts: Iterable[int]) -> str | None:
    counts = list(counts)
    if not counts or sum(counts) == 0:
        return None
    return LEX_CATEGORIES_HE[int(np.argmax(counts))]


def _tokens(text: str | None) -> set[str]:
    return {t for t in HEBREW_TOKEN.findall(text or "") if len(t) >= 3}


def keyword_jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / max(len(ta | tb), 1)


class Snapshot:
    """Read-only accessor over the local SQLite snapshot + vector index."""

    def __init__(self, sqlite_path: Path | None = None) -> None:
        self.conn = sqlite3.connect(sqlite_path or config.SQLITE_PATH)
        self.conn.row_factory = sqlite3.Row
        meta = json.loads(config.INDEX_META_PATH.read_text(encoding="utf-8"))
        vectors = np.load(config.INDEX_PATH)["vectors"]
        self.vec_by_id = {m["article_id"]: vectors[i] for i, m in enumerate(meta)}
        self._lexicon: dict[str, int] | None = None

    # ---- raw reads -------------------------------------------------------
    def articles(self) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute(
            "select a.article_id, a.source, a.title, a.text, a.canonical_url,"
            " a.first_seen_at, a.primary_category,"
            " g.num_comments, g.audience_mean, g.audience_p85"
            " from articles a left join article_comments_agg g"
            " on g.article_id = a.article_id"
        )
        return {r["article_id"]: dict(r) for r in rows}

    def window_features(self) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute(
            "select article_id, count(*) nw, avg(dominance) dom,"
            " sum(c1) c1, sum(c2) c2, sum(c3) c3, sum(c4) c4,"
            " sum(c5) c5, sum(c6) c6, sum(c7) c7"
            " from windows_features group by article_id"
        )
        return {r["article_id"]: dict(r) for r in rows}

    def comment_texts(self, article_id: str) -> list[str]:
        rows = self.conn.execute(
            "select text from comments where article_id = ? order by like_count desc",
            (article_id,),
        )
        return [r["text"] or "" for r in rows]

    def top_comment(self, article_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "select text, like_count from comments where article_id = ?"
            " order by like_count desc limit 1",
            (article_id,),
        ).fetchone()
        return dict(row) if row else None

    # ---- lexicon ---------------------------------------------------------
    @property
    def lexicon(self) -> dict[str, int]:
        """The pipeline's expanded article lexicon: token -> category 1..7."""
        if self._lexicon is None:
            path = config.REPO_ROOT / "data/lexicon_expanded/lexicon_expanded.json"
            raw = json.loads(path.read_text(encoding="utf-8"))
            self._lexicon = {k: v for k, v in raw.items() if isinstance(v, int)}
        return self._lexicon

    def lexicon_profile(self, text: str) -> list[int]:
        """Count lexicon hits per category — the same dictionary lookup the
        pipeline uses on articles, applied here to comment text."""
        counts = [0] * 7
        for token in HEBREW_TOKEN.findall(text or ""):
            cat = self.lexicon.get(token)
            if cat is not None and 1 <= cat <= 7:
                counts[cat - 1] += 1
        return counts


def build_event_clusters(snap: Snapshot, min_sources: int = 2,
                         min_versions: int = 2) -> list[Event]:
    """Group articles into cross-source events by embedding similarity.

    Greedy single-pass clustering: deterministic, and at snapshot scale a full
    similarity matrix is cheaper than any index. Duplicate titles inside a
    cluster are dropped — a few articles appear under two ids.
    """
    articles = snap.articles()
    feats = snap.window_features()
    ids = [i for i in snap.vec_by_id if i in articles]
    matrix = np.stack([snap.vec_by_id[i] for i in ids])
    sim = matrix @ matrix.T
    np.fill_diagonal(sim, -9.0)

    events: list[Event] = []
    used: set[str] = set()
    for i, article_id in enumerate(ids):
        if article_id in used:
            continue
        members = [article_id]
        for j in np.argsort(-sim[i])[:8]:
            if sim[i][j] > CLUSTER_SIM and ids[j] not in used:
                members.append(ids[j])
        seen_titles: set[str] = set()
        deduped: list[str] = []
        for member in members:
            title = articles[member]["title"]
            if title in seen_titles:
                continue
            seen_titles.add(title)
            deduped.append(member)
        if len(deduped) < min_versions:
            continue
        if len({articles[m]["source"] for m in deduped}) < min_sources:
            continue
        used.update(deduped)
        events.append(Event(
            event_id=deduped[0],
            versions=[_to_version(articles[m], feats.get(m)) for m in deduped],
        ))
    return events


def _to_version(row: dict[str, Any], feat: dict[str, Any] | None) -> Version:
    counts = [int(feat[f"c{i}"] or 0) for i in range(1, 8)] if feat else [0] * 7
    return Version(
        article_id=row["article_id"],
        source=row["source"],
        title=row["title"],
        url=row["canonical_url"],
        first_seen_at=row["first_seen_at"],
        windows=int(feat["nw"]) if feat else 0,
        mean_dominance=float(feat["dom"]) if feat and feat["dom"] is not None else None,
        lex_counts=counts,
        num_comments=row["num_comments"],
        audience_mean=row["audience_mean"],
        audience_p85=row["audience_p85"],
    )


def attach_comment_profiles(snap: Snapshot, event: Event) -> None:
    """Fill in what each version's readers actually talked about."""
    for version in event.versions:
        texts = snap.comment_texts(version.article_id)
        if texts:
            version.comment_counts = snap.lexicon_profile(" ".join(texts))


def keyword_recall(snap: Snapshot, event: Event) -> tuple[int, int]:
    """How many of the event's other versions a keyword baseline would find.

    Returns (found_by_keyword, total_other_versions). This is the on-screen
    proof that semantic retrieval is load-bearing rather than decorative — the
    audience can read the headlines and see they share no words.
    """
    seed = event.versions[0]
    others = event.versions[1:]
    found = sum(1 for v in others
                if keyword_jaccard(seed.title, v.title) >= KEYWORD_JACCARD)
    return found, len(others)


# ---------------------------------------------------------------------------
# Outlet profiles — statistics, not AI.
# ---------------------------------------------------------------------------

def outlet_deviation(events: list[Event], metric: str) -> dict[str, list[float]]:
    """Each version's deviation from the median of ITS OWN event.

    Comparing outlets on raw averages measures story selection, not framing;
    subtracting the event median holds the news itself fixed so what is left is
    the editorial choice. `metric` is 'dominance' or 'audience_p85'.
    """
    per_source: dict[str, list[float]] = {}
    for event in events:
        observed: list[tuple[str, float]] = []
        for version in event.versions:
            value = (version.mean_dominance if metric == "dominance"
                     else version.audience_p85)
            if value is not None:
                observed.append((version.source, float(value)))
        if len(observed) < 2:
            continue
        median = float(np.median([v for _, v in observed]))
        for source, value in observed:
            per_source.setdefault(source, []).append(value - median)
    return per_source


def category_mix_deviation(events: list[Event]) -> dict[str, np.ndarray]:
    """Per-outlet deviation in lexicon category MIX, again within event.

    A positive value on 'פוליטיקה' means: given the same story, this outlet's
    text leans more political than the median version of that story.
    """
    totals: dict[str, np.ndarray] = {}
    counts: dict[str, int] = {}
    for event in events:
        profiles: list[tuple[str, np.ndarray]] = []
        for version in event.versions:
            vec = np.asarray(version.lex_counts, dtype=float)
            if vec.sum() == 0:
                continue
            profiles.append((version.source, vec / vec.sum()))
        if len(profiles) < 2:
            continue
        median = np.median(np.stack([p for _, p in profiles]), axis=0)
        for source, profile in profiles:
            totals[source] = totals.get(source, np.zeros(7)) + (profile - median)
            counts[source] = counts.get(source, 0) + 1
    return {s: totals[s] / counts[s] for s in totals}


def bootstrap_ci(values: list[float], iterations: int = 4000,
                 seed: int = 20260828) -> tuple[float, float, float] | None:
    """(mean, lo, hi) at 95%. Returns None below 3 observations.

    Seeded so the kiosk replays identical numbers on every loop.
    """
    if len(values) < 3:
        return None
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    draws = rng.choice(arr, (iterations, len(arr)), replace=True).mean(axis=1)
    return float(arr.mean()), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def sampling_curve(values: list[float],
                   checkpoints: Iterable[int] = (3, 5, 10, 20, 40, 80, 160),
                   ) -> list[dict[str, float]]:
    """CI width as evidence accumulates — the honest replacement for the old
    staged accuracy arc. Nothing here is cast: the interval narrows because
    more events genuinely constrain the estimate.
    """
    curve: list[dict[str, float]] = []
    for n in checkpoints:
        if n > len(values):
            continue
        ci = bootstrap_ci(values[:n])
        if ci is None:
            continue
        curve.append({"n": n, "mean": ci[0], "lo": ci[1], "hi": ci[2],
                      "width": ci[2] - ci[1]})
    if len(values) not in [c["n"] for c in curve]:
        ci = bootstrap_ci(values)
        if ci is not None:
            curve.append({"n": len(values), "mean": ci[0], "lo": ci[1],
                          "hi": ci[2], "width": ci[2] - ci[1]})
    return curve


def coverage_matrix(events: list[Event], sources: Iterable[str]
                    ) -> dict[str, dict[str, float]]:
    """Which outlets covered the shared events.

    NOTE (kept in the returned payload, not hidden): this conflates editorial
    selection with how much of each outlet we actually crawled. An outlet with
    9 articles in the snapshot scores 0% for sampling reasons, not editorial
    ones, so `covered` must always be read next to `in_snapshot`.
    """
    per_source: dict[str, int] = {}
    for event in events:
        for source in event.sources:
            per_source[source] = per_source.get(source, 0) + 1
    total = max(len(events), 1)
    return {s: {"covered": per_source.get(s, 0), "total_events": total,
                "share": per_source.get(s, 0) / total} for s in sources}


# ---------------------------------------------------------------------------
# Per-topic framing — "which beat does this outlet reframe, and how".
# ---------------------------------------------------------------------------

# Below this many events a cell is reported but explicitly marked unusable;
# a bootstrap CI on 4 observations is not evidence about an outlet.
MIN_CELL_EVENTS = 10


@dataclass
class TopicCell:
    """One (outlet, topic) cell of the framing matrix."""

    source: str
    topic_he: str
    n: int
    deviations: list[float]
    mix: np.ndarray
    ci: tuple[float, float, float] | None

    @property
    def usable(self) -> bool:
        return self.n >= MIN_CELL_EVENTS

    @property
    def significant(self) -> bool:
        """CI excludes zero — and only counts if the cell is big enough."""
        return bool(self.usable and self.ci and (self.ci[1] > 0 or self.ci[2] < 0))

    def top_mix(self, k: int = 2) -> list[tuple[str, float]]:
        order = np.argsort(-np.abs(self.mix))[:k]
        return [(LEX_CATEGORIES_HE[i], float(self.mix[i])) for i in order]


def topic_framing_matrix(events: list[Event], metric: str = "dominance"
                         ) -> dict[tuple[str, str], TopicCell]:
    """Within-event deviation, split by the event's own topic.

    This is where an outlet's beat-level pattern shows up: an outlet can sit
    exactly on the median overall while systematically reframing one beat,
    because opposite-signed beats cancel in the pooled number.
    """
    devs: dict[tuple[str, str], list[float]] = {}
    mixes: dict[tuple[str, str], np.ndarray] = {}
    counts: dict[tuple[str, str], int] = {}
    for event in events:
        topic = event.topic_he
        if topic is None:
            continue
        observed: list[tuple[str, float]] = []
        profiles: list[tuple[str, np.ndarray]] = []
        for version in event.versions:
            value = (version.mean_dominance if metric == "dominance"
                     else version.audience_p85)
            if value is not None:
                observed.append((version.source, float(value)))
            vec = np.asarray(version.lex_counts, dtype=float)
            if vec.sum() > 0:
                profiles.append((version.source, vec / vec.sum()))
        if len(observed) >= 2:
            median = float(np.median([v for _, v in observed]))
            for source, value in observed:
                devs.setdefault((source, topic), []).append(value - median)
        if len(profiles) >= 2:
            median_mix = np.median(np.stack([p for _, p in profiles]), axis=0)
            for source, profile in profiles:
                key = (source, topic)
                mixes[key] = mixes.get(key, np.zeros(7)) + (profile - median_mix)
                counts[key] = counts.get(key, 0) + 1

    cells: dict[tuple[str, str], TopicCell] = {}
    for key, values in devs.items():
        mix = mixes.get(key, np.zeros(7)) / max(counts.get(key, 1), 1)
        cells[key] = TopicCell(source=key[0], topic_he=key[1], n=len(values),
                               deviations=values, mix=mix,
                               ci=bootstrap_ci(values))
    return cells


# ---------------------------------------------------------------------------
# Change-point detection — "did this outlet's line shift?"
# ---------------------------------------------------------------------------

# A split must leave at least this many events on each side, otherwise the
# statistic is dominated by one or two outlying articles.
MIN_SEGMENT = 8


@dataclass
class ChangePoint:
    index: int
    at: str
    before_mean: float
    after_mean: float
    shift: float
    statistic: float
    p_value: float
    n: int

    @property
    def detected(self) -> bool:
        return self.p_value < 0.05


def _max_split_statistic(values: np.ndarray) -> tuple[float, int]:
    """Worsley-style max-t over every admissible split.

    sqrt(t(n-t)/n) weighting keeps a split near the edges from winning on
    noise alone; without it the statistic is maximised at t=1 almost always.
    """
    n = len(values)
    # Start below zero, not at zero: a perfectly flat series scores 0.0 at every
    # split, and with a 0.0 floor no split would ever win, so the caller would
    # get None and the series would vanish from the scan instead of reporting
    # the correct "no change".
    best_stat, best_idx = -1.0, -1
    sd = float(values.std(ddof=1)) or 1e-9
    for t in range(MIN_SEGMENT, n - MIN_SEGMENT + 1):
        before, after = values[:t], values[t:]
        weight = np.sqrt(t * (n - t) / n)
        stat = weight * abs(before.mean() - after.mean()) / sd
        if stat > best_stat:
            best_stat, best_idx = float(stat), t
    return best_stat, best_idx


def detect_change_point(series: list[tuple[str, float]], iterations: int = 2000,
                        seed: int = 20260828) -> ChangePoint | None:
    """Find the most likely shift in a time-ordered deviation series.

    Significance comes from a permutation test rather than a table: under the
    null the observations are exchangeable in time, so shuffling the order and
    recomputing the same max-t gives an exact reference distribution. That
    matters here because the series is short and nowhere near normal.

    `series` is [(timestamp, deviation), ...]; it is sorted internally.
    Returns None when there are too few points to split at all.
    """
    ordered = sorted(series, key=lambda pair: pair[0])
    values = np.asarray([v for _, v in ordered], dtype=float)
    n = len(values)
    if n < 2 * MIN_SEGMENT:
        return None
    observed, index = _max_split_statistic(values)
    if index < 0:
        return None
    observed = max(observed, 0.0)

    rng = np.random.default_rng(seed)
    exceed = 0
    shuffled = values.copy()
    for _ in range(iterations):
        rng.shuffle(shuffled)
        stat, _ = _max_split_statistic(shuffled)
        if stat >= observed:
            exceed += 1
    # +1 smoothing: a permutation p-value can never honestly be 0.
    p_value = (exceed + 1) / (iterations + 1)
    before, after = values[:index], values[index:]
    return ChangePoint(
        index=index, at=ordered[index][0],
        before_mean=float(before.mean()), after_mean=float(after.mean()),
        shift=float(after.mean() - before.mean()),
        statistic=observed, p_value=p_value, n=n,
    )


def change_point_power(n: int, shift_in_sds: float, iterations: int = 300,
                       seed: int = 20260828) -> float:
    """Share of injected shifts of this size the detector actually catches.

    Reported next to every null result so "no change point found" is read as
    "none of a size we could see", not "none exists".
    """
    if n < 2 * MIN_SEGMENT:
        return 0.0
    rng = np.random.default_rng(seed)
    half = n // 2
    detected = 0
    for i in range(iterations):
        values = rng.normal(size=n)
        values[half:] += shift_in_sds
        series = [(f"{j:04d}", float(v)) for j, v in enumerate(values)]
        found = detect_change_point(series, iterations=200, seed=seed + i)
        if found and found.detected:
            detected += 1
    return detected / iterations


# ---------------------------------------------------------------------------
# LLM framing extraction — cached, so the kiosk never depends on the network.
# ---------------------------------------------------------------------------

FRAMING_SYSTEM = (
    "אתה מנתח מסגור תקשורתי. בהינתן כותרת ופסקה ראשונה של ידיעה בעברית, החזר "
    "JSON בלבד, בלי טקסט נוסף ובלי גדרות קוד, עם המפתחות הבאים בדיוק: "
    '{"actor": "מי מוצג כמבצע הפעולה, או null אם הניסוח סביל", '
    '"responsibility": "למי מיוחסת אחריות למצב, או null אם לא מיוחסת", '
    '"loaded_terms": ["מילות הערכה טעונות בכותרת בלבד — שמות תואר או כינויים '
    'שיפוטיים; רשימה ריקה אם הכותרת ניטרלית"], '
    '"voice": "active או passive", '
    '"lead_perspective": "מנקודת מבט של מי נפתחת הידיעה"}'
)

FRAMING_KEYS = ("actor", "responsibility", "loaded_terms", "voice", "lead_perspective")


class FramingExtractor:
    """LLM framing variables with an on-disk cache.

    The cache is what makes this exhibition-safe: extraction runs once with
    network at prepare time, and showtime replays real model output with no
    live call. `extract` returns None on any failure — callers must degrade to
    the lexicon-only view rather than showing a blank.
    """

    def __init__(self, cache_path: Path | None = None) -> None:
        self.cache_path = cache_path or (config.DATA_DIR / "framing_cache.json")
        self.cache: dict[str, dict[str, Any]] = {}
        if self.cache_path.exists():
            self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.failures = 0

    def cached(self, article_id: str) -> dict[str, Any] | None:
        return self.cache.get(article_id)

    def extract(self, article_id: str, title: str, text: str,
                allow_network: bool = True) -> dict[str, Any] | None:
        hit = self.cache.get(article_id)
        if hit is not None:
            return hit
        if not allow_network:
            return None
        parsed = self._call(title, text)
        if parsed is None:
            self.failures += 1
            return None
        self.cache[article_id] = parsed
        return parsed

    def _call(self, title: str, text: str) -> dict[str, Any] | None:
        import os

        import src.db.config  # noqa: F401  (loads .env as a side effect)
        from src.nlp.openai_config import get_openai_client

        client = get_openai_client()
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        try:
            resp = client.chat.completions.create(
                model=model, temperature=0, max_tokens=260, timeout=30,
                messages=[
                    {"role": "system", "content": FRAMING_SYSTEM},
                    {"role": "user",
                     "content": f"כותרת: {title}\nפתיח: {(text or '')[:500]}"},
                ],
            )
        except Exception:
            return None
        self.calls += 1
        if resp.usage:
            self.prompt_tokens += resp.usage.prompt_tokens
            self.completion_tokens += resp.usage.completion_tokens
        return self._parse(resp.choices[0].message.content or "")

    @staticmethod
    def _parse(raw: str) -> dict[str, Any] | None:
        """Tolerate the ~10% of responses that arrive fenced or with prose."""
        text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
        if not text.startswith("{"):
            match = re.search(r"\{.*\}", text, flags=re.S)
            if not match:
                return None
            text = match.group(0)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        out = {k: data.get(k) for k in FRAMING_KEYS}
        # The model sometimes emits the string "null" instead of JSON null.
        for key in ("actor", "responsibility", "lead_perspective"):
            if isinstance(out[key], str) and out[key].strip().lower() in ("null", "none", ""):
                out[key] = None
        if not isinstance(out["loaded_terms"], list):
            out["loaded_terms"] = []
        if out["voice"] not in ("active", "passive"):
            out["voice"] = None
        return out

    def cost_usd(self) -> float:
        return (self.prompt_tokens * config.PRICE_PROMPT_PER_M
                + self.completion_tokens * config.PRICE_COMPLETION_PER_M) / 1_000_000

    def save(self) -> None:
        self.cache_path.write_text(
            json.dumps(self.cache, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------------------
# The verifier — the second agent, and the one that earns the word "agent".
# ---------------------------------------------------------------------------

@dataclass
class Verdict:
    """What the verifier did to one extraction."""

    kept_terms: list[str]
    dropped_terms: list[str]
    actor_grounded: bool
    violations: list[str]

    @property
    def clean(self) -> bool:
        return not self.violations


def _normalise(text: str) -> str:
    """Strip quote marks and collapse whitespace so a term lifted from a
    headline still matches the headline it came from."""
    return re.sub(r"\s+", " ", re.sub(r"[\"״“”'׳]", "", text or "")).strip()


# The verifier must check against exactly the window the extractor was shown.
# Checking a wider window would let an invented term pass because it happens to
# appear deep in the body; checking a narrower one rejects terms the model was
# legitimately reading (that mistake scored 33% grounding instead of the true
# 93% on the first measurement run).
EXTRACT_LEAD_CHARS = 600


def verify_framing(framing: dict[str, Any], title: str, lead: str) -> Verdict:
    """Check an extraction against the text it claims to describe.

    Every check is deterministic string grounding, not a second opinion from a
    model: a loaded term must actually occur in the headline or lead the
    extractor was given, and a named actor must occur there too. Anything that
    fails is dropped rather than shown — an invented phrase on screen is worse
    than a blank cell.
    """
    haystack_all = _normalise(f"{title} {(lead or '')[:EXTRACT_LEAD_CHARS]}")
    kept, dropped, violations = [], [], []

    for term in framing.get("loaded_terms") or []:
        if not isinstance(term, str) or not term.strip():
            continue
        if _normalise(term) in haystack_all:
            kept.append(term)
        else:
            dropped.append(term)
            violations.append(f"מילה טעונה שאינה בטקסט: {term}")

    actor = framing.get("actor")
    actor_grounded = True
    if isinstance(actor, str) and actor.strip():
        # Proper nouns get rewritten ("טום באראק" vs "באראק"), so accept a
        # match on any word of the name rather than the whole string.
        words = [w for w in _normalise(actor).split() if len(w) >= 3]
        actor_grounded = any(w in haystack_all for w in words) if words else False
        if not actor_grounded:
            violations.append(f"מבצע שאינו מופיע בטקסט: {actor}")

    return Verdict(kept_terms=kept, dropped_terms=dropped,
                   actor_grounded=actor_grounded, violations=violations)


# ---------------------------------------------------------------------------
# Contrastive framing — this is the step that makes it retrieval-AUGMENTED.
# ---------------------------------------------------------------------------

CONTRAST_SYSTEM = (
    "אתה מנתח מסגור תקשורתי. תקבל כמה גרסאות של אותה ידיעה בדיוק, מכלי תקשורת "
    "שונים. המשימה: לומר מה ייחודי בכל גרסה ביחס לאחרות — לא לסכם אותה. "
    "החזר JSON בלבד: {\"per_source\":[{\"source\":\"...\",\"distinctive\":"
    "\"במשפט אחד, מה הגרסה הזאת מדגישה או משמיטה שהאחרות לא\",\"evidence\":"
    "\"ציטוט קצר מהכותרת או מהפתיח של אותה גרסה שמדגים זאת\"}],"
    "\"shared\":\"מה כל הגרסאות מסכימות עליו\"}"
)


def build_contrast_prompt(versions: list[tuple[str, str, str]]) -> str:
    """versions is [(source, title, lead), ...] — the retrieved siblings."""
    blocks = []
    for source, title, lead in versions:
        blocks.append(f"--- מקור: {source}\nכותרת: {title}\nפתיח: {(lead or '')[:400]}")
    return "\n\n".join(blocks)


def verify_contrast(result: dict[str, Any],
                    versions: list[tuple[str, str, str]]) -> tuple[dict[str, Any], list[str]]:
    """Same grounding rule applied to the contrastive output: an `evidence`
    quote that is not in that source's own text is dropped, because a quote the
    audience can not find on screen is the one thing that would sink this."""
    by_source = {s: _normalise(f"{t} {(l or '')[:EXTRACT_LEAD_CHARS]}")
                 for s, t, l in versions}
    violations: list[str] = []
    kept: list[dict[str, Any]] = []
    for item in result.get("per_source") or []:
        source = item.get("source")
        evidence = item.get("evidence") or ""
        haystack = by_source.get(source)
        if haystack is None:
            violations.append(f"מקור שלא נשלח למודל: {source}")
            continue
        if evidence and _normalise(evidence) not in haystack:
            violations.append(f"ציטוט שאינו בטקסט של {source}: {evidence[:40]}")
            item = {**item, "evidence": None}
        kept.append(item)
    return {**result, "per_source": kept}, violations
