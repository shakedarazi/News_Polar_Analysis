"""News article categories for AI labeling."""

from __future__ import annotations

import os

CATEGORIES: tuple[str, ...] = (
    "פוליטיקה",
    "ביטחון",
    "בידור",
    "כלכלה",
    "ספורט",
    "חברה",
    "טכנולוגיה",
    "בינלאומי",
    "אחר",
)

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "פוליטיקה": "ממשלה, כנסת, בחירות, מפלגות, מדיניות פנים, שחיתות פוליטית",
    "ביטחון": "צבא, משטרה, טרור, מלחמה, ביטחון לאומי, חטיפות, התקפות",
    "בידור": "סלבס, טלוויזיה, מוזיקה, קולנוע, תרבות פופולרית",
    "כלכלה": "בורסה, מחירים, תעסוקה, עסקים, מיסים, בנקים",
    "ספורט": "כדורגל, כדורסל, אולימפיאדה, קבוצות, שחקנים",
    "חברה": "חינוך, בריאות, רווחה, דת, מגזרים, אירועי חיים",
    "טכנולוגיה": "סטארטאפים, AI, מחשבים, אפליקציות, סייבר",
    "בינלאומי": "חדשות מחוץ לישראל, דיפלומטיה, מלחמות בעולם",
    "אחר": "כתבות שלא מתאימות בבירור לאף קטגוריה אחרת",
}

# User-facing AI (summary / bias / Q&A) — official OpenAI model id.
# Classify uses OPENAI_INGESTION_MODEL via src.nlp.openai_config instead.
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
