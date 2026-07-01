# מימוש נוכחי — News Polar Analysis

מסמך זה מתעד את מה שנבנה בפועל בקוד (נכון לגרסה `0.5.0-deterministic`).
הוא משלים את ה-RFC ב-`README.md` / `docs/roadmap.md`, שמתארים את המערכת המלאה לעתיד.

---

## מטרה

ניתוח קיטוב בטקסטים חדשותיים ישראליים לפי מסגרת **Simchon et al. (2022)** — שני צירים:

| ציר | משמעות |
|-----|--------|
| `issue` | שפה פוליטית / אידיאולוגית |
| `affective` | שפה רגשית-שלילית / מוסרית |

**כתבה** ו**תגובות** נמדדים בנפרד — אין ציון משולב.

---

## הרצה מהירה

```powershell
pip install -e ".[dev]"
python scripts/process_one_article.py
```

אין צורך ב-API key. ההתאמה למילון דטרמיניסטית.

---

## מבנה הפרויקט (קוד)

```
src/
  common/hashing.py              # article_id, comment_id, sha256
  nlp/
    normalize.py                 # נרמול טקסט עברי
    tokenize.py                  # פיצול למילים
    sentence_splitter.py         # פיצול למשפטים
  lexicon/
    load_polarization_lexicon.py # טעינת polarization.csv
    expand_lexicon.py            # הרחבת תחיליות עבריות (offline/in-memory)
    deterministic_matcher.py     # התאמת טוקנים למילון (ללא AI)
    ai_matcher.py                # אופציונלי — OpenAI (לא בשימוש בברירת מחדל)
  features/
    article_windows.py           # חלונות כתבה + ציון כתבה
    comments_scoring.py          # ציון תגובות + audience mean

scripts/
  process_one_article.py         # הרצה על כתבת דמה אחת
  build_polarization_lexicon.py  # בניית polarization.csv מ-OSF (נדיר)

data/
  fixtures/sample_article.json   # כתבה + 4 תגובות לדוגמה
  lexicon/
    polarization.csv             # המילון העברי (מקור עבודה)
    source/
      final_dict.csv             # מקור OSF — לא לערוך
      dict_hclust.csv            # מקור OSF — לא לערוך

tests/                           # 16 בדיקות pytest
```

---

## קבצי נתונים

### `data/fixtures/sample_article.json`

כתבת דמה בעברית (ynet) + מערך `comments` עם `comment_id`, `text`, `like_count`.
`like_count` נשמר אך **לא** נכנס לחישוב (בסיס Simchon).

### `data/lexicon/polarization.csv`

**מקור האמת** למילון העברי. עמודות:

| עמודה | תיאור |
|--------|--------|
| `lemma` | למה בעברית |
| `component` | `issue` או `affective` |
| `notes` | מקור / תרגום אנגלי |

עריכה: הוסף שורה → שמור → הרץ מחדש.

### `data/lexicon/source/`

קבצי המקור המקוריים מ-[OSF bm8uy](https://osf.io/bm8uy/) של סימחון:

- `final_dict.csv` — 205 מילים באנגלית
- `dict_hclust.csv` — תיוג issue/affective לכל stem

לא עורכים ידנית. לבנייה מחדש של `polarization.csv`:

```powershell
python scripts/build_polarization_lexicon.py
```

---

## אלגוריתם ציון

### כתבה

1. פיצול למשפטים → טוקניזציה
2. חלון = משפט (אם >60 מילים — חלוקה לתת-חלונות)
3. לכל חלון: `polar_ratio = polar_count / window_len`
4. אגרגציה: סכום מונים על פני כל החלונות

### תגובות

1. כל תגובה = חלון אחד
2. אותה התאמה למילון
3. `audience_polar_mean` = ממוצע פשוט של `polar_ratio` על התגובות

### התאמה למילון (דטרמיניסטית)

1. הרחבת תחיליות עבריות בזיכרון (`ה`, `ו`, `ב`, `ל`, `מ`, `כ`, `ש`)
2. חיפוש מדויק במילון המורחב
3. נפילה: הסרת תחיליות/סיומות נפוצות (`התנגדה` → `התנגד`)

---

## גרסאות בפלט

כל רשומה כוללת:

- `lexicon_version` — hash של `polarization.csv`
- `pipeline_version` — `0.5.0-deterministic`
- `run_id` — מזהה ריצה

---

## החלטות עיצוב

| נושא | החלטה |
|------|--------|
| מסגרת מחקרית | Simchon (issue/affective), לא 7 קטגוריות |
| התאמת מילים | מילון מורחב + heuristics — **ללא OpenAI** |
| כתבה vs תגובות | אותות נפרדים |
| משקל לייקים | לא בבסיס (שמור לעתיד) |
| אחסון | עדיין לא מומש (DuckDB/BQ בעתיד) |

---

## בדיקות

```powershell
python -m pytest tests/ -q
```

| קובץ | מה נבדק |
|------|---------|
| `test_article_windows.py` | חלונות, אגרגציה, polar_ratio |
| `test_comments_scoring.py` | תגובות, audience mean |
| `test_deterministic_matcher.py` | תחיליות, סיומות |
| `test_expand_lexicon.py` | הרחבת מילון |
| `test_load_lexicon.py` | טעינת CSV |
| `test_build_lexicon.py` | סקריפט בנייה מ-OSF |
| `test_ai_matcher.py` | מסלול OpenAI אופציונלי |

---

## מה עדיין לא מומש

- איסוף כתבות ותגובות אמיתי
- עיבוד batch / Parquet / DuckDB
- Airflow + GCS + BigQuery
- עדכון מלא של docs/algorithms לגישת Simchon

---

## היסטוריית פיתוח (סיכום)

1. **מילון** — תרגום והתאמה של מילון סימחון לעברית + תוספות ישראליות
2. **כתבה** — חלונות משפט + ציוני issue/affective/polar
3. **תגובות** — ציון לכל תגובה + `audience_*_mean`
4. **הסרת AI** — מעבר להתאמה דטרמיניסטית (חיסכון בעלות)
5. **איחוד מילון** — קובץ יחיד `polarization.csv`
6. **החזרת מקור OSF** — תחת `data/lexicon/source/`
