# News Polar Analysis

פרויקט גמר — ניתוח קיטוב בחדשות ישראליות לפי מסגרת Simchon et al. (2022).

## התחלה מהירה

```powershell
pip install -e ".[dev]"
python scripts/process_one_article.py
python -m pytest tests/ -q
```

## תיעוד

| מסמך | תוכן |
|------|------|
| [`docs/implementation.md`](docs/implementation.md) | **מה שנבנה בפועל** — קבצים, אלגוריתם, הרצה |
| [`docs/README.md`](docs/README.md) | חוזה המערכת המלא (RFC) |
| [`docs/roadmap.md`](docs/roadmap.md) | ארכיטקטורה עתידית (GCS, BQ, Airflow) |

## מבנה עיקרי

- `data/lexicon/polarization.csv` — המילון העברי
- `data/fixtures/sample_article.json` — כתבת דמה + תגובות
- `src/features/` — חישוב ציונים לכתבה ולתגובות
- `scripts/process_one_article.py` — הרצת demo
