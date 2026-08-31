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
    a = facts["audience"]
    print(f"  audience: {a['comments']['zero_polar']}/{a['comments']['total']} comments "
          f"score 0 · like-weight inert on {a['weight']['inert']} · "
          f"hijacked {a['hijack']['hijacked']}/{a['hijack']['comparable']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
