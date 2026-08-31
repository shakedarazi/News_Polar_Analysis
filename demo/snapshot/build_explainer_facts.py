#!/usr/bin/env python3
"""Build demo/data/explainer_facts.json — the numbers the explainer modules show.

Two kinds of facts, and the split is the whole point:

  constants — imported live from src/ (MAX_WINDOW_TOKENS, MAX_ATTEMPTS,
              TRACKING_PARAMS, SOURCES, the prefix tables...). Nothing is
              re-typed here, so a diagram on the wall cannot drift away from
              the code it claims to describe. Change the pipeline, re-run
              this, and the wall changes with it.

  measured  — computed from demo/data/demo.sqlite, the frozen snapshot the
              kiosk already runs on. Every distribution on screen is this
              snapshot's real distribution, not an illustration.

Offline: reads local files only, no network, no OpenAI, no Postgres.

    PYTHONPATH=. python demo/snapshot/build_explainer_facts.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from demo import config  # noqa: E402
from demo.roles.agents import source_he  # noqa: E402

# ── the live constants (imported, never re-typed) ───────────────────────
from src.common.canonical_url import TRACKING_PARAMS  # noqa: E402
from src.crawling.base import (  # noqa: E402
    FAILURE_RATE_ALERT_THRESHOLD,
    MIN_DISCOVERED_FOR_FAILURE_ALERT,
)
from src.crawling.retry import INITIAL_BACKOFF_SECONDS, MAX_ATTEMPTS  # noqa: E402
from src.crawling.sources.feed_dom import SOURCES  # noqa: E402
from src.crawling.sources.reshet13 import DOM_SELECTORS as R13_SELECTORS  # noqa: E402
from src.crawling.sources.reshet13 import NEWSFEED_URL  # noqa: E402
from src.crawling.sources.ynet import RSS_FEEDS as YNET_FEEDS  # noqa: E402
from src.lexicon.expand_lexicon import (  # noqa: E402
    MIN_BASE_LENGTH,
    SINGLE_PREFIXES,
    WHITELISTED_PREFIX_PAIRS,
)
from src.nlp.sentence_splitter import MAX_WINDOW_TOKENS  # noqa: E402

FACTS_PATH = config.DATA_DIR / "explainer_facts.json"

# BaseCrawler.crawl's politeness delay default — a signature default, not a
# module constant, so it is read off the function rather than copied.
def _crawl_delay_default() -> float:
    import inspect

    from src.crawling.base import BaseCrawler

    return float(inspect.signature(BaseCrawler.crawl).parameters["delay_seconds"].default)


# extract_article_with_fallback's tier thresholds, likewise read off the
# signature so the wall shows the real gate, not a remembered one.
def _extract_thresholds() -> dict[str, int]:
    import inspect

    from src.crawling.extractors import extract_article_with_fallback

    params = inspect.signature(extract_article_with_fallback).parameters
    return {
        "min_len": int(params["min_len"].default),
        "min_paragraph_len": int(params["min_paragraph_len"].default),
    }


def build_constants() -> dict:
    return {
        "retry": {
            "max_attempts": MAX_ATTEMPTS,
            "initial_backoff_s": INITIAL_BACKOFF_SECONDS,
            # 2s, 4s — the actual sleep sequence for MAX_ATTEMPTS tries
            "backoff_sequence_s": [
                INITIAL_BACKOFF_SECONDS * (2**i) for i in range(MAX_ATTEMPTS - 1)
            ],
        },
        "crawl": {
            "delay_seconds": _crawl_delay_default(),
            "min_discovered_for_alert": MIN_DISCOVERED_FOR_FAILURE_ALERT,
            "failure_rate_threshold": FAILURE_RATE_ALERT_THRESHOLD,
        },
        "extract": _extract_thresholds(),
        "canonical": {"tracking_params": sorted(TRACKING_PARAMS)},
        "windows": {"max_window_tokens": MAX_WINDOW_TOKENS},
        "lexicon": {
            "single_prefixes": list(SINGLE_PREFIXES),
            "prefix_pairs": list(WHITELISTED_PREFIX_PAIRS),
            "min_base_length": MIN_BASE_LENGTH,
        },
        "categories_he": list(config.LEXICON_CATEGORY_NAMES_HE),
    }


def build_sources(conn: sqlite3.Connection) -> list[dict]:
    """One row per registered crawler, with this snapshot's real yield.

    A source with 0 articles is kept and shown as 0 — the registry is the
    truth about what the system crawls, and hiding an empty source would
    quietly overstate coverage.
    """
    measured = {
        row[0]: {"articles": row[1], "avg_chars": round(row[2]),
                 "min_chars": row[3], "max_chars": row[4]}
        for row in conn.execute(
            "SELECT source, COUNT(*), AVG(LENGTH(text)), MIN(LENGTH(text)), "
            "MAX(LENGTH(text)) FROM articles GROUP BY source"
        )
    }

    rows: list[dict] = [
        {
            "id": "ynet",
            "discovery": "rss",
            "feeds": list(YNET_FEEDS),
            "dom_selectors": ["div.article-body span[data-text='true']",
                              "div.ArticleBodyComponent", "[data-contents='true']"],
            "bespoke_he": "שכבת DOM ייעודית ל־draft.js של ynet",
        },
        {
            "id": "reshet13",
            "discovery": "next_data",
            "feeds": [NEWSFEED_URL],
            "dom_selectors": list(R13_SELECTORS),
            "bespoke_he": "אין RSS — הגילוי סורק את __NEXT_DATA__ של הפיד",
        },
    ]
    rows += [
        {
            "id": name,
            "discovery": "rss",
            "feeds": list(cfg.feeds),
            "dom_selectors": list(cfg.dom_selectors),
            "bespoke_he": None,
        }
        for name, cfg in SOURCES.items()
    ]

    for row in rows:
        row["source_he"] = source_he(row["id"])
        row.update(measured.get(row["id"],
                                {"articles": 0, "avg_chars": 0,
                                 "min_chars": 0, "max_chars": 0}))
    rows.sort(key=lambda r: -r["articles"])
    return rows


def _histogram(conn: sqlite3.Connection, sql: str) -> list[dict]:
    return [{"bucket": b, "n": n} for b, n in conn.execute(sql)]


def build_windows(conn: sqlite3.Connection) -> dict:
    total, null_dom = conn.execute(
        "SELECT COUNT(*), SUM(CASE WHEN dominance IS NULL THEN 1 ELSE 0 END) "
        "FROM windows_features"
    ).fetchone()
    avg_len, min_len, max_len = conn.execute(
        "SELECT AVG(window_len), MIN(window_len), MAX(window_len) FROM windows_features"
    ).fetchone()
    at_cap = conn.execute(
        "SELECT COUNT(*) FROM windows_features WHERE window_len >= ?",
        (MAX_WINDOW_TOKENS,),
    ).fetchone()[0]
    per_article = conn.execute(
        "SELECT AVG(n), MIN(n), MAX(n) FROM "
        "(SELECT COUNT(*) n FROM windows_features GROUP BY article_id)"
    ).fetchone()

    return {
        "total": total,
        "null_dominance": null_dom,
        "avg_len": round(avg_len, 1),
        "min_len": min_len,
        "max_len": max_len,
        "at_or_over_cap": at_cap,
        "per_article": {"avg": round(per_article[0], 1),
                        "min": per_article[1], "max": per_article[2]},
        # dominance buckets, chosen to match what the reading guide claims:
        # 1.0 = one category owns the window, ~0.5 = a two-way split, and so on.
        "dominance_hist": _histogram(conn, """
            SELECT CASE
                WHEN dominance IS NULL THEN 'null'
                WHEN dominance >= 1.0 THEN '1.0'
                WHEN dominance >= 0.75 THEN '0.75-1.0'
                WHEN dominance >= 0.5 THEN '0.5-0.75'
                WHEN dominance >= 0.34 THEN '0.34-0.5'
                ELSE '<0.34' END,
            COUNT(*) FROM windows_features GROUP BY 1"""),
        "active_hist": _histogram(conn, """
            SELECT CAST(active AS TEXT), COUNT(*)
            FROM windows_features GROUP BY active ORDER BY active"""),
    }


def build_comments(conn: sqlite3.Connection) -> dict:
    total, articles, avg_chars = conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT article_id), AVG(LENGTH(text)) FROM comments"
    ).fetchone()
    avg_likes, max_likes = conn.execute(
        "SELECT AVG(like_count), MAX(like_count) FROM comments"
    ).fetchone()
    agg_n, mean, p85, avg_n, max_n = conn.execute(
        "SELECT COUNT(*), AVG(audience_mean), AVG(audience_p85), "
        "AVG(num_comments), MAX(num_comments) FROM article_comments_agg"
    ).fetchone()
    return {
        "total": total,
        "articles_with_comments": articles,
        "avg_chars": round(avg_chars),
        "avg_likes": round(avg_likes, 2),
        "max_likes": max_likes,
        "aggregates": agg_n,
        "avg_audience_mean": round(mean, 4),
        "avg_audience_p85": round(p85, 4),
        "avg_num_comments": round(avg_n, 1),
        "max_num_comments": max_n,
    }


def build_lexicon() -> dict:
    """Base lemma counts vs the expanded surface forms actually looked up."""

    def count_lines(path: Path) -> int:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines()
                   if line.strip())

    base_dir = REPO_ROOT / "data" / "lexicon_base"
    comment_base = REPO_ROOT / "data" / "comment_lexicon_base" / "polar_words.txt"
    article_expanded = json.loads(
        (REPO_ROOT / "data" / "lexicon_expanded" / "lexicon_expanded.json")
        .read_text(encoding="utf-8"))
    comment_expanded = json.loads(
        (REPO_ROOT / "data" / "comment_lexicon_expanded" /
         "comment_lexicon_expanded.json").read_text(encoding="utf-8"))

    per_category = [
        {"category": i,
         "name_he": config.LEXICON_CATEGORY_NAMES_HE[i - 1],
         "base": count_lines(base_dir / f"category{i}.txt")}
        for i in range(1, 8)
    ]
    article_base = sum(c["base"] for c in per_category)
    return {
        "per_category": per_category,
        "article_base": article_base,
        "article_expanded": len(article_expanded),
        "article_factor": round(len(article_expanded) / max(1, article_base), 1),
        "comment_base": count_lines(comment_base),
        "comment_expanded": len(comment_expanded),
        "comment_factor": round(len(comment_expanded) /
                                max(1, count_lines(comment_base)), 1),
    }


def build_identity_example(conn: sqlite3.Connection) -> dict:
    """Show the dedup key surviving a dirtied URL — computed, not asserted.

    Takes a real canonical URL out of the snapshot, dirties it the way a
    share link arrives in the wild (http, uppercase host, trailing slash,
    utm/fbclid noise), and runs the real canonicaliser and hasher over both.
    `same` is the actual comparison result: if a future change to
    canonicalize_url broke the invariant, this would render false on the wall
    rather than keep claiming true.
    """
    from src.common.canonical_url import canonicalize_url
    from src.common.hashing import article_id_from_url

    row = conn.execute(
        "SELECT article_id, canonical_url FROM articles "
        "WHERE canonical_url LIKE 'https://%' AND LENGTH(canonical_url) < 110 "
        "ORDER BY article_id LIMIT 1"
    ).fetchone()
    stored_id, clean = row

    parsed = clean.replace("https://", "")
    host, _, path = parsed.partition("/")
    dirty = (f"http://{host.upper()}/{path}/"
             "?utm_source=whatsapp&utm_campaign=share&fbclid=IwAR9x")

    return {
        "clean_url": clean,
        "dirty_url": dirty,
        "clean_canonical": canonicalize_url(clean),
        "dirty_canonical": canonicalize_url(dirty),
        "article_id": article_id_from_url(clean),
        "dirty_article_id": article_id_from_url(dirty),
        "stored_article_id": stored_id,
        "same": article_id_from_url(clean) == article_id_from_url(dirty) == stored_id,
    }


def build_worked_example(conn: sqlite3.Connection) -> dict:
    """One real article walked through the real analysis functions.

    Every stage below is the pipeline's own code (`sentence_windows`,
    `normalize_text`, `tokenize`, the lexicon dict) applied to text out of the
    snapshot — the UI only steps through the result. Nothing here is authored
    prose about what the algorithm would do.
    """
    from src.analysis.article_windows import extract_window_features
    from src.lexicon.load_lexicon import load_article_lexicon
    from src.nlp.normalize import normalize_text
    from src.nlp.sentence_splitter import split_sentences, sentence_windows
    from src.nlp.tokenize import tokenize

    word_to_category, _version = load_article_lexicon()

    # A window with a genuine multi-category split is the interesting case:
    # dominance is only worth explaining when it is not 1.0.
    row = conn.execute("""
        SELECT a.article_id, a.source, a.title, a.text
        FROM articles a
        JOIN windows_features w ON w.article_id = a.article_id
        WHERE w.active >= 3 AND LENGTH(a.text) BETWEEN 900 AND 4000
        ORDER BY a.article_id LIMIT 1""").fetchone()
    article_id, source, title, text = row

    sentences = split_sentences(text)
    windows = sentence_windows(text)
    features = extract_window_features(text, word_to_category)

    # the most-split window in this article — the one worth doing by hand
    best = max(range(len(features)),
               key=lambda i: (features[i].active, features[i].window_len))
    win_text = windows[best]
    feat = features[best]

    tokens = tokenize(normalize_text(win_text), normalized=True)
    counts = [feat.c1, feat.c2, feat.c3, feat.c4, feat.c5, feat.c6, feat.c7]

    return {
        "article_id": article_id,
        "source": source,
        "source_he": source_he(source),
        "title": title,
        "text_chars": len(text),
        "sentences_total": len(sentences),
        "windows_total": len(windows),
        # first sentences with their token counts — shows the cap in context
        "sentences": [{"text": s, "tokens": len(tokenize(s))}
                      for s in sentences[:6]],
        "window": {
            "index": best,
            "raw": win_text,
            "normalized": normalize_text(win_text),
            "tokens": [{"t": t, "category": word_to_category.get(t)}
                       for t in tokens],
            "window_len": feat.window_len,
            "counts": counts,
            "cat_words": sum(counts),
            "active": feat.active,
            "max_count": max(counts),
            "dominance": feat.dominance,
        },
    }


# ── retrieval ───────────────────────────────────────────────────────────

# Thresholds swept on screen. 0.90 (CLUSTER_SIM) must be in the list: the wall
# shows the chosen value inside the same table as the ones it was chosen over.
SWEEP_THRESHOLDS = [0.84, 0.86, 0.88, 0.90, 0.92, 0.94]
SIM_BUCKETS = [
    ("<0.70", -1.0, 0.70),
    ("0.70-0.80", 0.70, 0.80),
    ("0.80-0.85", 0.80, 0.85),
    ("0.85-0.90", 0.85, 0.90),
    ("0.90-0.95", 0.90, 0.95),
    ("0.95-1.00", 0.95, 1.01),
]
JACCARD_BUCKETS = [
    ("0", -0.001, 0.0001),
    ("0-0.05", 0.0001, 0.05),
    ("0.05-0.10", 0.05, 0.10),
    ("0.10-0.25", 0.10, 0.25),
    ("0.25+", 0.25, 1.01),
]


def _bucketize(values, buckets) -> list[dict]:
    return [{"label": label, "n": int(((values >= lo) & (values < hi)).sum())}
            for label, lo, hi in buckets]


def build_retrieval(conn: sqlite3.Connection) -> dict:
    """The semantic-retrieval layer: what is indexed, how the cut was chosen,
    and what a keyword baseline would have found instead.

    Everything here is recomputed from the frozen index + snapshot, including
    the threshold sweep — so the table on the wall is the experiment, not a
    memory of one. The embedding model is NOT loaded: the vectors were computed
    offline by prepare_demo.py and this only reads them.
    """
    import time

    import numpy as np

    from demo.core import framing as F
    from demo.core.framing import (Snapshot, build_event_clusters,
                                   keyword_jaccard)
    from demo.snapshot.prepare_demo import MIN_TEXT_CHARS, PASSAGE_LEAD_CHARS

    snap = Snapshot()
    articles = snap.articles()
    ids = [i for i in snap.vec_by_id if i in articles]
    matrix = np.stack([snap.vec_by_id[i] for i in ids])

    # ---- corpus coverage: who got into the index, and who was left out
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    too_short = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE length(coalesce(text,'')) <= ?",
        (MIN_TEXT_CHARS,),
    ).fetchone()[0]
    per_source: dict[str, dict] = {}
    for row in conn.execute(
        "SELECT source, COUNT(*) n,"
        " SUM(CASE WHEN length(coalesce(text,'')) > ? THEN 1 ELSE 0 END) long"
        " FROM articles GROUP BY source", (MIN_TEXT_CHARS,)
    ):
        per_source[row[0]] = {"source": row[0], "source_he": source_he(row[0]),
                              "articles": row[1], "indexed": 0}
    for article_id in ids:
        per_source[articles[article_id]["source"]]["indexed"] += 1

    # ---- the similarity distribution: what a cosine score is worth here
    sim = matrix @ matrix.T
    upper = sim[np.triu_indices(len(ids), k=1)]
    above = [{"threshold": t, "n": int((upper >= t).sum()),
              "pct": round(float((upper >= t).mean()) * 100, 3)}
             for t in (0.80, 0.86, 0.88, 0.90, 0.92, 0.95)]

    # ---- the threshold sweep: the choice, with what each value costs
    sweep = []
    original = F.CLUSTER_SIM
    try:
        for threshold in SWEEP_THRESHOLDS:
            F.CLUSTER_SIM = threshold
            events = build_event_clusters(snap)
            sweep.append({
                "threshold": threshold,
                "events": len(events),
                "three_plus": sum(1 for e in events if len(e.sources) >= 3),
                "versions": sum(len(e.versions) for e in events),
                "chosen": threshold == original,
            })
    finally:
        F.CLUSTER_SIM = original

    events = build_event_clusters(snap)

    # ---- the keyword baseline, over every event rather than the showcase
    jaccards, found, blind = [], 0, 0
    for event in events:
        seed = event.versions[0]
        hits = [keyword_jaccard(seed.title, v.title) for v in event.versions[1:]]
        jaccards.extend(hits)
        matched = sum(1 for j in hits if j >= F.KEYWORD_JACCARD)
        found += matched
        if hits and matched == 0:
            blind += 1
    jac = np.asarray(jaccards, dtype=float)

    # ---- one event, fully worked: prefer the one a keyword search is most
    # blind to (most zero-overlap pairs), tie-broken deterministically.
    example = _retrieval_example(snap, events, articles, ids, matrix)

    # ---- what the index sees that sha256(url) cannot
    duplicates = _duplicate_pairs(articles, ids, sim)

    query = matrix[0]
    start = time.perf_counter()
    for _ in range(200):
        _ = matrix @ query
    query_ms = (time.perf_counter() - start) / 200 * 1000

    return {
        "model": config.EMBED_MODEL,
        "dims": int(matrix.shape[1]),
        "vectors": len(ids),
        "bytes": int(matrix.nbytes),
        "query_ms": round(query_ms, 4),
        "min_text_chars": MIN_TEXT_CHARS,
        "passage_lead_chars": PASSAGE_LEAD_CHARS,
        "cluster_sim": F.CLUSTER_SIM,
        "keyword_jaccard": F.KEYWORD_JACCARD,
        "corpus": {
            "total": total, "indexed": len(ids), "too_short": too_short,
            "per_source": sorted(per_source.values(),
                                 key=lambda r: -r["articles"]),
        },
        "events": {
            "total": len(events),
            "versions": sum(len(e.versions) for e in events),
            "three_plus": sum(1 for e in events if len(e.sources) >= 3),
        },
        "keyword": {
            "found": found, "total": int(jac.size),
            "recall": round(found / max(int(jac.size), 1), 4),
            "zero_overlap": int((jac == 0).sum()),
            "blind_events": blind,
            "median": round(float(np.median(jac)), 4) if jac.size else None,
            "histogram": _bucketize(jac, JACCARD_BUCKETS),
        },
        "similarity": {
            "pairs": int(upper.size),
            "mean": round(float(upper.mean()), 4),
            "median": round(float(np.median(upper)), 4),
            "histogram": _bucketize(upper, SIM_BUCKETS),
            "above": above,
        },
        "sweep": sweep,
        "example": example,
        "duplicates": duplicates,
        "slots": _slot_policies(snap, events, articles),
    }


def _slot_policies(snap, events, articles) -> dict:
    """How current a news retrieval index has to be, and what keeps it that way.

    The live index has no window and no eviction: it holds every indexed
    article, 1.1 MB, a full dot product per query. At 4.8 days of corpus that
    is the right call, and the honest thing to show is what changes when the
    corpus is a year instead of a week.

    Two measurements, in the order the decision is actually made. First the
    data's own time constant — how long after a story breaks its other versions
    still arrive — because that, not memory, is what sets the window. Then a
    replay of the real arrival order through a K-slot index under four textbook
    policies, to see which one a rolling window should be implemented as.

    Deterministic: the random-replacement arm is seeded, everything else is a
    pure function of arrival order.
    """
    import random
    from datetime import datetime

    # Only articles that are actually in the index enter the stream. The set is
    # taken from the index itself rather than re-derived from a length rule, so
    # this table cannot drift from the vectors it describes.
    order = sorted((a for a in articles.values()
                    if a["article_id"] in snap.vec_by_id),
                   key=lambda a: (a["first_seen_at"] or "", a["article_id"]))
    position = {a["article_id"]: i for i, a in enumerate(order)}
    fire_at: dict[int, list] = {}
    for event in events:
        ids = [v.article_id for v in event.versions if v.article_id in position]
        if len(ids) < 2:
            continue
        last = max(ids, key=lambda x: position[x])
        fire_at.setdefault(position[last], []).append((last, ids))

    def replay(k: int, policy: str, seed: int = 7) -> tuple[int, int]:
        rng = random.Random(seed)
        resident: dict[str, None] = {}   # insertion order doubles as FIFO order
        used: dict[str, int] = {}
        recency: dict[str, int] = {}
        clock = 0
        found = total = 0

        def touch(aid: str) -> None:
            nonlocal clock
            clock += 1
            recency[aid] = clock
            used[aid] = used.get(aid, 0) + 1

        def evict() -> None:
            if policy == "fifo":
                victim = next(iter(resident))
            elif policy == "lru":
                victim = min(resident, key=lambda a: recency.get(a, 0))
            elif policy == "lfu":
                victim = min(resident,
                             key=lambda a: (used.get(a, 0), recency.get(a, 0)))
            else:
                victim = rng.choice(list(resident))
            resident.pop(victim, None)

        for i, article in enumerate(order):
            aid = article["article_id"]
            if aid not in resident:
                if len(resident) >= k:
                    evict()
                resident[aid] = None
            touch(aid)
            for query_id, ids in fire_at.get(i, []):
                siblings = [x for x in ids if x != query_id]
                total += len(siblings)
                for sibling in siblings:
                    if sibling in resident:
                        found += 1
                        touch(sibling)
        return found, total

    policies = [
        {"key": "fifo", "label_he": "הנכנס הראשון יוצא ראשון",
         "note_he": "בלי חשבונאות לכל גישה"},
        {"key": "lru", "label_he": "הכי מזמן שהיה בשימוש",
         "note_he": "שעון גישה לכל פריט"},
        {"key": "lfu", "label_he": "הכי מעט בשימוש",
         "note_he": "מונה גישות לכל פריט"},
        {"key": "rr", "label_he": "פינוי אקראי",
         "note_he": "ממוצע 20 ריצות, בסיס להשוואה"},
    ]
    sizes = [50, 100, 200, 400, len(order) // 2, len(order)]
    sizes = sorted({s for s in sizes if 0 < s <= len(order)})
    # The random arm is stochastic, so one seed is an anecdote: at some K a
    # lucky draw beats every deterministic policy. It is averaged over
    # RR_SEEDS runs and labelled as a mean; the other three are deterministic
    # and run once.
    rr_seeds = 20
    rows = []
    for k in sizes:
        row = {"k": k}
        for policy in policies:
            if policy["key"] == "rr":
                results = [replay(k, "rr", seed)[0] for seed in range(rr_seeds)]
                row["rr"] = round(sum(results) / len(results))
                row["total"] = replay(k, "fifo")[1]
            else:
                found, total = replay(k, policy["key"])
                row[policy["key"]] = found
                row["total"] = total
        rows.append(row)

    # ---- the time constant: how long a story keeps collecting versions
    def parsed(value):
        try:
            return datetime.fromisoformat(value) if value else None
        except ValueError:
            return None

    arrivals = [parsed(a["first_seen_at"]) for a in order]
    arrivals = [a for a in arrivals if a]
    corpus_hours = ((max(arrivals) - min(arrivals)).total_seconds() / 3600
                    if len(arrivals) > 1 else 0.0)
    per_day = len(arrivals) / (corpus_hours / 24) if corpus_hours else 0.0

    spans = []
    for event in events:
        stamps = [parsed(articles[v.article_id]["first_seen_at"])
                  for v in event.versions if v.article_id in articles]
        stamps = [s for s in stamps if s]
        if len(stamps) >= 2:
            spans.append((max(stamps) - min(stamps)).total_seconds() / 3600)
    spans.sort()

    def quantile(q: float) -> float:
        if not spans:
            return 0.0
        return round(spans[min(len(spans) - 1, int(len(spans) * q))], 1)

    windows = [{"hours": w,
                "covered": round(sum(1 for s in spans if s <= w) / len(spans), 4)
                if spans else 0.0,
                "slots": int(round(per_day * w / 24))}
               for w in (6, 12, 24, 48, 72, 168)]

    return {
        "policies": policies,
        "rows": rows,
        "corpus": len(order),
        "freshness": {
            "events": len(spans),
            "corpus_days": round(corpus_hours / 24, 1),
            "per_day": round(per_day),
            "p50_hours": quantile(0.50),
            "p75_hours": quantile(0.75),
            "p90_hours": quantile(0.90),
            "windows": windows,
        },
        # what the live system does today — stated so the table above cannot be
        # mistaken for a description of it
        "current": {"window_hours": None, "policy": None,
                    "resident": len(order)},
    }


def _retrieval_example(snap, events, articles, ids, matrix) -> dict:
    """Replay the greedy pass for ONE event, keeping what the pass discarded.

    build_event_clusters returns only survivors, and the discards are half the
    lesson: a neighbour above the threshold that the one-per-source rule drops,
    and the first neighbour below the threshold — the article the cut refused.
    """
    import numpy as np

    from demo.core import framing as F
    from demo.core.framing import keyword_jaccard

    def blindness(event) -> tuple:
        seed = event.versions[0]
        hits = [keyword_jaccard(seed.title, v.title) for v in event.versions[1:]]
        return (sum(1 for j in hits if j == 0), -max(hits), event.event_id)

    candidates = [e for e in events if len(e.versions) >= 3]
    if not candidates:
        candidates = events
    if not candidates:
        return {}
    event = max(candidates, key=blindness)
    seed_id = event.versions[0].article_id
    kept = {v.article_id for v in event.versions}

    scores = matrix @ snap.vec_by_id[seed_id]
    order = np.argsort(-scores)
    seed_title = articles[seed_id]["title"]

    neighbours, rejected = [], None
    for j in order:
        article_id, score = ids[j], float(scores[j])
        if article_id == seed_id:
            continue
        if score <= F.CLUSTER_SIM:
            row = articles[article_id]
            rejected = {"source": row["source"], "source_he": source_he(row["source"]),
                        "title": row["title"], "cos": round(score, 4)}
            break
        row = articles[article_id]
        shared = sorted(F._tokens(seed_title) & F._tokens(row["title"]))
        neighbours.append({
            "source": row["source"], "source_he": source_he(row["source"]),
            "title": row["title"], "cos": round(score, 4),
            "jaccard": round(keyword_jaccard(seed_title, row["title"]), 4),
            "shared": shared,
            "kept": article_id in kept,
        })

    return {
        "topic_he": event.topic_he,
        "seed": {"source": articles[seed_id]["source"],
                 "source_he": source_he(articles[seed_id]["source"]),
                 "title": seed_title},
        "neighbours": neighbours,
        "rejected": rejected,
    }


def _duplicate_pairs(articles, ids, sim, threshold: float = 0.999) -> dict:
    """Near-identical vectors — the same story under two URLs.

    article_id is sha256 of the canonical URL, so identity is a URL fact, not a
    content fact. The index does not fix that; it makes it visible, which is
    why it belongs on the wall rather than in a drawer.
    """
    import numpy as np

    rows, upper = [], np.triu(sim, k=1)
    for i, j in zip(*np.where(upper >= threshold)):
        a, b = articles[ids[i]], articles[ids[j]]
        rows.append({
            "cos": round(float(sim[i][j]), 5),
            "source": a["source"], "source_he": source_he(a["source"]),
            "title": a["title"],
            "url_a": a["canonical_url"], "url_b": b["canonical_url"],
            "id_a": ids[i][:12], "id_b": ids[j][:12],
        })
    rows.sort(key=lambda r: r["id_a"])
    return {"threshold": threshold, "pairs": len(rows), "examples": rows[:3]}


# ── framing + verifier ──────────────────────────────────────────────────

# Why a rejected quote failed. The verifier itself does not classify — it just
# says no — so this split is computed here, after the fact, to answer the
# obvious question from the floor: is the model making things up, or is our
# check blunt? The answer turns out to be "mostly the second", and that
# belongs on the wall rather than in a drawer.
_PUNCT = None


def _loose(text: str) -> str:
    """Punctuation-insensitive form, for asking 'was this verbatim apart from
    a full stop the model added at the end?'"""
    import re

    global _PUNCT
    if _PUNCT is None:
        _PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
    return re.sub(r"\s+", " ", _PUNCT.sub("", text or "")).strip()


