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

# "live"    — real LLM calls through OpenRouter (network required)
# "offline" — no network: kNN classification, grounded template debates
# "auto"    — try live, degrade to offline on first failure/timeout
DEMO_MODE = os.environ.get("DEMO_MODE", "auto")
# Multiplier on theatrical sleeps; 1.0 ≈ a ~5 minute loop. Use 0.15 for dev.
DEMO_SPEED = float(os.environ.get("DEMO_SPEED", "1.0"))
SERVER_PORT = int(os.environ.get("DEMO_PORT", "8010"))

TOTAL_ROUNDS = 3
ARTICLES_PER_ROUND = 8
LLM_TIMEOUT_S = 8.0

ROUND_LABELS_HE = {1: "בלי RAG", 2: "עם RAG", 3: "עם RAG + למידה"}

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
        "persona_he": "מדויקת, תמיד מביאה הקשר",
    },
    {
        "id": "nova", "name_he": "נובה", "role_he": "סוכנת סיווג", "emoji": "🤖",
        "tier": 4, "tier_label_he": "RAG + מודל שפה + זיכרון",
        "persona_he": "בטוחה בעצמה, אוהבת להסביר למה",
    },
    {
        "id": "amit", "name_he": "עמית", "role_he": "מבקר־על", "emoji": "🎓",
        "tier": 5, "tier_label_he": "אוטונומי: מבקר, מתווכח, לומד",
        "persona_he": "ספקן, שואל את השאלות הקשות",
    },
]

CATEGORIES_HE = [
    "פוליטיקה", "ביטחון", "בידור", "כלכלה", "ספורט",
    "חברה", "טכנולוגיה", "בינלאומי", "אחר",
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
