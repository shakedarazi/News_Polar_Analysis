"""Tests for shared, composable HTML article extraction tiers."""

import json

from src.crawling.extractors import (
    extract_article_paragraphs,
    extract_article_with_fallback,
    extract_json_ld,
    extract_json_ld_news_article,
    extract_og_description,
)

LONG_BODY = ("פסקה עם מספיק תוכן כדי לעבור את סף האורך המינימלי הנדרש לבדיקה. " * 3).strip()


def html_with_json_ld(body: str) -> str:
    return f"""
    <html><head>
      <script type="application/ld+json">
      {{"@type": "NewsArticle", "headline": "כותרת", "articleBody": {json.dumps(body)}}}
      </script>
      <meta property="og:description" content="תיאור קצר מהמטא שלא אמור להיבחר" />
    </head><body><h1>כותרת H1</h1>
      <article><p>{body}</p></article>
    </body></html>
    """


def html_without_json_ld(body: str, og_desc: str = "") -> str:
    og_tag = f'<meta property="og:description" content="{og_desc}" />' if og_desc else ""
    return f"""
    <html><head>{og_tag}</head>
    <body><h1>כותרת H1</h1>
      <article><p>{body}</p></article>
    </body></html>
    """


def test_extract_json_ld_ignores_meta_description():
    title, text = extract_json_ld(html_with_json_ld(LONG_BODY))
    assert text == LONG_BODY
    assert "תיאור קצר" not in text


def test_extract_json_ld_returns_empty_when_absent():
    title, text = extract_json_ld(html_without_json_ld(LONG_BODY))
    assert text == ""


def test_extract_og_description_ignores_json_ld():
    html = html_with_json_ld(LONG_BODY)
    title, text = extract_og_description(html, min_len=10)
    assert "תיאור קצר" in text
    assert text != LONG_BODY


def test_extract_article_paragraphs_uses_first_matching_selector():
    html = html_without_json_ld(LONG_BODY)
    title, text = extract_article_paragraphs(html, ["article p"])
    assert text == LONG_BODY
    assert title == "כותרת H1"


def test_json_ld_news_article_composition_unchanged():
    """extract_json_ld_news_article stays JSON-LD-or-og:description, for
    callers not yet split into a 3-tier chain."""
    html = html_without_json_ld("", og_desc=LONG_BODY[:150])
    title, text = extract_json_ld_news_article(html)
    assert text == LONG_BODY[:150]


def test_fallback_chain_prefers_json_ld_first():
    html = html_with_json_ld(LONG_BODY)
    title, text = extract_article_with_fallback(html, ["article p"])
    assert text == LONG_BODY


def test_fallback_chain_uses_dom_when_json_ld_missing():
    html = html_without_json_ld(LONG_BODY, og_desc="תיאור קצר מדי")
    title, text = extract_article_with_fallback(html, ["article p"])
    assert text == LONG_BODY


def test_fallback_chain_uses_og_description_when_json_ld_and_dom_missing():
    html = f"""
    <html><head>
      <meta property="og:description" content="{LONG_BODY}" />
    </head><body><h1>כותרת H1</h1></body></html>
    """
    title, text = extract_article_with_fallback(html, ["article p"])
    assert text == LONG_BODY
    assert title == "כותרת H1"


def test_fallback_chain_returns_empty_when_nothing_matches():
    html = "<html><body><h1>כותרת H1</h1><p>קצר מדי</p></body></html>"
    title, text = extract_article_with_fallback(html, ["article p"])
    assert text == ""
