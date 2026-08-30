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

    from demo.core.framing import (CONTRAST_SYSTEM, EXTRACT_LEAD_CHARS,
                                   FRAMING_KEYS, FRAMING_SYSTEM,
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
        "max_tokens": {"framing": 260, "contrast": 700},
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
        }
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
