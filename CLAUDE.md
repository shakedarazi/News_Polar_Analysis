# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A batch pipeline that crawls Israeli news sites, fetches audience comments, runs deterministic lexicon-based
polarity/category analysis, and serves results through a FastAPI backend + Next.js frontend. Everything currently
runs against **PostgreSQL** (local via Docker Compose). The `docs/` folder and the bottom half of `README.md`
describe a larger RFC target architecture (Airflow DAGs, GCS, BigQuery, Parquet staging) — that is the aspirational
design, not the current implementation. `airflow/dags/crawl_latest_to_gcs.py` exists but is not the primary
runtime path; treat it as optional/future work unless a task specifically asks for it.

## Commands

### Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d                # starts Postgres (news_polar_db)
cp .env.example .env                # set DATABASE_URL, OPENAI_API_KEY
python pipeline/init_db.py          # applies sql/schema.sql + sql/migrations/*.sql
```

### Run the web app (two processes)
```bash
python pipeline/serve_api.py        # FastAPI on :8000 (src/api/app.py)
cd frontend && npm run dev          # Next.js on :3000 (Turbopack)
```
`frontend/.env.local` sets `NEXT_PUBLIC_API_URL` (defaults to `http://127.0.0.1:8000`).

### Tests
```bash
PYTHONPATH=. pytest tests/ -q
PYTHONPATH=. pytest tests/test_classify.py -q          # single file
PYTHONPATH=. pytest tests/test_classify.py::test_parse_response -q  # single test
```
Tests are plain unit tests against pure functions (parsing, hashing, normalization, extraction) — no live DB or
network required for most of them.

### Frontend lint
```bash
cd frontend && npm run lint
cd frontend && npm run build        # production build
```

### Pipeline scripts (all under `pipeline/`, run from repo root with venv active)
```bash
python pipeline/crawl.py --source all|ynet|haaretz|mako|news12|reshet13|channel14 [--limit N]
python pipeline/classify_articles.py [--all] [--limit N] [--dry-run]   # OpenAI category labeling, run after crawl
python pipeline/fetch_comments.py [--source X] [--min-age-hours 0] [--force]
python pipeline/build_lexicon.py    # expands data/lexicon_base/* and data/comment_lexicon_base/* -> data/*_expanded
python pipeline/analyze_articles.py [--limit N] [--force]              # lexicon polarity scoring
python pipeline/import_json_to_db.py  # one-time legacy JSON import
```
`scripts/run_ingestion.sh` wraps crawl + comment fetch + analysis and is what `.github/workflows/ingestion.yml`
calls on a 6-hour schedule in the cloud (see "Cloud deployment" below). `scripts/setup_cron.sh` /
`scripts/remove_cron.sh` are an alternate local-machine OS-cron path for self-hosting outside GitHub Actions —
not used by the deployed system.

## Architecture

### Data flow
1. **Crawl** (`pipeline/crawl.py` → `src/crawling/`) — each source has a `BaseCrawler` subclass
   (`src/crawling/base.py`) in `src/crawling/sources/{ynet,haaretz,mako,news12,reshet13,channel14}.py`, registered
   in `src/crawling/registry.py` (`CRAWLERS` dict, `get_crawler(source)`). A crawler discovers URLs from RSS/feed
   pages and extracts article text (JSON-LD `articleBody` with site-specific HTML fallbacks via
   `src/crawling/extract_article.py` / `extractors.py`). `article_id = sha256(canonical_url)`
   (`src/common/canonical_url.py`, `src/common/hashing.py`) — this is the dedup key checked against
   `load_known_ids()` before fetching, so re-running crawl is idempotent.
2. **Classify** (optional, OpenAI) — `src/nlp/classify.py` sends only title + first ~1,200 chars
   (`src/nlp/truncate.py`) to `gpt-4o-mini`, parses a JSON response into one of 9 fixed Hebrew categories
   (`src/nlp/categories.py`). Decoupled from crawl — run explicitly as a separate step via
   `pipeline/classify_articles.py`, which `scripts/run_ingestion.sh` invokes right after crawl.
3. **Comments** — `pipeline/fetch_comments.py` + `src/crawling/comments/{source}.py`, one fetcher per supported
   source (ynet, haaretz, mako, news12, channel14 — not reshet13). Only run for articles ≥24h old (comments need
   time to accumulate); haaretz needs Playwright/Chromium for headless rendering.
4. **Lexicon build** (`pipeline/build_lexicon.py`) — expands `data/lexicon_base/category{1..7}.txt` and
   `data/comment_lexicon_base/polar_words.txt` into `data/lexicon_expanded/lexicon_expanded.json` and
   `data/comment_lexicon_expanded/comment_lexicon_expanded.json` by generating Hebrew prefix variants
   (ה, ו, ב, ל, מ, כ, ש, and the conservative two-prefix case). Word matching at analysis time is a direct lookup
   against this expanded set — tokens are never modified/stemmed at runtime. Versioned by
   `sha256(lexicon_expanded.json)`, stored alongside the JSON.
