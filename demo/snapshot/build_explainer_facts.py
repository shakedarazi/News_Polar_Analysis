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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
