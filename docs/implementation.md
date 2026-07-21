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
    deterministic_matcher.py     # התאמת טוקנים למילון
    lexicon_provenance.py          # תיוג מקור (simchon / media-v2 / …)
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

tests/                           # בדיקות pytest
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
| `notes` | מקור המילה באנגלית: `simchon`, `israeli-supplement`, `media-v2`, `ai-review` |

עריכה: הוסף שורה → שמור → הרץ מחדש. אין צורך לבנות קובץ מורחב — ההרחבה רצה בזיכרון בכל ריצה.

לתיוג מקור בשורות חדשות: `src/lexicon/lexicon_provenance.py` (ערכי `notes` מוגדרים שם).

### `data/lexicon/source/`

קבצי המקור המקוריים מ-[OSF bm8uy](https://osf.io/bm8uy/) של סימחון:

- `final_dict.csv` — 205 מילים באנגלית
- `dict_hclust.csv` — תיוג issue/affective לכל stem

לא עורכים ידנית. לבנייה מחדש של `polarization.csv`:

```powershell
python scripts/build_polarization_lexicon.py
```

---

## זרימת עיבוד מלאה

```
קלט (כתבה / תגובה)
  → נרמול (normalize)
  → טוקניזציה (tokenize)
  → [כתבה בלבד] פיצול למשפטים + חלונות
  → התאמה למילון (deterministic_matcher)
  → ספירת issue / affective
  → חישוב יחסים (ratios)
  → [כתבה] אגרגציה לרמת כתבה | [תגובות] ממוצע audience
```

נקודת כניסה: `scripts/process_one_article.py`  
מודולים מרכזיים: `src/features/article_windows.py`, `src/features/comments_scoring.py`

### אורקסטרציה (`process_one_article.py`)

1. טוען `data/fixtures/sample_article.json`
2. טוען `polarization.csv` → `lexicon_base` + `lexicon_expanded` (בזיכרון)
3. יוצר `DeterministicLexiconMatcher(lexicon_expanded)`
4. מחשב `article_id = sha256(canonicalize_url)`
5. קורא `compute_article_analysis(...)` → `windows`, `token_matches`, `article`
6. קורא `compute_comments_analysis(...)` → `comments`, `token_matches`, `audience`
7. מדפיס JSON לכל רשומה + סיכום `token_matches` (issue / affective / unmatched)

**חשוב:** ציון הכתבה וציון התגובות מחושבים בנפרד. אין ציון משולב אחד.

---

## שלב 1 — עיבוד טקסט

### נרמול (`src/nlp/normalize.py`)

חל על כתבה ותגובות באותה לוגיקה:

1. הסרת URLs
2. הסרת ניקוד (Unicode category `Mn`)
3. נרמול גרשיים ומקפים
4. `lower()` — בעברית לרוב ללא השפעה
5. הסרת תווים לא-לשוניים (שומר עברית, אותיות לטיניות, מקף, גרש)
6. כיווץ רווחים

לא מתבצעת למטיזציה, לא מוסרות מילים, ולא משנים סדר מילים.

### טוקניזציה (`src/nlp/tokenize.py`)

- פיצול לפי **רווח** בלבד
- כל מילה = טוקן אחד
- ביטויים מרובי מילים במילון (למשל `רצח עם`) יתאימו רק אם מופיעים כטוקן בודד — בפועל כמעט תמיד לא

### פיצול למשפטים — כתבה בלבד (`src/nlp/sentence_splitter.py`)

- פיצול אחרי `.` `!` `?` `…`
- heuristics לקיצורים (dr., e.g. וכו') — רלוונטי בעיקר לאנגלית
- כל משפט מקבל `sentence_idx` עולה (0, 1, 2, …)

### חלונות (windows) — כתבה בלבד

| מצב | הגדרה |
|-----|--------|
| משפט רגיל | חלון אחד = כל הטוקנים במשפט |
| משפט > 60 טוקנים | פיצול לרצפים של 60; כל רצף = חלון נפרד עם `sentence_idx` עולה |

קבוע: `MAX_TOKENS_PER_WINDOW = 60` ב-`article_windows.py`

**תגובה:** אין פיצול למשפטים. כל תגובה = חלון יחיד.

---

## שלב 2 — מילון והתאמה

### טעינה (`src/lexicon/load_polarization_lexicon.py`)

1. קורא `data/lexicon/polarization.csv` → מילון בסיס: `lemma → component`
2. מרחיב בזיכרון (`expand_lexicon`) → ~2,500 צורות עם תחיליות עבריות
3. `lexicon_version` = SHA-256 של תוכן הקובץ

### הרחבת תחיליות (`src/lexicon/expand_lexicon.py`)

לכל lemma באורך ≥ 3 (`MIN_BASE_LENGTH`):

- תחילית בודדת: `ה`, `ו`, `ב`, `ל`, `מ`, `כ`, `ש`
- זוגות מורשים: `וה`, `ול`, `וב`, `וש`, `כש`

למות קצרות מ-3 תווים (למשל `בגץ`) **לא** מקבלות הרחבת תחיליות — רק הצורה המדויקת מה-CSV.

דוגמה: `ממשלה` → גם `הממשלה`, `בממשלה`, `והממשלה`

אם שתי למות מייצרות אותה צורה עם `component` שונה — הצורה **נמחקת** (לא דו-משמעות בזמן ריצה).

### התאמת טוקן (`src/lexicon/deterministic_matcher.py`)

לכל טוקן ייחודי בטקסט, לפי סדר:

1. חיפוש מדויק במילון המורחב
2. הסרת תחיליות עבריות (`הובלמכש`) וחיפוש שוב
3. הסרת סיומות נפוצות (`יות`, `ות`, `ים`, `ה`, `י`, …) וחיפוש שוב
4. שילובי תחילית+סיומת

תוצאה לכל טוקן: `issue` | `affective` | `null` (לא במילון)

כללים:

- טוקן מתאים ל**למה אחת לכל היותר**
- אם אין התאמה — הטוקן לא נספר
- אותה מילה ייחודית נשלחת פעם אחת לכל הכתבה/קבוצת תגובות (לא קריאה חוזרת)

---

## שלב 3 — נוסחאות ציון

### ספירה בחלון (משפט / תגובה)

עבור רשימת טוקנים בחלון:

```
issue_count     = מספר טוקנים שסווגו issue
affective_count = מספר טוקנים שסווגו affective
polar_count     = issue_count + affective_count
window_len      = סך כל הטוקנים בחלון (גם אלו שלא במילון)
```

### יחסים (ratios)

```
issue_ratio     = issue_count / window_len
affective_ratio = affective_count / window_len
polar_ratio     = polar_count / window_len
```

**מקרי קצה:**

| מצב | התנהגות |
|-----|---------|
| `window_len = 0` (טקסט ריק) | כל ה-ratios = `null` |
| `window_len > 0` אבל אין התאמות | `polar_ratio = 0.0` (לא `null`) |

טווח ערכים: `[0.0, 1.0]` כשאינם `null`.

---

## שלב 4 — ציון כתבה

### לכל חלון (`WindowFeature`)

שדות: `sentence_idx`, `window_len`, `issue_count`, `affective_count`, `polar_count`, `issue_ratio`, `affective_ratio`, `polar_ratio`, + מטא-דאטה גרסאות.

### אגרגציה לרמת כתבה (`ArticlePolarization`)

```
total_tokens    = סכום window_len על כל החלונות
issue_count     = סכום issue_count
affective_count = סכום affective_count
polar_count     = issue_count + affective_count

issue_ratio     = issue_count / total_tokens
affective_ratio = affective_count / total_tokens
polar_ratio     = polar_count / total_tokens
```

**שים לב:** ציון הכתבה הוא **סכום מונים / סך טוקנים** — לא ממוצע של `polar_ratio` לחלון.  
משפט קצר עם קיטוב גבוה משפיע פחות ממשפט ארוך עם אותו יחס.

---

## שלב 5 — ציון תגובות

### לכל תגובה (`CommentPolarization`)

אותה נוסחת חלון כמו למעלה, עם:

- `comment_len` במקום `window_len`
- `comment_id` — מהמקור, או `sha256(article_id:index:text)`
- `like_count` — **נשמר בפלט בלבד, לא נכנס לחישוב**

### אגרגציה לרמת קהל (`AudiencePolarization`)

```
audience_polar_mean     = ממוצע polar_ratio של תגובות (רק כאלה עם ratio לא-null)
audience_issue_mean     = ממוצע issue_ratio
audience_affective_mean = ממוצע affective_ratio
num_comments            = מספר התגובות שנבדקו
```

**לא** משקללים לפי לייקים (בניגוד ל-RFC הישן ב-`docs/algorithms/`).

תגובה ריקה: `polar_ratio = null` — לא נכנסת לממוצע.

---

## דוגמה מספרית — כתבת הדמה

טקסט:
> הממשלה החליטה על רפורמה חדשה. האופוזיציה התנגדה בחריפות. הציבור מחולק בדעותיו.

| חלון | טוקנים | issue | affective | polar_ratio |
|------|--------|-------|-----------|-------------|
| 1 | 5 | 2 (`הממשלה`, `רפורמה`) | 0 | 0.40 |
| 2 | 3 | 1 (`האופוזיציה`) | 2 (`התנגדה`, `בחריפות`) | 1.00 |
| 3 | 3 | 1 (`הציבור`) | 1 (`מחולק`) | 0.67 |

**ציון כתבה:**
```
total_tokens = 11
polar_count  = 7
polar_ratio  = 7/11 ≈ 0.64
```

**תגובה 1** ("הממשלה משחיתה ומשקרת לציבור. בושה!", 5 טוקנים):
```
issue=2, affective=3 → polar_ratio = 5/5 = 1.0
```

**תגובה 2** ("רפורמה נחוצה וחשובה לדמוקרטיה.", 4 טוקנים):
```
issue=2, affective=0 → polar_ratio = 2/4 = 0.5
```

**תגובה 3** ("האופוזיציה מתנגדת לכל דבר רק בגלל פוליטיקה קטנה.", 8 טוקנים):
```
issue=2, affective=1 → polar_ratio = 3/8 = 0.375
```

**תגובה 4** ("אין פה מחלוקת אמיתית, הכל תיאטרון.", 6 טוקנים):
```
issue=1, affective=0 → polar_ratio = 1/6 ≈ 0.17
```

**audience** (4 תגובות): ממוצע פשוט של `polar_ratio` = (1.0 + 0.5 + 0.375 + 0.167) / 4 ≈ **0.51**

---

## שדות פלט — מפתח

### כתבה (`article`)

| שדה | משמעות |
|-----|--------|
| `window_count` | מספר חלונות |
| `total_tokens` | סך טוקנים |
| `issue_count` / `affective_count` / `polar_count` | מונים מצטברים |
| `issue_ratio` / `affective_ratio` / `polar_ratio` | יחסים מצטברים |

### חלון (`windows[]`)

כמו למעלה, לכל משפט/תת-חלון.

### תגובה (`comments[]`)

| שדה | משמעות |
|-----|--------|
| `comment_id` | מזהה תגובה |
| `comment_len` | אורך בטוקנים |
| `*_ratio` | יחסים לתגובה |
| `like_count` | מידע בלבד |

### קהל (`audience`)

| שדה | משמעות |
|-----|--------|
| `num_comments` | כמה תגובות (כולל ריקות) |
| `audience_polar_mean` | ממוצע קיטוב תגובות |
| `audience_issue_mean` | ממוצע ציר issue |
| `audience_affective_mean` | ממוצע ציר affective |

### `token_matches` (דיבוג)

מילון `טוקן → issue | affective | null` לכל הטוקנים הייחודיים בכתבה או בקבוצת התגובות.
מודפס בסקריפט הדמו לפי קבוצות — שימושי לבדיקת התאמות מילון, לא חלק מסכימת אחסון עתידית.

---

## מזהים (`src/common/hashing.py`)

```
article_id  = sha256(canonicalize_url)
comment_id  = מזהה מהמקור, או sha256(f"{article_id}:{index}:{text}")
```

`canonical_url` — ניקוי פרמטרי tracking (`utm_*`, `fbclid`, `gclid`), netloc קטן, path מנורמל, query ממוין.

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
| התאמת מילים | מילון מורחב + heuristics דטרמיניסטיים |
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

---

## הערה על תיעוד ישן

קבצים ב-`docs/algorithms/` (article_windows, comments_scoring, aggregation) מתארים גישה קודמת (7 קטגוריות, משקל לייקים). **אל תסתמכו עליהם** — מסמך זה הוא מקור האמת למימוש הנוכחי.

---

## מה עדיין לא מומש

- איסוף כתבות ותגובות אמיתי
- עיבוד batch / Parquet / DuckDB
- Airflow + GCS + BigQuery

---

## היסטוריית פיתוח (סיכום)

1. **מילון** — תרגום והתאמה של מילון סימחון לעברית + תוספות ישראליות
2. **כתבה** — חלונות משפט + ציוני issue/affective/polar
3. **תגובות** — ציון לכל תגובה + `audience_*_mean`
4. **הסרת AI** — מעבר להתאמה דטרמיניסטית (חיסכון בעלות)
5. **איחוד מילון** — קובץ יחיד `polarization.csv`
6. **החזרת מקור OSF** — תחת `data/lexicon/source/`