5. **Analyze** (`pipeline/analyze_articles.py` → `src/analysis/`) — deterministic, no ML:
   - `article_windows.py`: splits article text into sentence "windows" (rule-based sentence splitter, long
     sentences chunked at 60 tokens), counts lexicon category hits per window, computes `dominance = max(counts) /
     cat_words` (NULL if no lexicon words present).
   - `comments_scoring.py`: per-comment `polar_ratio = polar_count / max(1, comment_len)`, like-weighted via
     `like_weight = 1 + ln(1 + like_count)`.
   - `aggregation.py`: per-article weighted mean/p85 of comment scores → `audience_mean`, `audience_p85`.
   This whole layer is intentionally simple/explainable — see `docs/algorithms/` for the exact formulas and
   `docs/contracts/data_quality.md` for invariants (`window_len > 0`, `dominance ∈ [0,1] ∪ {NULL}`,
   `polar_ratio ∈ [0,1]`, etc.).
6. **Serve** — `src/api/app.py` (FastAPI) exposes read-only endpoints (`/api/health`, `/api/stats`,
   `/api/articles`, `/api/articles/{id}`, `/api/sources`, `/api/categories`) backed by `src/db/browse.py` queries.
   Runs schema migrations (`src/db/migrations.py` — applies every file in `sql/migrations/` in sorted order, no
   version tracking table) on startup. `frontend/` (Next.js App Router) consumes this API via
   `frontend/src/lib/api.ts`; pages live under `frontend/src/app/` (`/`, `/articles`, `/articles/[id]`, `/about`),
   shared UI in `frontend/src/components/`. `web/` is a legacy static HTML/JS UI, served as a fallback by
   `src/api/app.py` if `frontend` isn't running — not actively developed.

### Cloud deployment
The system also runs 24/7 in the cloud, decoupling ingestion scheduling from API uptime:
- **Neon** — hosted PostgreSQL, same `DATABASE_URL` contract as local Docker Postgres (see below).
- **GitHub Actions** (`.github/workflows/ingestion.yml`) — the *only* ingestion scheduler. Runs
  `scripts/run_ingestion.sh` (crawl → windows backfill → classify → comments → lexicon → analyze) every 6 hours via
  `cron`, plus `workflow_dispatch` for manual runs. Secrets `DATABASE_URL` / `OPENAI_API_KEY` point it at Neon.
  This replaced two earlier mechanisms: OS `cron` (unreliable — macOS TCC blocked it silently) and an in-process
  `APScheduler` started from FastAPI's startup hook (required the API host to stay running continuously just to
  fire a timer). Because scheduling no longer lives inside the API process, the API host is free to idle/sleep
  without affecting data freshness.
- **Render** (`render.yaml`) — hosts `src/api/app.py` (`uvicorn`, free web service, may spin down when idle).
- **Vercel** — hosts `frontend/` (Next.js). Client code never calls the backend directly; browser requests hit
  same-origin Next.js route handlers (`frontend/src/app/api/*/route.ts`) which proxy server-side to Render via
  `NEXT_PUBLIC_API_URL`, so the browser has no CORS dependency on the backend.

### Database
- Single source of truth: PostgreSQL, connection via `DATABASE_URL` (`src/db/config.py`, `src/db/connection.py`).
- Base schema in `sql/schema.sql` (`articles` table: `article_id` PK = sha256 of canonical URL). Additive changes
  live as numbered files in `sql/migrations/` (`001_classification.sql`, `002_comments.sql`, `003_analysis.sql`)
  and are all re-applied (idempotently, via `IF NOT EXISTS`-style DDL) on every `init_db.py` run and API startup —
  there is no migration-version tracking, so new migrations must be safe to re-run.
- `src/db/` modules are split by concern: `articles.py` (crawl writes/dedup), `classification.py` (AI labels),
  `comments.py`, `analysis.py` (polarity results), `browse.py` (read-only queries backing the API).

### Key invariants to preserve
- `article_id = sha256(canonical_url)` is the dedup/idempotency key everywhere — don't introduce a second notion
  of article identity.
- Comment analysis intentionally excludes author identity and timestamps (simplicity/privacy by design per the
  RFC) — don't add them casually.
- Lexicon matching is a static/offline-expanded dictionary lookup, not runtime stemming or NLP — keep new
  category/lexicon logic in the same build-once-then-lookup style.
- Concurrency (where it exists/is planned) is scoped to the article level only — no concurrency within a single
  article's windows or comments, to preserve determinism.

## Reference docs
`docs/architecture/overview.md` explains the *why* behind the design (determinism, batch-over-streaming,
article/comment signal separation). `docs/algorithms/` has exact formulas for aggregation, article windows, and
comment scoring. `docs/schemas/` and `docs/contracts/` describe the target BigQuery/GCS schemas and ID/versioning
contracts from the RFC — useful for intent, but the live system substitutes Postgres tables (`sql/schema.sql`,
`sql/migrations/`) for those BigQuery tables.

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues (`shakedarazi/News_Polar_Analysis`), managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context layout — `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