def build_framing() -> dict:
    """The model layer and the deterministic check that trims it.

    Every rate here is counted over the whole cache rather than the showcase
    event, so what the wall reports is the extractor's behaviour and not one
    lucky story. Nothing calls the model: the cache on disk IS the measurement.
    """
    import collections
    import difflib
    import re

    from demo.core.framing import (CONTRAST_MAX_TOKENS, CONTRAST_SYSTEM,
                                   EXTRACT_LEAD_CHARS, FRAMING_KEYS,
                                   FRAMING_MAX_TOKENS, FRAMING_SYSTEM,
                                   ContrastExtractor, FramingExtractor,
                                   Snapshot, _normalise, build_event_clusters,
                                   verify_framing)
    from demo.snapshot.prepare_demo import CONTRAST_VERSIONS

    snap = Snapshot()
    articles = snap.articles()
    events = build_event_clusters(snap)
    framer, contraster = FramingExtractor(), ContrastExtractor()

    # ---- what the model actually returns, across the whole cache
    voices: collections.Counter = collections.Counter()
    per_article: collections.Counter = collections.Counter()
    actor_null = responsibility_null = 0
    for value in framer.cache.values():
        voices[value.get("voice") or "null"] += 1
        per_article[len(value.get("loaded_terms") or [])] += 1
        actor_null += value.get("actor") is None
        responsibility_null += value.get("responsibility") is None

    # ---- the grounding pass over every extraction
    terms_total = terms_rejected = 0
    actors_exact = actors_word_level = actors_rejected = 0
    term_example = None
    for event in events:
        for version in event.versions:
            framing = framer.cached(version.article_id)
            if not framing:
                continue
            lead = (articles[version.article_id]["text"] or "")[:EXTRACT_LEAD_CHARS]
            verdict = verify_framing(framing, version.title,
                                     articles[version.article_id]["text"])
            terms_total += len(verdict.kept_terms) + len(verdict.dropped_terms)
            terms_rejected += len(verdict.dropped_terms)
            actor = framing.get("actor")
            if actor:
                haystack = _normalise(f"{version.title} {lead}")
                if not verdict.actor_grounded:
                    actors_rejected += 1
                elif _normalise(actor) in haystack:
                    actors_exact += 1
                else:
                    actors_word_level += 1
            # the first drop, with everything needed to check it on screen
            if verdict.dropped_terms and term_example is None:
                term_example = {
                    "source": version.source,
                    "source_he": source_he(version.source),
                    "title": version.title,
                    "lead": lead,
                    "framing": framing,
                    "kept": verdict.kept_terms,
                    "dropped": verdict.dropped_terms,
                }

    # ---- the contrastive step, and why its quotes get dropped
    by_event = {e.event_id: e for e in events}
    reasons: collections.Counter = collections.Counter()
    quotes_total = 0
    quote_examples: dict[str, dict] = {}
    contrast_example = None
    for event_id, result in contraster.cache.items():
        event = by_event.get(event_id)
        if event is None:
            continue
        texts = {v.source: (v.title, articles[v.article_id]["text"])
                 for v in event.versions[:CONTRAST_VERSIONS]}
        rendered = []
        for item in result.get("per_source") or []:
            source = item.get("source")
            evidence = item.get("evidence") or ""
            if source not in texts:
                continue
            title, body = texts[source]
            haystack = _normalise(f"{title} {(body or '')[:EXTRACT_LEAD_CHARS]}")
            kept = True
            if evidence:
                quotes_total += 1
                if _normalise(evidence) not in haystack:
                    kept = False
                    kind = _quote_failure_kind(_normalise(evidence), haystack,
                                               difflib)
                    reasons[kind] += 1
                    quote_examples.setdefault(kind, {
                        "kind": kind,
                        "source": source, "source_he": source_he(source),
                        "evidence": evidence,
                        "excerpt": _closest_excerpt(_normalise(evidence),
                                                    haystack, difflib),
                    })
            rendered.append({
                "source": source, "source_he": source_he(source),
                "title": title,
                "distinctive": item.get("distinctive"),
                "evidence": evidence or None,
                "kept": kept,
            })
        if contrast_example is None and len(rendered) >= 3 and any(
                not r["kept"] for r in rendered):
            contrast_example = {
                "topic_he": event.topic_he,
                "shared": result.get("shared"),
                "per_source": rendered,
            }

    # ---- the acronym repair, measured rather than asserted
    acronym = re.compile(r'(?<=[\u0590-\u05ff])"(?=[\u0590-\u05ff])')
    word = re.compile(r'[\u0590-\u05ff]+"[\u0590-\u05ff]+')

    def strings(obj):
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                yield from strings(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from strings(v)

    def hits(cache) -> int:
        return sum(1 for v in cache.values()
                   if any(acronym.search(s) for s in strings(v)))

    distinct = sorted({m for cache in (framer.cache, contraster.cache)
                       for v in cache.values() for s in strings(v)
                       for m in word.findall(s)})

    return {
        "model": "gpt-4o-mini",
        "temperature": 0,
        "lead_chars": EXTRACT_LEAD_CHARS,
        "max_tokens": {"framing": FRAMING_MAX_TOKENS,
                       "contrast": CONTRAST_MAX_TOKENS},
        "contrast_versions": CONTRAST_VERSIONS,
        "keys": list(FRAMING_KEYS),
        "framing_system": FRAMING_SYSTEM,
        "contrast_system": CONTRAST_SYSTEM,
        "cache": {"framing": len(framer.cache),
                  "contrast": len(contraster.cache)},
        "distribution": {
            "total": len(framer.cache),
            "voice": [{"label": k, "n": n} for k, n in voices.most_common()],
            "terms_per_article": [{"terms": k, "n": per_article[k]}
                                  for k in sorted(per_article)],
            "actor_null": actor_null,
            "responsibility_null": responsibility_null,
        },
        "verifier": {
            "terms_total": terms_total, "terms_rejected": terms_rejected,
            "actors_total": actors_exact + actors_word_level + actors_rejected,
            "actors_rejected": actors_rejected,
            "actors_exact": actors_exact,
            "actors_word_level": actors_word_level,
            "quotes_total": quotes_total,
            "quotes_rejected": sum(reasons.values()),
            "quote_reasons": [{"kind": k, "n": n}
                              for k, n in sorted(reasons.items())],
        },
        "acronyms": {
            "framing_hits": hits(framer.cache),
            "framing_total": len(framer.cache),
            "contrast_hits": hits(contraster.cache),
            "contrast_total": len(contraster.cache),
            "distinct": len(distinct),
            "examples": distinct[:10],
        },
        "term_example": term_example,
        "quote_examples": list(quote_examples.values()),
        "contrast_example": contrast_example,
    }


def _quote_failure_kind(quote: str, haystack: str, difflib) -> str:
    """punct — verbatim apart from punctuation the model added or dropped.
    wrapper — the quote contains the prose plus a label the model bolted on.
    paraphrase — the model rewrote or elided; the only genuine miss."""
    if _loose(quote) and _loose(quote) in _loose(haystack):
        return "punct"
    match = difflib.SequenceMatcher(None, quote, haystack).find_longest_match(
        0, len(quote), 0, len(haystack))
    return "wrapper" if quote and match.size / len(quote) >= 0.8 else "paraphrase"


def _closest_excerpt(quote: str, haystack: str, difflib, pad: int = 40) -> str:
    """The stretch of real text the quote came closest to — so the audience
    can see for themselves how near the miss was."""
    match = difflib.SequenceMatcher(None, quote, haystack).find_longest_match(
        0, len(quote), 0, len(haystack))
    start = max(0, match.b - pad)
    return haystack[start:match.b + match.size + pad]


# ── the audience signal ─────────────────────────────────────────────────
# Reader engagement is the one input the pipeline does not control: we take
# whatever each outlet's comment widget happens to expose. That makes this
# the module where "what the data does not contain" matters as much as the
# formulas, so almost everything below is a coverage measurement.

RATIO_BUCKETS = [
    ("0", 0.0, 0.0),
    ("0-0.02", 0.0, 0.02),
    ("0.02-0.05", 0.02, 0.05),
    ("0.05-0.10", 0.05, 0.10),
    ("0.10-0.20", 0.10, 0.20),
    ("0.20+", 0.20, 1.01),
]

# Likes to show on the weight curve. Endpoints are replaced by the snapshot's
# real maximum at build time so the curve ends where the data ends.
WEIGHT_LIKES = [0, 1, 3, 10, 30, 100, 300]


def _ratio_hist(values: list[float]) -> list[dict]:
    out = []
    for label, lo, hi in RATIO_BUCKETS:
        if lo == hi == 0.0:
            n = sum(1 for v in values if v == 0.0)
        else:
            n = sum(1 for v in values if lo < v < hi or (v == lo and lo > 0))
        out.append({"label": label, "n": n})
    return out


def _audience_quantile_default(weighted_quantile) -> float:
    """0.85 read off aggregation._weighted_quantile, not re-typed here."""
    import inspect

    return float(inspect.signature(weighted_quantile).parameters["quantile"].default)


def build_audience(conn: sqlite3.Connection) -> dict:
    import math
    import statistics
    from collections import Counter, defaultdict

    from src.analysis.aggregation import _weighted_mean, _weighted_quantile
    from src.analysis.comments_scoring import (
        controversy,
        engagement_weight,
        score_comment,
    )
    from src.lexicon.load_lexicon import load_comment_lexicon
    from src.nlp.normalize import normalize_text
    from src.nlp.tokenize import tokenize

    polar, _polar_version = load_comment_lexicon()
    conn.row_factory = sqlite3.Row

    sources = {r["article_id"]: r["source"]
               for r in conn.execute("SELECT article_id, source FROM articles")}
    titles = {r["article_id"]: r["title"]
              for r in conn.execute("SELECT article_id, title FROM articles")}

    per_article: dict[str, list] = defaultdict(list)
    raw_by_id: dict[str, dict] = {}
    lengths: list[int] = []
    ratios: list[float] = []
    inert = 0
    ratio_one_lengths: Counter = Counter()
    ratio_one_examples: list[dict] = []
    per_source_comments: dict[str, dict] = defaultdict(
        lambda: {"comments": 0, "likes": 0, "inert": 0})

    rows = conn.execute(
        "SELECT comment_id, article_id, source, text, like_count FROM comments")
    for row in rows:
        likes = int(row["like_count"] or 0)
        feat = score_comment(comment_id=row["comment_id"], text=row["text"] or "",
                             polar_lexicon=polar, like_count=likes)
        per_article[row["article_id"]].append(feat)
        raw_by_id[row["comment_id"]] = {"text": row["text"] or "", "likes": likes}
        lengths.append(feat.comment_len)
        ratios.append(feat.polar_ratio)
        bucket = per_source_comments[row["source"]]
        bucket["comments"] += 1
        bucket["likes"] += likes
        if feat.engagement_weight == 1.0:
            inert += 1
            bucket["inert"] += 1
        if feat.polar_ratio == 1.0:
            ratio_one_lengths[feat.comment_len] += 1
            if len(ratio_one_examples) < 6:
                ratio_one_examples.append({
                    "source": row["source"],
                    "source_he": source_he(row["source"]),
                    "text": (row["text"] or "").strip()[:40],
                    "likes": likes,
                    "len": feat.comment_len,
                })

    # What the like-weighting actually changes: the SAME estimator run with
    # every weight forced to 1.0. Anything else would compare two different
    # statistics and blame the difference on the weights.
    shift_mean: list[float] = []
    shift_p85: list[float] = []
    per_source_shift: dict[str, list[float]] = defaultdict(list)
    for article_id, feats in per_article.items():
        scores = [f.comment_score for f in feats]
        weights = [f.engagement_weight for f in feats]
        flat = [1.0] * len(feats)
        wm, um = _weighted_mean(scores, weights), _weighted_mean(scores, flat)
        wp, up = _weighted_quantile(scores, weights), _weighted_quantile(scores, flat)
        if wm is None or wp is None:
            continue
        shift_mean.append(abs(wm - um))
        shift_p85.append(abs(wp - up))
        per_source_shift[sources.get(article_id, "?")].append(abs(wp - up))

    per_source = []
    for source, bucket in sorted(per_source_comments.items(),
                                 key=lambda kv: -kv[1]["comments"]):
        shifts = per_source_shift.get(source, [])
        per_source.append({
            "source": source,
            "source_he": source_he(source),
            "comments": bucket["comments"],
            "likes": bucket["likes"],
            "avg_likes": round(bucket["likes"] / max(1, bucket["comments"]), 2),
            "inert": bucket["inert"],
            "articles": len(shifts),
            "articles_unaffected": sum(1 for s in shifts if s == 0.0),
            "mean_p85_shift": round(statistics.mean(shifts), 5) if shifts else 0.0,
        })

    likes_max = max((r["likes"] for r in raw_by_id.values()), default=0)
    curve = [{"likes": n, "weight": round(engagement_weight(n), 3)}
             for n in WEIGHT_LIKES if n < likes_max]
    curve.append({"likes": likes_max, "weight": round(engagement_weight(likes_max), 3)})

    agg_rows = [dict(r) for r in conn.execute(
        "SELECT audience_mean, audience_p85, controversy_mean, num_comments"
        " FROM article_comments_agg WHERE num_comments > 0")]
    p85 = [r["audience_p85"] for r in agg_rows if r["audience_p85"] is not None]
    means = [r["audience_mean"] for r in agg_rows if r["audience_mean"] is not None]
    counts = [r["num_comments"] for r in agg_rows]

    facts = {
        "polar_lexicon_forms": len(polar),
        "quantile": _audience_quantile_default(_weighted_quantile),
        "comments": {
            "total": len(lengths),
            "articles": len(per_article),
            "len_mean": round(statistics.mean(lengths), 1),
            "len_median": statistics.median(lengths),
            "len_max": max(lengths),
            "len_under_4": sum(1 for x in lengths if x <= 3),
            "zero_polar": sum(1 for x in ratios if x == 0.0),
            "ratio_mean": round(statistics.mean(ratios), 5),
            "ratio_hist": _ratio_hist(ratios),
        },
        "weight": {
            "curve": curve,
            "max_likes": likes_max,
            "inert": inert,
            "shift_mean": round(statistics.mean(shift_mean), 5) if shift_mean else 0.0,
            "shift_p85": round(statistics.mean(shift_p85), 5) if shift_p85 else 0.0,
            "articles": len(shift_p85),
            "articles_unaffected": sum(1 for s in shift_p85 if s == 0.0),
            "per_source": per_source,
        },
        # The pipeline computes this on every comment. No Israeli outlet in the
        # snapshot exposes a dislike count, so p is always 1 and 4p(1-p) is
        # always 0 — a live metric with no data behind it.
        "controversy": {
            "articles": len(agg_rows),
            "nonzero": sum(1 for r in agg_rows if (r["controversy_mean"] or 0) > 0),
            "at_one_like": round(controversy(1, 0), 4),
            "at_even_split": round(controversy(1, 1), 4),
        },
        "aggregate": {
            "p85_mean": round(statistics.mean(p85), 4),
            "p85_median": round(statistics.median(p85), 4),
            "p85_zero": sum(1 for x in p85 if x == 0.0),
            "p85_one": sum(1 for x in p85 if x == 1.0),
            "mean_median": round(statistics.median(means), 4),
            "p85_hist": _ratio_hist(p85),
            "counts": {
                "median": statistics.median(counts),
                "under_5": sum(1 for x in counts if x < 5),
                "under_10": sum(1 for x in counts if x < 10),
                "total": len(counts),
            },
        },
        "artifacts": {
            "ratio_one": sum(ratio_one_lengths.values()),
            "single_token": ratio_one_lengths.get(1, 0),
            "examples": ratio_one_examples,
        },
        "example": _audience_example(per_article, raw_by_id, sources, titles,
                                    polar, normalize_text, tokenize,
                                    _weighted_mean, _weighted_quantile,
                                    _audience_quantile_default(_weighted_quantile)),
    }
    facts.update(_audience_events(math))
    return facts


# The article the worked example walks through. Chosen once, by hand, for one
# reason: its most-liked comment is furious and scores exactly 0.0000, so the
# example teaches the limit at the same time as the formula. Pinned by title so
# a re-export that reshuffles ids still finds it, with a fallback if it is gone.
EXAMPLE_TITLE = 'ומי ישלם על קריסת נתב"ג?'


def _audience_example(per_article, raw_by_id, sources, titles, polar,
                      normalize_text, tokenize, weighted_mean, weighted_quantile,
                      quantile) -> dict | None:
    wanted = [aid for aid, t in titles.items() if t == EXAMPLE_TITLE
              and aid in per_article]
    if not wanted:
        wanted = sorted((aid for aid in per_article if 8 <= len(per_article[aid]) <= 12),
                        key=lambda a: -len(per_article[a]))[:1]
    if not wanted:
        return None
    article_id = wanted[0]
    feats = sorted(per_article[article_id], key=lambda f: -f.like_count)

    comments = []
    for feat in feats:
        raw = raw_by_id[feat.comment_id]
        tokens = tokenize(normalize_text(raw["text"]), normalized=True)
        comments.append({
            "text": raw["text"].strip(),
            "likes": feat.like_count,
            "len": feat.comment_len,
            "polar": feat.polar_count,
            "hits": [t for t in tokens if t in polar],
            "ratio": round(feat.polar_ratio, 4),
            "weight": round(feat.engagement_weight, 3),
        })

    scores = [f.comment_score for f in feats]
    weights = [f.engagement_weight for f in feats]
    flat = [1.0] * len(feats)
    total_weight = sum(weights)
    target = quantile * total_weight

    walk, cumulative, landed = [], 0.0, False
    for value, weight in sorted(zip(scores, weights), key=lambda p: p[0]):
        cumulative += weight
        hit = not landed and cumulative >= target
        landed = landed or hit
        walk.append({"value": round(value, 4), "weight": round(weight, 3),
                     "cum": round(cumulative, 3), "hit": hit})

    return {
        "article_id": article_id,
        "source": sources.get(article_id, "?"),
        "source_he": source_he(sources.get(article_id, "?")),
        "title": titles.get(article_id, ""),
        "comments": comments,
        "weighted": {"mean": round(weighted_mean(scores, weights), 5),
                     "p85": round(weighted_quantile(scores, weights), 5)},
        "unweighted": {"mean": round(weighted_mean(scores, flat), 5),
                       "p85": round(weighted_quantile(scores, flat), 5)},
        "sum_weight": round(total_weight, 3),
        "target": round(target, 3),
        "walk": walk,
    }


def _audience_events(math) -> dict:
    """Topic hijacking and the within-event audience deviation.

    Both need the event clustering, so they are built from demo.core.framing
    rather than from SQL — the same clusters the kiosk itself shows.
    """
    import statistics
    from collections import Counter, defaultdict

    from demo.core.framing import (
        Snapshot,
        attach_comment_profiles,
        build_event_clusters,
        outlet_deviation,
    )

    snap = Snapshot()
    events = build_event_clusters(snap)

    comparable = 0
    hijacked = 0
    per_source: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    pairs: Counter = Counter()
    examples: list[tuple] = []
    for event in events:
        attach_comment_profiles(snap, event)
        for version in event.versions:
            article_topic, comment_topic = version.lex_top_he, version.comment_top_he
            if not (article_topic and comment_topic):
                continue
            comparable += 1
            per_source[version.source][1] += 1
            if version.audience_hijacked:
                hijacked += 1
                per_source[version.source][0] += 1
                pairs[(article_topic, comment_topic)] += 1
                top = snap.top_comment(version.article_id) or {}
                examples.append((
                    version.num_comments or 0, version.source, version.title,
                    article_topic, comment_topic,
                    (top.get("text") or "").strip()[:150], top.get("like_count") or 0,
                ))
    examples.sort(key=lambda e: -e[0])

    deviation = []
    for source, values in sorted(outlet_deviation(events, "audience_p85").items(),
                                 key=lambda kv: -len(kv[1])):
        deviation.append({
            "source": source,
            "source_he": source_he(source),
            "n": len(values),
            "mean": round(statistics.mean(values), 4),
            "median": round(statistics.median(values), 4),
        })

    return {
        "hijack": {
            "events": len(events),
            "comparable": comparable,
            "hijacked": hijacked,
            "per_source": [
                {"source": s, "source_he": source_he(s), "hijacked": v[0], "total": v[1]}
                for s, v in sorted(per_source.items(), key=lambda kv: -kv[1][1])
            ],
            "pairs": [{"article_he": a, "comments_he": c, "n": n}
                      for (a, c), n in pairs.most_common(6)],
            "examples": [
                {"num_comments": e[0], "source": e[1], "source_he": source_he(e[1]),
                 "title": e[2], "article_he": e[3], "comments_he": e[4],
                 "top_comment": e[5], "top_likes": e[6]}
                for e in examples[:3]
            ],
        },
        "deviation": deviation,
    }


# ── the statistics layer ────────────────────────────────────────────────
# Everything here is recomputed from the snapshot on every build, with one
# stated exception: the detector's power table, which costs ~20s and is read
# out of demo/data/demo_set.json instead — the same table the narrated run
# already shows, so the wall and the run cannot disagree. A test recomputes one
# of its rows live and asserts it still matches.

# The two metrics the comparison runs on. Both are the pipeline's own outputs;
# neither is invented for the demo.
STAT_METRICS = [
    ("dominance", "דומיננטיות לקסיקון", "mean_dominance"),
    ("audience_p85", "אחוזון 85 של הקהל", "audience_p85"),
]


def _stat_constants() -> dict:
    """Iteration counts and seeds read off the signatures, never re-typed."""
    import inspect

    from demo.core import framing as fr

    boot = inspect.signature(fr.bootstrap_ci).parameters
    perm = inspect.signature(fr.detect_change_point).parameters
    return {
        "bootstrap_iterations": int(boot["iterations"].default),
        "bootstrap_seed": int(boot["seed"].default),
        "bootstrap_min_n": 3,
        "permutation_iterations": int(perm["iterations"].default),
        "min_segment": fr.MIN_SEGMENT,
        "min_cell_events": fr.MIN_CELL_EVENTS,
        "alpha": 0.05,
    }


def _bootstrap_p(values: list[float], iterations: int, seed: int) -> float | None:
    """Two-sided bootstrap p for 'the mean deviation is zero'.

    bootstrap_ci already answers this at 95%, but a CI cannot say how far past
    the line a result sits — and the multiplicity panel needs exactly that.
    Same resampling, same seed, so the p and the interval describe one draw.
    """
    import numpy as np

    if len(values) < 3:
        return None
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    draws = rng.choice(arr, (iterations, len(arr)), replace=True).mean(axis=1)
    return float(2 * min((draws <= 0).mean(), (draws >= 0).mean()))


def build_stats(conn: sqlite3.Connection) -> dict:
    import statistics

    import numpy as np

    from demo.core.framing import (
        Snapshot,
        bootstrap_ci,
        build_event_clusters,
        coverage_matrix,
        detect_change_point,
        outlet_deviation,
        sampling_curve,
        topic_framing_matrix,
    )

    consts = _stat_constants()
    snap = Snapshot()
    events = build_event_clusters(snap)
    articles = snap.articles()
    window_feats = snap.window_features()

    # 1. the naive number: each outlet's raw mean, over everything crawled.
    raw_snapshot: dict[str, list[float]] = {}
    for article_id, row in articles.items():
        feat = window_feats.get(article_id)
        if feat and feat["dom"] is not None:
            raw_snapshot.setdefault(row["source"], []).append(float(feat["dom"]))

    # 2. the same naive number restricted to the event versions, so the two
    #    methods are computed on exactly the same articles and the ranking
    #    they produce can be compared without a sampling excuse.
    metrics = []
    for key, label_he, attr in STAT_METRICS:
        raw_versions: dict[str, list[float]] = {}
        values, medians, deviations = [], [], []
        for event in events:
            observed = [(v.source, float(getattr(v, attr))) for v in event.versions
                        if getattr(v, attr) is not None]
            if len(observed) < 2:
                continue
            median = float(np.median([x for _, x in observed]))
            for source, value in observed:
                raw_versions.setdefault(source, []).append(value)
                values.append(value)
                medians.append(median)
                deviations.append(value - median)

        devs = outlet_deviation(events, key)
        rows = []
        for source, dev_values in sorted(devs.items(), key=lambda kv: -len(kv[1])):
            ci = bootstrap_ci(dev_values)
            raw = raw_versions.get(source, [])
            rows.append({
                "source": source,
                "source_he": source_he(source),
                "n": len(dev_values),
                "raw_mean": round(statistics.mean(raw), 4) if raw else None,
                "mean": round(ci[0], 5) if ci else None,
                "lo": round(ci[1], 5) if ci else None,
                "hi": round(ci[2], 5) if ci else None,
                "significant": bool(ci and (ci[1] > 0 or ci[2] < 0)),
                "p": (lambda v: round(v, 5) if v is not None else None)(
                    _bootstrap_p(dev_values, consts["bootstrap_iterations"],
                                 consts["bootstrap_seed"])),
            })

        total_var = float(np.var(values, ddof=1)) if len(values) > 1 else 0.0
        between = float(np.var(medians, ddof=1)) if len(medians) > 1 else 0.0
        within = float(np.var(deviations, ddof=1)) if len(deviations) > 1 else 0.0
        metrics.append({
            "key": key,
            "label_he": label_he,
            "n": len(values),
            "variance": {
                "total": round(total_var, 6),
                "between": round(between, 6),
                "within": round(within, 6),
                "between_share": round(between / total_var, 4) if total_var else None,
                "within_share": round(within / total_var, 4) if total_var else None,
            },
            "outlets": rows,
        })

    # 3. how the interval narrows as evidence accumulates
    devs = outlet_deviation(events, "dominance")
    curve_source = max(devs, key=lambda s: len(devs[s]))
    curve = [{"n": int(p["n"]), "mean": round(p["mean"], 5), "lo": round(p["lo"], 5),
              "hi": round(p["hi"], 5), "width": round(p["width"], 5)}
             for p in sampling_curve(devs[curve_source])]

    # 4. the beat-level matrix, including the cells we refuse to report
    cells_all, cells_meta = {}, []
    for key, label_he, _attr in STAT_METRICS:
        cells = topic_framing_matrix(events, key)
        rows = []
        for cell in sorted(cells.values(), key=lambda c: -c.n):
            rows.append({
                "source": cell.source,
                "source_he": source_he(cell.source),
                "topic_he": cell.topic_he,
                "n": cell.n,
                "mean": round(cell.ci[0], 5) if cell.ci else None,
                "lo": round(cell.ci[1], 5) if cell.ci else None,
                "hi": round(cell.ci[2], 5) if cell.ci else None,
                "usable": cell.usable,
                "significant": cell.significant,
                # a cell whose interval clears zero but whose n is below the
                # floor: the exact shape a false positive takes here
                "tempting": bool(cell.ci and not cell.usable
                                 and (cell.ci[1] > 0 or cell.ci[2] < 0)),
            })
        cells_all[key] = rows
        cells_meta.append({
            "key": key, "label_he": label_he, "total": len(rows),
            "usable": sum(1 for r in rows if r["usable"]),
            "significant": sum(1 for r in rows if r["significant"]),
            "tempting": sum(1 for r in rows if r["tempting"]),
        })

    # 5. the change-point scan, pooled per outlet
    scans = []
    for key, label_he, attr in STAT_METRICS:
        series: dict[str, list[tuple[str, float]]] = {}
        for event in events:
            observed = [(v.source, float(getattr(v, attr)), v.first_seen_at)
                        for v in event.versions if getattr(v, attr) is not None]
            if len(observed) < 2:
                continue
            median = float(np.median([x for _, x, _ in observed]))
            for source, value, stamp in observed:
                series.setdefault(source, []).append((stamp or "", value - median))
        for source, points in sorted(series.items(), key=lambda kv: -len(kv[1])):
            found = detect_change_point(points)
            scans.append({
                "metric": key, "metric_he": label_he,
                "source": source, "source_he": source_he(source),
                "n": len(points),
                "too_short": found is None,
                "at": found.at[:16] if found else None,
                "before": round(found.before_mean, 5) if found else None,
                "after": round(found.after_mean, 5) if found else None,
                "shift": round(found.shift, 5) if found else None,
                "statistic": round(found.statistic, 4) if found else None,
                "p": round(found.p_value, 4) if found else None,
                "detected": bool(found and found.detected),
            })

    # 6. the arithmetic of running all of the above at once
    ci_tests = sum(1 for m in metrics for r in m["outlets"] if r["p"] is not None)
    cell_tests = sum(m["usable"] for m in cells_meta)
    scan_tests = sum(1 for s in scans if not s["too_short"])
    tests = ci_tests + cell_tests + scan_tests
    alpha = consts["alpha"]
    bonferroni = alpha / max(tests, 1)
    # `direction` travels with each hit so the closing sentence on the wall is
    # written from the data rather than from whatever this snapshot happened to
    # show when the panel was authored.
    hits = [
        *[{"what": f"{r['source_he']} · {m['label_he']}", "p": r["p"],
           "source_he": r["source_he"], "metric_he": m["label_he"],
           "direction": "below" if (r["mean"] or 0) < 0 else "above"}
          for m in metrics for r in m["outlets"]
          if r["p"] is not None and r["p"] < alpha],
        *[{"what": f"{s['source_he']} · {s['metric_he']} · נקודת שינוי", "p": s["p"],
           "source_he": s["source_he"], "metric_he": s["metric_he"],
           "direction": "shift"}
          for s in scans if s["detected"]],
    ]
    multiplicity = {
        "ci_tests": ci_tests,
        "cell_tests": cell_tests,
        "scan_tests": scan_tests,
        "tests": tests,
        "alpha": alpha,
        "bonferroni": round(bonferroni, 5),
        "expected_false": round(tests * alpha, 2),
        "hits": sorted(hits, key=lambda h: h["p"]),
        "survivors": [h for h in sorted(hits, key=lambda h: h["p"])
                      if h["p"] < bonferroni],
    }

    # 7. power — read, not recomputed. See the note at the top of this section.
    power = {"source": "demo/data/demo_set.json", "rows": [], "iterations": 150}
    demo_set = config.DATA_DIR / "demo_set.json"
    if demo_set.exists():
        profile = json.loads(demo_set.read_text(encoding="utf-8")).get("profile", {})
        power["rows"] = [
            {"n": r["n"],
             "power_1sd": round(r["power_1sd"], 4),
             "power_half_sd": round(r["power_half_sd"], 4)}
            for r in profile.get("power_table", [])
        ]

    # 8. how the events are shaped — this is what limits everything above.
    # In a two-version event the median IS the midpoint, so the two deviations
    # are mechanically +d/2 and -d/2: not two independent observations, one
    # comparison written down twice.
    from collections import Counter
    from itertools import combinations

    sizes = Counter(len(e.versions) for e in events)
    co: Counter = Counter()
    for event in events:
        for a, b in combinations(sorted({v.source for v in event.versions}), 2):
            co[(a, b)] += 1
    two_version = [e for e in events if len(e.versions) == 2]
    top_pair = co.most_common(1)[0] if co else (("", ""), 0)
    pairing = {
        "sizes": [{"versions": k, "events": v} for k, v in sorted(sizes.items())],
        "two_version": len(two_version),
        "events": len(events),
        "pairs": [{"a": a, "a_he": source_he(a), "b": b, "b_he": source_he(b),
                   "events": n} for (a, b), n in co.most_common()],
        "top_pair_two_version": sum(
            1 for e in two_version
            if {v.source for v in e.versions} == set(top_pair[0])),
    }

    in_snapshot: dict[str, int] = {}
    for row in articles.values():
        in_snapshot[row["source"]] = in_snapshot.get(row["source"], 0) + 1
    coverage = [
        {"source": s, "source_he": source_he(s), "covered": c["covered"],
         "total_events": c["total_events"], "share": round(c["share"], 4),
         "in_snapshot": in_snapshot.get(s, 0)}
        for s, c in sorted(coverage_matrix(events, in_snapshot).items(),
                           key=lambda kv: -kv[1]["covered"])
    ]

    return {
        "constants": consts,
        "events": len(events),
        "raw_snapshot": [
            {"source": s, "source_he": source_he(s), "n": len(v),
             "mean": round(statistics.mean(v), 4)}
            for s, v in sorted(raw_snapshot.items(), key=lambda kv: -len(kv[1]))
        ],
        "metrics": metrics,
        "curve": {"source": curve_source, "source_he": source_he(curve_source),
                  "points": curve},
        "cells_meta": cells_meta,
        "cells": cells_all,
        "scans": scans,
        "multiplicity": multiplicity,
        "power": power,
        "pairing": pairing,
        "coverage": coverage,
    }


# ── the token economy ───────────────────────────────────────────────────

USAGE_PATH = config.DATA_DIR / "llm_usage.json"
REPAIR_LOG_PATH = config.DATA_DIR / "repair_log.json"

# The show-day projection's only assumption, kept here so it is one number in
# one place rather than a sentence on a slide: an exhibition shift and how
# often the narrated loop comes around.
SHOW_HOURS = 8
LOOP_MINUTES = 5


def _usd(prompt_tokens: float, completion_tokens: float) -> float:
    """The one pricing formula, shared with _CachedLLM.cost_usd."""
    return (prompt_tokens * config.PRICE_PROMPT_PER_M
            + completion_tokens * config.PRICE_COMPLETION_PER_M) / 1_000_000


def _share(part: float, whole: float) -> float:
    return round(part / whole, 4) if whole else 0.0


def build_economy(conn: sqlite3.Connection, facts: dict) -> dict:
    """What the model layer cost, and — mostly — where no model was used.

    Two things are measured rather than assumed. First, the prompts: every one
    of the cached calls is reconstructed from the same snapshot and the same
    prompt builders the extractors use, so the character counts on screen are
    the characters that were actually sent. Second, the exchange rate: the
    usage file holds the true billed token counts, so dividing real chars by
    real tokens gives this corpus's Hebrew chars-per-token instead of a
    remembered rule of thumb. Everything derived from that rate is labelled
    an estimate, and the output side is measured separately as a check on it.

    Counts for the deterministic stages are taken from the already-built facts
    rather than recounted, so this tile cannot disagree with the six before it.
    """
    import statistics

    from demo.core.framing import (CONTRAST_LEAD_CHARS, CONTRAST_MAX_TOKENS,
                                   CONTRAST_SYSTEM, EXTRACT_LEAD_CHARS,
                                   FRAMING_MAX_TOKENS, FRAMING_SYSTEM,
                                   ContrastExtractor, FramingExtractor,
                                   Snapshot, build_contrast_prompt,
                                   build_event_clusters)
    from demo.snapshot.prepare_demo import CONTRAST_VERSIONS
    from src.nlp.categories import DEFAULT_MODEL as CLASSIFY_MODEL
    from src.nlp.classify import _build_system_prompt as classify_system
    from src.nlp.truncate import MAX_TEXT_CHARS, truncate_for_classification

    usage = json.loads(USAGE_PATH.read_text(encoding="utf-8"))
    prompt_tokens = int(usage["prompt_tokens"])
    completion_tokens = int(usage["completion_tokens"])
    total_tokens = prompt_tokens + completion_tokens

    snap = Snapshot()
    articles = snap.articles()
    events = build_event_clusters(snap)
    framer, contraster = FramingExtractor(), ContrastExtractor()
    by_event = {e.event_id: e for e in events}

    # ---- rebuild every prompt that was actually sent
    framing_user: list[int] = []
    for article_id in framer.cache:
        row = articles.get(article_id)
        if row is None:
            continue
        framing_user.append(len(
            f"כותרת: {row['title']}\nפתיח: {(row['text'] or '')[:EXTRACT_LEAD_CHARS]}"))

    contrast_user: list[int] = []
    versions_per_call: dict[int, int] = {}
    for event_id in contraster.cache:
        event = by_event.get(event_id)
        if event is None:
            continue
        versions = [(v.source, v.title, articles[v.article_id]["text"])
                    for v in event.versions[:CONTRAST_VERSIONS]]
        contrast_user.append(len(build_contrast_prompt(versions)))
        versions_per_call[len(versions)] = versions_per_call.get(len(versions), 0) + 1

    f_sys, c_sys = len(FRAMING_SYSTEM), len(CONTRAST_SYSTEM)
    f_calls, c_calls = len(framing_user), len(contrast_user)
    f_chars = sum(framing_user) + f_sys * f_calls
    c_chars = sum(contrast_user) + c_sys * c_calls
    prompt_chars = f_chars + c_chars
    system_chars = f_sys * f_calls + c_sys * c_calls
    # Published at the precision the wall prints, and then used at that
    # precision for everything downstream: a visitor who recomputes an
    # estimate from the number on screen must land on the number on screen.
    chars_per_token = round(prompt_chars / prompt_tokens, 3) if prompt_tokens else 0.0

    # The output side, measured independently: what the cache holds is the
    # parsed answer re-serialised, so it is close to but not identical with
    # the raw response — which is exactly why the two rates are shown apart
    # instead of averaged into one confident number.
    f_out = sum(len(json.dumps(v, ensure_ascii=False)) for v in framer.cache.values())
    c_out = sum(len(json.dumps(v, ensure_ascii=False)) for v in contraster.cache.values())
    out_chars = f_out + c_out
    out_per_token = (round(out_chars / completion_tokens, 3)
                     if completion_tokens else 0.0)

    rate = {
        "prompt_chars": prompt_chars,
        "prompt_tokens": prompt_tokens,
        "chars_per_token": chars_per_token,
        "output_chars": out_chars,
        "completion_tokens": completion_tokens,
        "output_chars_per_token": out_per_token,
        "gap": round(abs(chars_per_token - out_per_token) / chars_per_token, 4)
        if chars_per_token else 0.0,
        "examples": [
            {"label_he": "הנחיית המערכת של המסגור", "chars": f_sys},
            {"label_he": "פתיח מלא, בגבול החיתוך", "chars": EXTRACT_LEAD_CHARS},
            {"label_he": "קריאת מסגור טיפוסית, הכל כלול",
             "chars": f_sys + int(statistics.median(framing_user))
             if framing_user else f_sys},
        ],
    }

    for example in rate["examples"]:
        example["tokens"] = (round(example["chars"] / chars_per_token)
                             if chars_per_token else 0)

    # ---- prompt anatomy: what fraction of the bill is instructions
    prompt_facts = {
        "framing": {
            "calls": f_calls,
            "system_chars": f_sys,
            "user_median": round(statistics.median(framing_user), 1) if framing_user else 0,
            "user_mean": round(statistics.mean(framing_user), 1) if framing_user else 0,
            "total_chars": f_chars,
            "system_share": _share(f_sys * f_calls, f_chars),
            "max_tokens": FRAMING_MAX_TOKENS,
        },
        "contrast": {
            "calls": c_calls,
            "system_chars": c_sys,
            "user_median": round(statistics.median(contrast_user), 1) if contrast_user else 0,
            "user_mean": round(statistics.mean(contrast_user), 1) if contrast_user else 0,
            "total_chars": c_chars,
            "system_share": _share(c_sys * c_calls, c_chars),
            "max_tokens": CONTRAST_MAX_TOKENS,
            "lead_chars": CONTRAST_LEAD_CHARS,
            "versions": [{"versions": k, "events": v}
                         for k, v in sorted(versions_per_call.items())],
        },
        "system_chars_total": system_chars,
        "system_tokens": round(system_chars / chars_per_token) if chars_per_token else 0,
        "system_share_of_prompt": _share(system_chars, prompt_chars),
        "framing_share": _share(f_chars, prompt_chars),
    }

    # ---- what the 500-char cap kept off the bill
    version_chars = [len(articles[v.article_id]["text"] or "")
                     for e in events for v in e.versions]
    dropped = sum(max(0, n - EXTRACT_LEAD_CHARS) for n in version_chars)
    dropped_tokens = round(dropped / chars_per_token) if chars_per_token else 0
    truncation = {
        "lead_chars": EXTRACT_LEAD_CHARS,
        "versions": len(version_chars),
        "median_chars": round(statistics.median(version_chars), 1) if version_chars else 0,
        "over_cap": sum(1 for n in version_chars if n > EXTRACT_LEAD_CHARS),
        "sent_chars": sum(min(n, EXTRACT_LEAD_CHARS) for n in version_chars),
        "dropped_chars": dropped,
        "dropped_tokens": dropped_tokens,
        "dropped_usd": round(_usd(dropped_tokens, 0), 6),
        "would_be_prompt_tokens": prompt_tokens + dropped_tokens,
        "median_share_sent": round(statistics.median(
            [min(n, EXTRACT_LEAD_CHARS) / n for n in version_chars if n]), 4)
        if version_chars else 0.0,
    }

    # ---- the bill, and the two ways to cut it
    # rounded first, then summed, so the two figures on screen add up to the
    # third one on screen rather than to an invisible extra digit
    prompt_usd = round(_usd(prompt_tokens, 0), 6)
    completion_usd = round(_usd(0, completion_tokens), 6)
    bill = {
        "calls": int(usage["calls"]),
        "cached_outputs": int(usage.get("cached_outputs", 0)),
        "covered": int(usage["calls"]) == len(framer.cache) + len(contraster.cache),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "prompt_usd": prompt_usd,
        "completion_usd": completion_usd,
        "usd": round(prompt_usd + completion_usd, 6),
        "reported_usd": round(float(usage["usd"]), 6),
        "completion_per_call": round(completion_tokens / int(usage["calls"]), 1)
        if usage["calls"] else 0.0,
        "completion_token_share": _share(completion_tokens, total_tokens),
        "completion_bill_share": _share(completion_usd, prompt_usd + completion_usd),
        "price_prompt_per_m": config.PRICE_PROMPT_PER_M,
        "price_completion_per_m": config.PRICE_COMPLETION_PER_M,
    }

    # The dollar split between the two call types is NOT in the usage file —
    # it holds one total. Splitting prompt tokens by measured characters is
    # exact up to the tokenizer; splitting completion tokens by cached output
    # characters assumes the same rate on both sides, which is the assumption
    # the rate panel puts a number on. Marked derived, not measured.
    split = []
    for key, label, calls, chars, out in (
        ("framing", "חילוץ מסגור", f_calls, f_chars, f_out),
        ("contrast", "ניתוח קונטרסטיבי", c_calls, c_chars, c_out),
    ):
        p_tok = round(prompt_tokens * _share(chars, prompt_chars))
        c_tok = round(completion_tokens * _share(out, out_chars))
        usd = _usd(p_tok, c_tok)
        split.append({
            "key": key, "label_he": label, "calls": calls,
            "prompt_tokens": p_tok, "completion_tokens": c_tok,
            "usd": round(usd, 6),
            "per_call_usd": round(usd / calls, 6) if calls else 0.0,
            "derived": True,
        })

    per_unit = [
        {"label_he": "לאירוע חוצה־ערוצים", "n": len(events),
         "usd": round(bill["usd"] / len(events), 6) if events else 0.0},
        {"label_he": "לגרסה שנותחה", "n": len(framer.cache),
         "usd": round(bill["usd"] / len(framer.cache), 6) if framer.cache else 0.0},
        {"label_he": "לכתבה בתמונת המצב", "n": facts["corpus"]["articles"],
         "usd": round(bill["usd"] / facts["corpus"]["articles"], 6)},
        {"label_he": "לתגובה שנוקדה", "n": facts["comments"]["total"], "usd": 0.0},
    ]

    # ---- the stages, and how many of them need a model at all
    verifier = facts["framing"]["verifier"]
    stages = [
        {"key": "crawl", "label_he": "איסוף", "kind": "free",
         "n": facts["corpus"]["articles"], "unit_he": "כתבות",
         "detail_he": "מוריד דפים, מחלץ טקסט, ומזהה כפילויות לפי sha256"},
        {"key": "windows", "label_he": "חלונות", "kind": "free",
         "n": facts["windows"]["total"], "unit_he": "חלונות",
         "detail_he": "מפצל למשפטים לפי חוקים, וחותך כל חלון ב־60 טוקנים"},
        {"key": "comments", "label_he": "תגובות", "kind": "free",
         "n": facts["comments"]["total"], "unit_he": "תגובות",
         "detail_he": "סופר בכל תגובה מילים מהמילון. חיפוש ברשימה, לא מודל"},
        {"key": "lexicon", "label_he": "מילון", "kind": "free",
         "n": facts["lexicon"]["article_expanded"], "unit_he": "צורות",
         "detail_he": "הורחב פעם אחת מראש. בזמן ריצה נשאלת רק שאלת שייכות"},
        {"key": "embed", "label_he": "וקטורים", "kind": "local",
         "n": facts["retrieval"]["vectors"], "unit_he": "וקטורים",
         "detail_he": f"{config.EMBED_MODEL} רץ על המחשב הזה. מודל אמיתי, בלי חשבון"},
        {"key": "cluster", "label_he": "אשכול אירועים", "kind": "free",
         "n": facts["retrieval"]["events"]["total"], "unit_he": "אירועים",
         "detail_he": "מודד זווית בין וקטורים ומשווה לסף. אריתמטיקה בלבד"},
        {"key": "framing", "label_he": "חילוץ מסגור", "kind": "paid",
         "n": f_calls, "unit_he": "קריאות",
         "detail_he": "שואל מי מוצג כמבצע ולמי מיוחסת אחריות. לקוד אין תשובה"},
        {"key": "contrast", "label_he": "ניתוח קונטרסטיבי", "kind": "paid",
         "n": c_calls, "unit_he": "קריאות",
         "detail_he": "שואל מה ייחודי בכל גרסה. גרסה בודדת לא עונה על זה"},
        {"key": "verify", "label_he": "אימות", "kind": "free",
         "n": verifier["terms_total"] + verifier["quotes_total"], "unit_he": "בדיקות",
         "detail_he": "מחפש כל ביטוי וכל ציטוט בטקסט המקורי. השוואת מחרוזות"},
        {"key": "stats", "label_he": "סטטיסטיקה", "kind": "free",
         "n": facts["stats"]["multiplicity"]["tests"], "unit_he": "בדיקות",
         "detail_he": "דגימות חוזרות, ערבוב תוויות, תיקון לריבוי בדיקות. numpy"},
    ]
    for stage in stages:
        stage["usd"] = next((s["usd"] for s in split if s["key"] == stage["key"]), 0.0)

    # ---- the cache: what a show day would cost if it were not there
    demo_set = json.loads(config.DEMO_SET_PATH.read_text(encoding="utf-8"))
    showcases = demo_set.get("showcase_events") or []
    per_loop_framing = (statistics.mean(len(s["versions"]) for s in showcases)
                        if showcases else 0.0)
    f_per_call = next(s["per_call_usd"] for s in split if s["key"] == "framing")
    c_per_call = next(s["per_call_usd"] for s in split if s["key"] == "contrast")
    loop_usd = per_loop_framing * f_per_call + c_per_call
    loops = int(SHOW_HOURS * 60 / LOOP_MINUTES)
    cache = {
        "entries": len(framer.cache) + len(contraster.cache),
        "framing": len(framer.cache),
        "contrast": len(contraster.cache),
        "showtime_calls": 0,
        "showcases": len(showcases),
        "calls_per_loop": round(per_loop_framing + 1, 1),
        "loop_usd": round(loop_usd, 6),
        "show_hours": SHOW_HOURS,
        "loop_minutes": LOOP_MINUTES,
        "loops": loops,
        "day_usd": round(loop_usd * loops, 4),
        "day_calls": round((per_loop_framing + 1) * loops),
    }

    # ---- the strawman, costed two ways
    article_chars = conn.execute(
        "SELECT COALESCE(SUM(LENGTH(text)), 0) FROM articles").fetchone()[0]
    comment_chars = conn.execute(
        "SELECT COALESCE(SUM(LENGTH(text)), 0) FROM comments").fetchone()[0]
    n_articles = facts["corpus"]["articles"]
    n_comments = facts["comments"]["total"]
    all_calls = n_articles + n_comments
    straw_system = f_sys * all_calls
    straw_prompt = round((article_chars + comment_chars + straw_system) / chars_per_token) \
        if chars_per_token else 0
    per_call_completion = completion_tokens / int(usage["calls"]) if usage["calls"] else 0
    straw_completion = round(all_calls * per_call_completion)
    straw_usd = _usd(straw_prompt, straw_completion)

    # the coarser estimate the narrated run puts on screen, kept here so the
    # two numbers on the wall are shown together instead of contradicting
    scene_articles = facts["retrieval"]["vectors"]
    scene_usd = _usd(scene_articles * 900, scene_articles * 150)

    span = conn.execute(
        "SELECT MIN(first_seen_at), MAX(first_seen_at) FROM articles").fetchone()
    days = _snapshot_days(span)
    strawman = {
        "articles": n_articles, "article_chars": article_chars,
        "comments": n_comments, "comment_chars": comment_chars,
        "calls": all_calls,
        "system_chars": straw_system,
        "system_share": _share(straw_system, article_chars + comment_chars + straw_system),
        "prompt_tokens": straw_prompt,
        "completion_tokens": straw_completion,
        "per_call_completion": round(per_call_completion, 1),
        "usd": round(straw_usd, 4),
        "ratio": round(straw_usd / bill["usd"], 1) if bill["usd"] else 0.0,
        "days": days,
        "month_usd": round(straw_usd * 30 / days, 2) if days else 0.0,
        "agents_month_usd": round(bill["usd"] * 30 / days, 3) if days else 0.0,
        "scene": {"articles": scene_articles, "prompt_per_article": 900,
                  "completion_per_article": 150, "usd": round(scene_usd, 4)},
    }

    # ---- what this bill does not include, with the big one measured
    classify_sys = classify_system()
    classify_chars = 0
    labeled = 0
    for row in conn.execute("SELECT text, primary_category FROM articles"):
        classify_chars += len(classify_sys) + len(truncate_for_classification(row[0] or ""))
        labeled += bool(row[1])
    classify_tokens = round(classify_chars / chars_per_token) if chars_per_token else 0
    classify_completion = round(n_articles * per_call_completion)
    excluded = [
        {"key": "classify", "label_he": "סיווג קטגוריה בפייפליין",
         "detail_he": f"{CLASSIFY_MODEL} מקבל כותרת ו־{MAX_TEXT_CHARS} תווים ראשונים "
                      f"מכל כתבה. רץ בענן כל 6 שעות, על כל כתבה שנאספה",
         "n": labeled, "unit_he": "כתבות שכבר תויגו",
         "prompt_tokens": classify_tokens,
         "usd": round(_usd(classify_tokens, classify_completion), 4),
         "estimate": True},
        {"key": "enrich", "label_he": "סיכום והערכת הטיה",
         "detail_he": "נוצרים לפי בקשה מהאתר ונשמרים. הם לא רצים בלוח זמנים, "
                      "ולכן אין להם חשבון קבוע",
         "n": None, "unit_he": None, "prompt_tokens": None, "usd": None,
         "estimate": False},
        {"key": "embed", "label_he": "זמן המעבד של מודל הווקטורים",
         "detail_he": f"{config.EMBED_MODEL} לא צורך טוקנים. הוא כן צורך חשמל וזמן, "
                      "ואלה לא נספרים בשום שורה",
         "n": facts["retrieval"]["vectors"], "unit_he": "וקטורים",
         "prompt_tokens": None, "usd": None, "estimate": False},
        {"key": "dev", "label_he": "ריצות פיתוח שנזרקו",
         "detail_he": "קובץ השימוש מצטבר על פני ריצות הכנה. ניסויי הנחיה שנמחקו "
                      "לא נספרו, והמספר מתאר את המטמון שנשאר",
         "n": None, "unit_he": None, "prompt_tokens": None, "usd": None,
         "estimate": False},
    ]

    return {
        "constants": {
            "model": facts["framing"]["model"],
            "temperature": facts["framing"]["temperature"],
            "embed_model": config.EMBED_MODEL,
            "price_prompt_per_m": config.PRICE_PROMPT_PER_M,
            "price_completion_per_m": config.PRICE_COMPLETION_PER_M,
            "lead_chars": EXTRACT_LEAD_CHARS,
            "contrast_lead_chars": CONTRAST_LEAD_CHARS,
            "contrast_versions": CONTRAST_VERSIONS,
            "framing_max_tokens": FRAMING_MAX_TOKENS,
            "contrast_max_tokens": CONTRAST_MAX_TOKENS,
        },
        "bill": bill,
        "stages": stages,
        "rate": rate,
        "prompt": prompt_facts,
        "truncation": truncation,
        "split": split,
        "per_unit": per_unit,
        "cache": cache,
        "strawman": strawman,
        "excluded": excluded,
    }


def _snapshot_days(span) -> float:
    """Calendar days the snapshot spans — the denominator of any rate here."""
    from datetime import datetime

    try:
        start = datetime.fromisoformat(span[0])
        end = datetime.fromisoformat(span[1])
    except (TypeError, ValueError):
        return 0.0
    return round((end - start).total_seconds() / 86400, 2)


def build_repair(facts: dict) -> dict:
    """The repair loop: what the verifier's deletions cost, and what came back.

    The verifier is deterministic and only ever deletes, so its rejection rate
    is also a loss rate — every rejected quote is a sentence that reaches the
    screen without evidence. This tile measures the recovery path, including
    the two outcomes that are easy to conflate: a quote that now grounds, and a
    quote the model honestly refused to invent. Only the first is a recovery.

    Everything here is read off demo/data/repair_log.json, which is written by
    demo/snapshot/run_repair.py at prepare time. No model is called.
    """
    from demo.core.framing import (CONTRAST_LEAD_CHARS, EXTRACT_LEAD_CHARS,
                                   MAX_REPAIR_ATTEMPTS,
                                   REPAIR_ATTEMPTS_MEASURED,
                                   REPAIR_MAX_TOKENS, ContrastExtractor,
                                   Snapshot, _normalise, build_event_clusters)
    from demo.snapshot.prepare_demo import CONTRAST_VERSIONS

    log = json.loads(REPAIR_LOG_PATH.read_text(encoding="utf-8"))
    attempts = log["attempts"]

    # ---- the cap, measured rather than guessed
    by_attempt: dict[int, dict[str, int]] = {}
    for row in attempts:
        slot = by_attempt.setdefault(row["attempt"], {"calls": 0, "accepted": 0})
        slot["calls"] += 1
        slot["accepted"] += int(row["accepted"])
    attempt_rows = [
        {
            "n": n,
            "calls": slot["calls"],
            "accepted": slot["accepted"],
            "detail_he": (
                f"תיקן {slot['accepted']} מתוך {slot['calls']}"
                if slot["accepted"]
                else f"תיקן 0 מתוך {slot['calls']}. זה מה שעלה לדעת"
            ),
        }
        for n, slot in sorted(by_attempt.items())
    ]

    # ---- the bill, and what it is next to
    layer_usd = round(facts["economy"]["bill"]["usd"], 6)
    usd = round(log["usd"], 6)
    entered = log["items_entered"]

    # ---- one real before/after, chosen for being legible rather than flattering
    example = _repair_example(ContrastExtractor(), Snapshot(),
                              build_event_clusters, CONTRAST_VERSIONS,
                              _normalise, EXTRACT_LEAD_CHARS)

    # ---- what reaches the three stories on the wall
    demo_set = json.loads(config.DEMO_SET_PATH.read_text(encoding="utf-8"))
    on_stage = sum(len(s.get("contrast_repaired") or [])
                   for s in demo_set["showcase_events"])

    verifier = facts["framing"]["verifier"]
    return {
        "constants": {
            "model": facts["economy"]["constants"]["model"],
            "max_attempts": MAX_REPAIR_ATTEMPTS,
            "max_attempts_measured": REPAIR_ATTEMPTS_MEASURED,
            "max_tokens": REPAIR_MAX_TOKENS,
            "lead_chars": EXTRACT_LEAD_CHARS,
            "contrast_lead_chars": CONTRAST_LEAD_CHARS,
        },
        "verifier": {
            "quotes_total": verifier["quotes_total"],
            "quotes_rejected": verifier["quotes_rejected"],
            "terms_total": verifier["terms_total"],
            "terms_rejected": verifier["terms_rejected"],
        },
        "loop": {
            "candidates_framing": log["candidates"]["framing"],
            "candidates_contrast": log["candidates"]["contrast"],
            "entered": entered,
            "calls": log["calls"],
            "fixed_fully": log["fixed_fully"],
            "unchanged": log["unchanged"],
            "violations_before": log["violations_before"],
            "violations_after": log["violations_after"],
            "regrounded": log["quotes_regrounded"],
            "nulled": log["quotes_nulled_honestly"],
            "destroyed": log["valid_quotes_destroyed"],
        },
        "attempts": attempt_rows,
        "bill": {
            "prompt_tokens": log["prompt_tokens"],
            "completion_tokens": log["completion_tokens"],
            "usd": usd,
            "per_item_usd": round(usd / entered, 8) if entered else 0.0,
            "layer_usd": layer_usd,
            "total_usd": round(layer_usd + usd, 6),
            "share_of_layer": round(usd / layer_usd, 4) if layer_usd else 0.0,
        },
        "guards": [
            {
                "key": "verifier_judges",
                "title_he": "אותו מאמת שופט גם את התיקון",
                "detail_he": ("המודל לא מאשר את עצמו. תיקון עובר את אותה בדיקת "
                              "העתקה מילה במילה, ולכן לא יכול להלבין ציטוט מומצא."),
            },
            {
                "key": "same_window",
                "title_he": "התיקון מקבל את אותו חלון טקסט",
                "detail_he": (f"{CONTRAST_LEAD_CHARS} תווים, כמו הקריאה שנפסלה. "
                              "חלון רחב יותר היה מאשר ציטוט מטקסט שהקריאה "
                              "הראשונה לא ראתה."),
            },
            {
                "key": "no_regression",
                "title_he": "תיקון שמוחק ראיה נדחה",
                "detail_he": ("פחות הפרות זה לא מספיק — תשובה שכולה null גם היא "
                              "בלי הפרות. תיקון מתקבל רק אם מספר הציטוטים "
                              "המאומתים לא ירד."),
            },
            {
                "key": "fallback",
                "title_he": "בלי הלולאה חוזרים למצב הקודם",
                "detail_he": ("אין רשת או שהתיקון נכשל — הציטוט נשאר ריק, "
                              "בדיוק כמו לפני. אף פעם לא ציטוט שגוי."),
            },
        ],
        # The guard above exists because the first version of the loop did not
        # have it. Recorded here as a finding, not recomputed: the run that
        # produced it was discarded when the rule changed.
        "regression": {
            "destroyed_before_guard": 13,
            "destroyed_now": log["valid_quotes_destroyed"],
        },
        "stage": {"events": len(demo_set["showcase_events"]),
                  "recovered": on_stage},
        "example": example,
    }


def _repair_example(contraster, snap, cluster_fn, versions_cap, normalise,
                    lead_chars) -> dict | None:
    """A real rejected quote and the quote that replaced it.

    Preference goes to a repair that ends on sentence punctuation and is long
    enough to read as a quote: the model often fixes a stitched citation by
    truncating it to the verbatim prefix, and a fragment cut mid-word is a true
    example that teaches nobody anything from across a room.
    """
    cache_path = config.DATA_DIR / "repair_cache.json"
    if not cache_path.exists():
        return None
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    articles = snap.articles()
    events = {e.event_id: e for e in cluster_fn(snap)}
    best = None
    for key, entry in cache.items():
        if not key.startswith("contrast:"):
            continue
        event = events.get(key.split(":", 1)[1])
        original = contraster.cached(key.split(":", 1)[1])
        if event is None or original is None:
            continue
        hay = {v.source: normalise(f"{v.title} "
                                   f"{(articles[v.article_id]['text'] or '')[:lead_chars]}")
               for v in event.versions[:versions_cap]}
        before = {i.get("source"): i.get("evidence")
                  for i in original.get("per_source") or []}
        for item in entry["result"].get("per_source") or []:
            source, now = item.get("source"), item.get("evidence")
            was = before.get(source)
            if not was or not now or now == was:
                continue
            if normalise(now) not in hay.get(source, ""):
                continue
            if normalise(was) in hay.get(source, ""):
                continue
            score = (0 if now.rstrip()[-1:] in '."\'׳!?' else 1, -len(now))
            if best is None or score < best[0]:
                best = (score, {"source": source, "before": was, "after": now,
                                "headline": event.headline})
    return best[1] if best else None


def main() -> int:
    if not config.SQLITE_PATH.exists():
        print(f"missing snapshot: {config.SQLITE_PATH}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(config.SQLITE_PATH)
    try:
        articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        facts = {
            "corpus": {"articles": articles},
            "constants": build_constants(),
            "identity_example": build_identity_example(conn),
            "worked_example": build_worked_example(conn),
            "sources": build_sources(conn),
            "windows": build_windows(conn),
            "comments": build_comments(conn),
            "lexicon": build_lexicon(),
            "retrieval": build_retrieval(conn),
            "framing": build_framing(),
            "audience": build_audience(conn),
            "stats": build_stats(conn),
        }
        # last, and on purpose: the economy tile reports the deterministic
        # stages' own counts rather than recounting them, so it cannot claim
        # a corpus size the six tiles before it disagree with.
        facts["economy"] = build_economy(conn, facts)
        # after economy, because the repair tile reports its own bill as a
        # share of the model layer's — and that total is economy's to state.
        facts["repair"] = build_repair(facts)
    finally:
        conn.close()

    FACTS_PATH.write_text(json.dumps(facts, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    print(f"wrote {FACTS_PATH.relative_to(REPO_ROOT)}")
    print(f"  {articles} articles · {facts['windows']['total']} windows · "
          f"{facts['comments']['total']} comments")
    print(f"  {len(facts['sources'])} sources · "
          f"{facts['lexicon']['article_expanded']} expanded lexicon forms")
    ret = facts["retrieval"]
    print(f"  index {ret['vectors']}x{ret['dims']} · {ret['events']['total']} events · "
          f"keyword recall {ret['keyword']['found']}/{ret['keyword']['total']}")
    v = facts["framing"]["verifier"]
    print(f"  verifier: {v['terms_rejected']}/{v['terms_total']} terms and "
          f"{v['quotes_rejected']}/{v['quotes_total']} quotes rejected")
    a = facts["audience"]
    print(f"  audience: {a['comments']['zero_polar']}/{a['comments']['total']} comments "
          f"score 0 · like-weight inert on {a['weight']['inert']} · "
          f"hijacked {a['hijack']['hijacked']}/{a['hijack']['comparable']}")
    m = facts["stats"]["multiplicity"]
    print(f"  stats: {m['tests']} significance tests · {len(m['hits'])} below "
          f"{m['alpha']} · {len(m['survivors'])} survive Bonferroni "
          f"({m['bonferroni']})")
    e = facts["economy"]
    print(f"  economy: {e['bill']['calls']} paid calls · "
          f"{e['bill']['total_tokens']} tokens · ${e['bill']['usd']:.4f} · "
          f"{e['rate']['chars_per_token']} chars/token · "
          f"{sum(1 for s in e['stages'] if s['kind'] == 'paid')}/{len(e['stages'])} "
          f"stages paid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
