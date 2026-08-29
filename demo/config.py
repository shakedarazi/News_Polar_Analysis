"""Demo layer configuration — paths, roster, pacing. No pipeline imports."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "demo" / "data"
SQLITE_PATH = DATA_DIR / "demo.sqlite"
INDEX_PATH = DATA_DIR / "vector_index.npz"
INDEX_META_PATH = DATA_DIR / "vector_index_meta.json"
DEMO_SET_PATH = DATA_DIR / "demo_set.json"
LEARNINGS_PATH = DATA_DIR / "learnings.json"
DEBATE_CACHE_PATH = DATA_DIR / "debate_cache.json"

EMBED_MODEL = "intfloat/multilingual-e5-small"

# Multiplier on theatrical sleeps; 1.0 ≈ a ~5 minute loop. Use 0.15 for dev.
DEMO_SPEED = float(os.environ.get("DEMO_SPEED", "1.0"))
SERVER_PORT = int(os.environ.get("DEMO_PORT", "8010"))

# HITL pacing: 0 = wait at every scene gate for POST /control/advance
# (presenter mode; run_demo.sh default). 1 = gates auto-clear after
# AUTOPLAY_GATE_S * DEMO_SPEED (unattended kiosk loop, CI benchmark).
DEMO_AUTOPLAY = os.environ.get("DEMO_AUTOPLAY", "1") == "1"
AUTOPLAY_GATE_S = 12.0

# How many of the precomputed showcase events exist; the runner walks one per
# loop so a kiosk running all day does not repeat the same story every five
# minutes.
SHOWCASE_EVENTS = 3

# The scene waterfall — the full story in focused, gated steps. The frontend
# switches its layout on the scene id; the runner emits them in this order.
SCENES = [
    {"id": "arch", "title_he": "הארכיטקטורה",
     "subtitle_he": "פייפליין דטרמיניסטי אוסף ומנתח — עוד לפני ששכבת הסוכנים נכנסת"},
    {"id": "intake", "title_he": "איסוף — עוד בלי AI",
     "subtitle_he": "קרולרים דטרמיניסטיים מביאים מנה מעורבת של כתבות; קישור שבור מפעיל עץ החלטות, לא קריסה"},
    {"id": "lexicon", "title_he": "האלגוריתם — עדיין בלי AI",
     "subtitle_he": "לקסיקון הקיטוב של אלמוג בן שמחון: חלונות, ספירה, דומיננטיות — כך נולדים השדות שבאתר"},
    {"id": "event_map", "title_he": "כאן נכנס ה־AI: מי עוד סיקר את זה?",
     "subtitle_he": "כותרות של אותו אירוע כמעט לא חולקות מילים — אחזור סמנטי מוצא את הגרסאות שחיפוש מילולי מפספס"},
    {"id": "framing", "title_he": "המסגור: מי המבצע, למי האחריות",
     "subtitle_he": "מודל שפה מחלץ את מה שהלקסיקון עיוור אליו — ומאמת דטרמיניסטי פוסל כל ביטוי שאינו בטקסט"},
    {"id": "audience", "title_he": "אותו אירוע, קהלים שונים",
     "subtitle_he": "מה הקוראים עשו מהסיפור — ומתי הם חטפו אותו לנושא אחר לגמרי"},
    {"id": "profile", "title_he": "פרופיל הערוץ",
     "subtitle_he": "כל ערוץ מול חציון אותו אירוע — מה כבר אפשר לומר, ומה עוד אין מספיק ראיות לומר"},
    {"id": "economy", "title_he": "כלכלת טוקנים",
     "subtitle_he": "דטרמיניסטי כשאפשר, מודל שפה רק כשצריך — וכמה זה חוסך"},
    {"id": "summary", "title_he": "סיכום", "subtitle_he": ""},
]

# Architecture scene steps — the deterministic pipeline in the exact
# chronological order of the scheduled cloud run (scripts/run_ingestion.sh,
# GitHub Actions, every 6 hours), then the agent layer on top of it.
ARCH_STEPS = [
    {"step": "crawl", "label_he": "Crawl", "detail_he":
        "קרולרים לכל מקור (ynet, הארץ, מאקו…) — זיהוי כפילויות לפי sha256 של הכתובת"},
    {"step": "windows", "label_he": "Windows", "detail_he":
        "כל כתבה נחתכת לחלונות משפטים — היחידה הבסיסית של הניתוח"},
    {"step": "comments", "label_he": "Comments", "detail_he":
        "איסוף תגובות גולשים לכתבות בנות 24+ שעות — אות הקהל של המערכת"},
    {"step": "lexicon", "label_he": "Lexicon", "detail_he":
        "מילון קיטוב שנבנה פעם אחת אופליין (מחקר בן שמחון) — בלי NLP בזמן ריצה"},
    {"step": "analyze", "label_he": "Analyze", "detail_he":
        "ספירת מופעים ודומיננטיות לכל חלון + שקלול התגובות — דטרמיניסטי"},
    {"step": "db", "label_he": "Postgres", "detail_he":
        "התוצאות נשמרות ומוגשות לאתר — בדיוק בסדר הזה רץ הכל ב־GitHub Actions כל 6 שעות"},
    {"step": "agents", "label_he": "שכבת הסוכנים", "detail_he":
        "ומעל הכל: חמישה סוכנים — איסוף, לקסיקון, אחזור סמנטי, חילוץ מסגור ואימות"},
]

AGENTS = [
    {
        "id": "scout", "name_he": "סקאוט", "role_he": "סוכן איסוף", "emoji": "🛰️",
        "tier": 2, "tier_label_he": "עץ החלטות אוטונומי",
        "persona_he": "שיטתי, לא מוותר על קישור שבור",
    },
    {
        "id": "lexi", "name_he": "לקסי", "role_he": "אנליסט לקסיקון", "emoji": "📖",
        "tier": 1, "tier_label_he": "דטרמיניסטי מבוסס־חוקים",
        "persona_he": "גאה בדטרמיניזם, מצטט את המחקר",
    },
    {
        "id": "librarian", "name_he": "הספרנית", "role_he": "סוכנת אחזור (RAG)", "emoji": "🗂️",
        "tier": 3, "tier_label_he": "אחזור וקטורי סמנטי",
        "persona_he": "מוצאת את אותו סיפור גם כשאין מילה משותפת",
    },
    {
        "id": "nova", "name_he": "נובה", "role_he": "סוכנת מסגור", "emoji": "🤖",
        "tier": 4, "tier_label_he": "מודל שפה על גבי האחזור",
        "persona_he": "קוראת מי המבצע ולמי מיוחסת האחריות",
    },
    {
        "id": "amit", "name_he": "עמית", "role_he": "המאמת", "emoji": "🎓",
        "tier": 5, "tier_label_he": "דטרמיניסטי — פוסל מה שאינו מעוגן",
        "persona_he": "ספקן; ביטוי שלא נמצא בטקסט לא עולה למסך",
    },
]

# The 7 lexicon categories (c1..c7), matching the headers of
# data/lexicon_base/category{1..7}.txt — used for grounded insights.
LEXICON_CATEGORY_NAMES_HE = [
    "פוליטיקה", "ביטחון", "כלכלה", "חברה", "משפט", "זהות/דת", "בינלאומי",
]

# OpenRouter pricing for openai/gpt-4o-mini (USD per 1M tokens) — for the
# token-economy display only.
PRICE_PROMPT_PER_M = 0.15
PRICE_COMPLETION_PER_M = 0.60
