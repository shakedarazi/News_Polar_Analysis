# 📘 RFC – News Analysis Pipeline

דטרמיניסטי, מחקרי, Batch-Oriented (עד BigQuery)

---

## Table of Contents

- [1️⃣ מטרת המערכת](#1️⃣-מטרת-המערכת)
- [2️⃣ מקורות נתונים (Sources)](#2️⃣-מקורות-נתונים-sources)
- [3️⃣ עקרונות על (Design Principles)](#3️⃣-עקרונות-על-design-principles)
- [4️⃣ ארכיטקטורה כללית (High-Level)](#4️⃣-ארכיטקטורה-כללית-high-level)
- [5️⃣ זיהוי וישויות (IDs & Keys)](#5️⃣-זיהוי-וישויות-ids--keys)
- [6️⃣ נרמול וטקסט (Text Processing Spec)](#6️⃣-נרמול-וטקסט-text-processing-spec)
- [7️⃣ חלוקה לחלונות (Article Windows)](#7️⃣-חלוקה-לחלונות-article-windows)
- [8️⃣ אסטרטגיית Lexicon (נעול)](#8️⃣-אסטרטגיית-lexicon-נעול)
- [9️⃣ אלגוריתם ניתוח כתבות (7 קטגוריות)](#9️⃣-אלגוריתם-ניתוח-כתבות-7-קטגוריות)
- [🔟 ניתוח תגובות (Audience Signal)](#🔟-ניתוח-תגובות-audience-signal)
- [1️⃣1️⃣ אחסון ב־GCS](#1️⃣1️⃣-אחסון-ב־gcs)
- [1️⃣2️⃣ Staging Format](#1️⃣2️⃣-staging-format)
- [1️⃣3️⃣ BigQuery – טבלאות יעד](#1️⃣3️⃣-bigquery--טבלאות-יעד)
- [1️⃣4️⃣ Airflow DAGs](#1️⃣4️⃣-airflow-dags)
- [1️⃣5️⃣ Data Quality (DQ)](#1️⃣5️⃣-data-quality-dq)
- [1️⃣6️⃣ LLM – אופציונלי בלבד](#1️⃣6️⃣-llm--אופציונלי-בלבד)
- [📕 Appendix A – Concurrency, Staging & Algorithmic Specification](#📕-appendix-a--concurrency-staging--algorithmic-specification)

---

## 1️⃣ מטרת המערכת

לבנות מערכת דטרמיניסטית, יציבה ולא תלויה בהתנהגות אתרי חדשות, שמבצעת:

- איסוף כתבות חדשות ממרכזי החדשות בישראל
- איסוף תגובות קהל לכתבות
- ניתוח טקסטואלי מבוסס מילונים (lexicon-based)
- הפקת מדדים כמותיים לחלונות (משפטים) ולתגובות
- טעינה נקייה ל־BigQuery לצורך ניתוחים עתידיים

> ❗️המערכת אינה Streaming, ואינה נועדה לזמן־אמת.
> המטרה היא דיוק, יציבות ומחקריות, לא latency.

---

## 2️⃣ מקורות נתונים (Sources)

המערכת תומכת במרכזי החדשות המרכזיים בישראל, כולל:

- הארץ
- ynet
- mako / קשת 12
- חדשות 12
- רשת 13 (ערוץ 10 לשעבר)
- ערוץ 14
- מקורות חדשות מרכזיים נוספים באותו מבנה

> ❗️הנחת יסוד:
> אין דרך אמינה למשוך "כל כתבות היום" ישירות מהאתרים (feeds מוגבלים, דינמיקה משתנה).

---

## 3️⃣ עקרונות על (Design Principles)

### 3.1 דטרמיניזם

- אותו input ⇒ אותו output
- אין אלגוריתמים לא דטרמיניסטיים ב־critical path
- כל שינוי ב־lexicon / אלגוריתם ⇒ version חדש

### 3.2 Idempotency

- ריצות חוזרות לא מייצרות כפילויות
- טעינה ל־BQ נעשית רק דרך staging → MERGE
- כל ישות מזוהה ע"י מפתח חד־משמעי

### 3.3 Separation of Concerns

- איסוף (ingestion) מופרד מעיבוד
- תגובות מופרדות מכתבות
- LLM מופרד כ־enrichment אופציונלי

### 3.4 Batch-Oriented

- אין צורך ב־streaming
- תגובות נמדדות לאחר הצטברות (24 שעות)

---

## 4️⃣ ארכיטקטורה כללית (High-Level)

המערכת בנויה משני DAGs ב־Airflow:

### DAG 1 – Ingestion (כל 6 שעות)

מטרתו:

- "להקפיא" כתבות לפני שהאתר משנה/מעלים אותן.

### DAG 2 – Daily Snapshot + Processing (יומי)

מטרתו:

- לאסוף תגובות לאחר הצטברות ולחשב מדדים יציבים.

---

## 5️⃣ זיהוי וישויות (IDs & Keys)

### 5.1 canonical_url

- ניקוי URL (tracking params, trailing slash, scheme)

### 5.2 article_id

```
article_id = sha256(canonical_url)
```

### 5.3 חלונות כתבה

- חלון = משפט
- sentence_idx = אינדקס לאחר sentence split דטרמיניסטי
- מפתח: (article_id, sentence_idx)

### 5.4 תגובות

- אם יש comment_id מהמקור — משתמשים בו
- אחרת:

```
comment_id = sha256(article_id + text + local_index)
```

- מפתח: (article_id, comment_id)

---

## 6️⃣ נרמול וטקסט (Text Processing Spec)

### 6.1 Normalization (כתבות + תגובות)

- הסרת URLs
- הסרת ניקוד
- נרמול גרשיים / מקפים
- lowercasing
- ניקוי תווים לא־לשוניים
- whitespace normalization

> ❗️לא מבצעים שינוי סמנטי בטקסט.

---

## 7️⃣ חלוקה לחלונות (Article Windows)

**החלטה נעולה:**

- חלון = משפט
- sentence splitter rule-based דטרמיניסטי
- פיצול לפי . ! ? … עם heuristics לקיצורים נפוצים

**חריג:**

- אם משפט > 60 טוקנים
- מפוצל לתת־חלונות של 60 טוקנים
- האינדוקס (sentence_idx) ממשיך ברצף

**הנמקה מחקרית:**

- משפט = יחידת טיעון טבעית
- מאפשר מדידת "עושר קטגוריות" ו־dominance
- chunking מונע outliers

---

## 8️⃣ אסטרטגיית Lexicon (נעול)

### הבחירה הרשמית – גישה A: Expanded Lexicon

**עיקרון:**

- לא משנים טוקנים בזמן ריצה
- ההתאמה מתבצעת ע"י מילון מורחב מראש

**lexicon_expanded כולל:**

- מילה בסיסית
- וריאציות עם תחיליות עבריות נפוצות:
  - ה, ו, ב, ל, מ, כ, ש
- (שמרני) צירוף שכיח מאוד של שתי תחיליות בלבד (למשל וה)
- לא מייצרים וריאציות אם אורך < 3

**Versioning:**

- lexicon_base.json
- lexicon_expanded.json
- lexicon_version = sha256(lexicon_expanded.json)

**אותו עיקרון ל־תגובות:**

- comment_lexicon_expanded
- comment_lexicon_version

### אופציה עתידית בלבד (לא ב־baseline)

- גישה B: Prefix stripping שמרני
- מוזכרת כ־Future Work בלבד
- אינה מופעלת בפועל

---

## 9️⃣ אלגוריתם ניתוח כתבות (7 קטגוריות)

### Precompute

- יצירת word2category (dict)

### לכל חלון:

- counts[7]
- active = מספר קטגוריות שונות
- window_len
- cat_words = sum(counts)

### Dominance

```
dominance = max(counts) / cat_words
```

- אם cat_words == 0 → NULL

### סיבוכיות

- O(total_tokens_in_article)

---

## 🔟 ניתוח תגובות (Audience Signal)

### תגובה = חלון

**לכל תגובה:**

- polar_count
- comment_len
- polar_ratio = polar_count / max(1, comment_len)
- like_weight = 1 + ln(1 + like_count)
- comment_score = polar_ratio

### צבירה ברמת כתבה:

- num_comments
- audience_mean (ממוצע משוקלל)
- audience_p85 (quantile משוקלל)

> ❗️אין זיהוי כותב, אין זמן פרסום — בכוונה (פשטות וניקיון).

---

## 1️⃣1️⃣ אחסון ב־GCS

### Raw Articles (DAG 1)

```
gs://bucket/raw/articles/source=.../dt=YYYY-MM-DD/article_id=.../article.json
```

### Snapshot עם תגובות (DAG 2)

```
gs://bucket/snapshot/articles_with_comments/source=.../dt=YYYY-MM-DD/article_id=.../article_with_comments.json
```

> 📝 תגובות ממיונות לפי comment_id → דטרמיניזם.

---

## 1️⃣2️⃣ Staging Format

**החלטה נעולה:**

- Parquet

**הנמקה:**

- schema חזק
- columnar
- טעינה יעילה ל־BigQuery
- פחות זיהום נתונים

---

## 1️⃣3️⃣ BigQuery – טבלאות יעד

- articles
- windows_features
- comments_features
- article_comments_agg
- article_llm_enrichment (אופציונלי)

**כל טעינה:**

- staging → MERGE
- לפי מפתחות ייחודיים

---

## 1️⃣4️⃣ Airflow DAGs

### DAG 1 – crawl_latest_to_gcs

- תזמון: כל 6 שעות
- תפקיד: איסוף והקפאת כתבות

### DAG 2 – daily_snapshot_process_to_bq

- תזמון: פעם ביום
- בוחר כתבות ש־now - first_seen_at >= 24h
- אוסף תגובות
- מחשב פיצ'רים
- טוען ל־BQ

### Concurrency:

- ברמת כתבה בלבד (worker pool)

---

## 1️⃣5️⃣ Data Quality (DQ)

- window_len > 0
- sum(c1..c7) ≤ window_len
- dominance ∈ [0,1] OR NULL
- polar_ratio ∈ [0,1]
- num_comments ≤ 200 (warn)

---

## 1️⃣6️⃣ LLM – אופציונלי בלבד

- לא ב־critical path
- enrichment נפרד
- versioning מלא
- לא משפיע על 7 המדדים הדטרמיניסטיים

---

---

## 📕 Appendix A – Concurrency, Staging & Algorithmic Specification

(השלמה מחייבת ל-RFC הראשי)

---

### A️⃣ מודל מקביליות (Concurrency Model)

**עקרון יסוד:**

המקביליות במערכת מוגבלת אך ורק לרמת הכתבה (article-level parallelism).

אין מקביליות בתוך כתבה, אין מקביליות בתוך חלון, ואין מקביליות בתוך תגובה.

**למה זה קריטי?**

- שומר על דטרמיניזם מוחלט
- מונע race conditions
- מונע שינוי סדר חישוב שמשפיע על פלט
- מאפשר reasoning אלגוריתמי ברור

#### מודל הביצוע בפועל

**יחידת עבודה (Atomic Unit):**

```
ArticleJob(article_id)
```

**כל ArticleJob מבצע:**

- עיבוד כתבה → חלונות
- עיבוד תגובות → ציוני תגובה
- אגרגציה ברמת כתבה
- כתיבה ל-staging (GCS)

#### Worker Pool

- Airflow מפעיל Worker Pool
- כל Worker:
  - מקבל article_id אחד
  - עובד עליו מקצה לקצה
  - לא משתף state עם Workers אחרים

#### Big-O בהקשר מקביליות

**אלגוריתמית:**

```
O(sum(tokens_articles) + sum(tokens_comments))
```

**מקביליות:**

- Speedup קבוע בלבד
- אין שינוי אסימפטוטי

> 📝 זה חשוב לציון אקדמי:
> "Parallelism improves wall-clock time but not asymptotic complexity"

---

### B️⃣ פיצול הפייפליין לשני מסלולים (Pipeline Split)

**למה חייבים פיצול?**

כי:

- כתבות הן טקסט מבני
- תגובות הן אותות קהל
- מחזור החיים שונה
- האלגוריתמים שונים

לכן יש שני מסלולים לוגיים, שמתכנסים רק ברמת הכתבה.

---

### C️⃣ Staging – פירוט מלא לפי פייפליין

#### C1️⃣ Staging של כתבות (Article → Windows)

**Input:**

- article_with_comments.json
- (רק שדה text רלוונטי כאן)

**אלגוריתם חישוב (Article Windows):**

**מבני נתונים:**

```
counts: int[7]
active_categories: int
present_mask: int (bitmask)
```

**פסאודו-קוד (פורמלי):**

```
for sentence in split_to_sentences(article_text):
    tokens = tokenize(sentence)

    if len(tokens) > 60:
        chunks = chunk(tokens, size=60)
    else:
        chunks = [tokens]

    for chunk in chunks:
        counts = [0,0,0,0,0,0,0]
        active = 0
        present_mask = 0

        for token in chunk:
            if token in word2category:
                c = word2category[token]
                if counts[c] == 0:
                    active += 1
                    present_mask |= (1 << c)
                counts[c] += 1

        cat_words = sum(counts)

        if cat_words > 0:
            dominance = max(counts) / cat_words
        else:
            dominance = NULL

        emit window_row
```

**Output ל-Staging (Parquet):**

- טבלה לוגית: windows_features_staging

**שדות:**

- article_id
- sentence_idx
- window_len
- c1 … c7
- active
- present_mask
- dominance
- lexicon_version
- pipeline_version
- run_id

---

#### C2️⃣ Staging של תגובות (Comments → Scores)

**Input:**

- article_with_comments.json
- (רק מערך comments)

**אלגוריתם חישוב (תגובות):**

**פסאודו-קוד:**

```
for comment in comments:
    tokens = tokenize(comment.text)

    polar_count = count(tokens in comment_lexicon)
    comment_len = len(tokens)

    polar_ratio = polar_count / max(1, comment_len)
    like_weight = 1 + ln(1 + like_count)

    emit comment_row
```

**Output ל-Staging (Parquet):**

- טבלה לוגית: comments_features_staging

**שדות:**

- article_id
- comment_id
- comment_len
- polar_count
- polar_ratio
- like_count
- like_weight
- comment_score
- comment_lexicon_version
- pipeline_version
- run_id

---

#### C3️⃣ Staging של אגרגציית תגובות (Per Article)

**פסאודו-קוד:**

```
scores = []
weights = []

for comment in article_comments:
    scores.append(comment_score)
    weights.append(like_weight)

audience_mean = weighted_mean(scores, weights)
audience_p85  = weighted_quantile(scores, weights, 0.85)
```

**Output ל-Staging:**

- טבלה: article_comments_agg_staging

**שדות:**

- article_id
- num_comments
- audience_mean
- audience_p85
- sum_like_weight
- pipeline_version
- run_id

---

### D️⃣ התכנסות (Merge Point)

שלושת ה-staging tables:

- windows_features_staging
- comments_features_staging
- article_comments_agg_staging

נטענים ל-BigQuery וממוזגים (MERGE) לטבלאות הסופיות.

> ❗️אין Join בפייפליין עצמו.
> ❗️הקישור מתבצע רק באמצעות article_id ב-BQ.

---

### E️⃣ למה המבנה הזה נכון מחקרית

#### 1. הפרדת אותות

- כתבה = אות טקסטואלי
- תגובות = אות קהל
- חיבור רק בשאילתות

#### 2. אלגוריתמים פשוטים → מדדים חזקים

- אין מודלים כבדים
- אין state חבוי
- כל מספר ניתן להסבר

#### 3. ניתן להרחבה

- אפשר להוסיף קטגוריות
- אפשר להוסיף LLM
- בלי לשבור חוזה
