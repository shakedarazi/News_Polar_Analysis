"""Tests for ynet article extraction."""

import json

from src.crawling.sources.ynet import extract_ynet_article


SAMPLE_BODY = "פסקה ראשונה של הכתבה. " + "מילים נוספות " * 30
SAMPLE_HTML = f"""
<html>
<head>
  <meta property="og:title" content="כותרת מטא" />
  <script type="application/ld+json">
  {{
    "@type": "NewsArticle",
    "headline": "כותרת JSON",
    "articleBody": {json.dumps(SAMPLE_BODY)}
  }}
  </script>
</head>
<body>
  <h1 class="mainTitle">כותרת H1</h1>
  <div class="article-body">
    <div data-contents="true">
      <span data-text="true">טקסט שלא אמור להיקרא</span>
    </div>
  </div>
</body>
</html>
"""


def test_extract_prefers_json_ld_over_draftjs():
    title, text = extract_ynet_article(SAMPLE_HTML)
    assert title == "כותרת H1"
    assert "פסקה ראשונה של הכתבה" in text
    assert "טקסט שלא אמור להיקרא" not in text


def test_extract_draftjs_fallback():
    html = """
    <html><body>
      <h1>כותרת</h1>
      <div class="article-body">
        <span data-text="true">פסקה א.</span>
        <span data-text="true">פסקה ב עם מספיק טקסט כדי לעבור את סף האורך המינימלי.</span>
      </div>
    </body></html>
    """
    title, text = extract_ynet_article(html)
    assert title == "כותרת"
    assert "פסקה א." in text
    assert "פסקה ב" in text


def test_extract_og_description_fallback_when_json_ld_and_draftjs_missing():
    og_desc = "תיאור מהמטא " + "עם מספיק תוכן " * 10
    html = f"""
    <html><head>
      <meta property="og:description" content="{og_desc}" />
    </head><body>
      <h1>כותרת</h1>
    </body></html>
    """
    title, text = extract_ynet_article(html)
    assert title == "כותרת"
    assert text == og_desc.strip()
