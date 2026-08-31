# News Polar Analysis

A deterministic, lexicon-based pipeline that crawls Israeli news sites, fetches audience comments, scores
article/comment polarity, and serves the results through a FastAPI backend + Next.js frontend (branded **Trust**
in the UI). Runs 24/7 in the cloud — see [Deployment & Operations](#-deployment--operations) below.

For day-to-day dev commands and coding conventions, see `CLAUDE.md`. For the exact algorithms and formulas, see
`docs/algorithms/` and `docs/contracts/`.

## 🔴 Live now

| Piece | Service | Notes |
|---|---|---|
| Database | **Neon** (hosted Postgres) | Single source of truth, `DATABASE_URL` everywhere |
| Ingestion scheduling | **GitHub Actions** (`.github/workflows/ingestion.yml`) | Cron every 6h + manual `workflow_dispatch` |
| Backend API | **Render** (`render.yaml` blueprint) | Free web service, `uvicorn src.api.app:app` |
| Frontend | **Vercel** | Next.js app in `frontend/` |

Full provisioning/operations details are in [Deployment & Operations](#-deployment--operations).

## How it works

Everything downstream of "serve" is derived, deterministic, and re-computable — the only non-deterministic step
(AI classification/summary/bias/assistant) is decoupled from the critical path and never blocks or gates the
lexicon-based numbers.

1. **Crawl** (`pipeline/crawl.py` → `src/crawling/`) — one `BaseCrawler` subclass per source
   (`ynet`, `haaretz`, `mako`, `news12`, `reshet13`, `channel14`), registered in `src/crawling/registry.py`.
   Discovers URLs via RSS/feed pages, extracts article text (JSON-LD with per-site HTML fallbacks).
   `article_id = sha256(canonical_url)` is the dedup key everywhere, so re-running crawl is idempotent. Sources
   crawl in parallel with retry + per-run observability (`ingestion_runs` table) — see
   `docs/adr/0001-parallel-source-crawl-with-retry-and-run-observability.md`.
2. **Article windows** (`src/analysis/article_windows.py`) — splits each new article into sentence "windows" and
   scores lexicon-category hits immediately after crawl (`--windows-only` backfill in `run_ingestion.sh` is a
   safety net, not the primary path).
3. **Comments** — `pipeline/fetch_comments.py` + `src/crawling/comments/{source}.py`, one fetcher per supported
   source (not reshet13). Only fetched once an article is ≥24h old, so comments have time to accumulate.
   The scheduled job caps the batch (`--limit 80`, `--max-minutes 25`, `--haaretz-limit 10`) so a comment
   backlog cannot starve polarity analysis.
4. **Lexicon build** (`pipeline/build_lexicon.py`) — expands `data/lexicon_base/category{1..7}.txt` (7 polarity
   categories, distinct from the 9 AI classification categories below) and `data/comment_lexicon_base/` into
   versioned expanded dictionaries via deterministic Hebrew prefix generation. No runtime stemming — matching is
   a static lookup against the pre-expanded set.
5. **Analyze** (`pipeline/analyze_articles.py` → `src/analysis/`) — per-window category dominance, per-comment
   `polar_ratio` (like-weighted), and per-article weighted aggregates (`audience_mean`, `audience_p85`). Fully
   explainable, no ML. Exact formulas: `docs/algorithms/`.
6. **Classify** (optional, AI, last in the scheduled job) — `src/nlp/classify.py` sends title + truncated body
   to an OpenAI-compatible model and labels one of 9 fixed Hebrew categories (`src/nlp/categories.py`:
   פוליטיקה, ביטחון, בידור, כלכלה, ספורט, חברה, טכנולוגיה, בינלאומי, אחר). Decoupled from crawl and from
   analyze — a classify failure never fails the ingestion run (see `docs/adr/0002-decouple-classification-from-crawl.md`
   and `docs/adr/0003-protect-analyze-from-classify-and-comment-backlog.md`).
7. **AI enrichment** (optional, all off the critical path) — per-article summary (`src/nlp/summarize.py`),
   political bias/framing estimate (`src/nlp/bias.py`), and a RAG-style assistant that answers only from what's
   in the database (`src/nlp/qa.py`). Generated on demand from the frontend, cached in `articles.summary_*` /
   `articles.bias_*` columns.
8. **Derived signals** — trending topics (`src/db/trending.py`), cross-article event timelines
   (`src/analysis/event_grouping.py`), and smart alerts (`src/analysis/alerts.py`, e.g. polarity spikes) are all
   computed from the analyzed data, not separately crawled.
9. **Serve** — `src/api/app.py` (FastAPI) exposes it all read-only; `frontend/` (Next.js) consumes it. See
   [API reference](#api-reference) and [Product tour](#product-tour) below.

`scripts/run_ingestion.sh` runs crawl → windows backfill → comments → lexicon build → analyze, then classify
as a best-effort bonus, and is what the GitHub Actions workflow calls every 6 hours.

### Key invariants

- `article_id = sha256(canonical_url)` is the only notion of article identity — never introduce a second one.
- Comment analysis intentionally excludes author identity and timestamps (privacy/simplicity by design).
- Lexicon matching is build-once-then-lookup, never runtime NLP/stemming.
- Concurrency is scoped to the article level only — no concurrency within one article's windows or comments.

## Product tour

The frontend (`frontend/src/app/`, Hebrew RTL UI branded "Trust") has:

| Page | Route | What it shows |
|---|---|---|
| Home | `/` | Headline stats, polarity trend chart, per-source comparison, trending topics, sources grid |
| Articles | `/articles` | Filterable/searchable article table (source, category, date range, min audience polarity) |
| Article detail | `/articles/[id]` | Full polarity breakdown, comment list, AI summary card, political bias meter — summary/bias generated on demand |
| Events | `/events` | Cross-article event timeline (clustered by `src/analysis/event_grouping.py`) |
| Event detail | `/events/[id]` | Timeline of articles belonging to one event |
| AI Assistant | `/assistant` | Chat that answers only from the database (no external knowledge) via `/api/ai/ask` |
| About | `/about` | Plain-language explanation of the system for end users |

A notification bell (`NotificationBell` / `AnalysisStatusBar`) surfaces smart alerts from `/api/alerts` anywhere
in the shell. Browser requests never hit Render directly — `frontend/src/app/api/*/route.ts` route handlers proxy
server-side to the Render API via `NEXT_PUBLIC_API_URL`, so the browser only ever talks same-origin to Vercel.

## API reference

All endpoints are read-only except the two `POST .../generate` AI endpoints and the alert-read mutations. Backed
by `src/db/browse.py`, `trending.py`, `events.py`, `summary.py`, `bias.py`, `alerts.py`.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness check |
| `GET /api/stats` | Dashboard headline numbers (filterable by source/category/date range) |
| `GET /api/sources`, `GET /api/categories` | Filter option lists |
| `GET /api/analytics/polarity-trend`, `GET /api/analytics/polarity-by-source` | Chart data |
| `GET /api/articles` | Paginated, filterable article list |
| `GET /api/articles/{id}` | Full article detail |
| `GET/POST /api/articles/{id}/summary[/generate]` | AI summary — fetch cached or generate on demand |
| `GET/POST /api/articles/{id}/bias[/generate]` | AI bias/framing estimate — fetch cached or generate on demand |
| `POST /api/ai/ask` | Database-grounded Q&A assistant |
| `GET /api/trending` | Trending topics |
| `GET /api/events`, `GET /api/events/{id}/timeline` | Event list / single event timeline |
| `GET /api/alerts`, `PATCH /api/alerts/{id}/read`, `PATCH /api/alerts/read-all` | Smart alerts + read state |

## Running it locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d                # starts local Postgres (news_polar_db)
cp .env.example .env                # set DATABASE_URL, OPENAI_API_KEY (see note below)
python pipeline/init_db.py          # applies sql/schema.sql + sql/migrations/*.sql
```

Run the app (two processes):

```bash
python pipeline/serve_api.py        # FastAPI on :8000
cd frontend && npm run dev          # Next.js on :3000 (frontend/.env.local sets NEXT_PUBLIC_API_URL)
```

Run the pipeline manually:

```bash
python pipeline/crawl.py --source all|ynet|haaretz|mako|news12|reshet13|channel14 [--limit N]
python pipeline/classify_articles.py [--all] [--limit N] [--dry-run]
python pipeline/fetch_comments.py [--source X] [--min-age-hours 0] [--force]
python pipeline/build_lexicon.py
python pipeline/analyze_articles.py [--limit N] [--force]
```

Tests and lint:

```bash
PYTHONPATH=. pytest tests/ -q
cd frontend && npm run lint && npm run build
```

> **Note on `OPENAI_API_KEY`:** the deployed system uses **two different keys**, one per workload, so that the
> on-demand AI features an end user can trigger from the site never draw on the same quota as the unattended
> 6-hourly ingestion:
>
> | Workload | Key | Configured in |
> |---|---|---|
> | Site AI (`qa`, `summarize`, `bias`) — on demand, in the API process | real OpenAI (`sk-...`) | Render env vars |
> | Ingestion (`classify`) — scheduled, in the Actions runner | OpenRouter (`sk-or-v1-...`) | GitHub Actions secret |
>
> No code knows about this split. `src/nlp/openai_config.py` just reads `OPENAI_API_KEY` / `OPENAI_BASE_URL` from
> its own environment, and the two workloads never share a process — the API never imports `classify`, and Render
> never runs ingestion. Routing follows from which env vars are present: the Actions workflow sets
> `OPENAI_BASE_URL` / `OPENAI_MODEL` to OpenRouter's values, and Render deliberately sets neither, which is what
> makes it fall through to `api.openai.com` and the bare `gpt-4o-mini` model id.
>
> Locally there's only one environment, so `.env` holds a single key that serves both — OpenRouter is the simplest
> choice there. To use a real OpenAI key locally instead, unset `OPENAI_BASE_URL` and `OPENAI_MODEL` (or set
> `OPENAI_MODEL=gpt-4o-mini`), since provider model ids differ.

## 🚀 Deployment & Operations

This section is the source of truth for how the system actually runs in the cloud.

### Why not cron / an in-process scheduler

- **OS `cron`** (`scripts/setup_cron.sh` / `scripts/remove_cron.sh`) is unreliable on developer machines — e.g.
  macOS's TCC privacy layer silently blocks cron jobs under some paths. Still usable for a self-hosted Linux
  box, but it's not what the deployed system relies on.
- An **in-process `APScheduler`** (previously started from FastAPI's startup hook) was removed. It required the
  API host to stay running 24/7 just to fire a timer, coupling ingestion uptime to API uptime for no reason —
  GitHub Actions schedules for free, independent of whether Render is currently awake or cold-started.

### Secrets / env vars

- **GitHub Actions repo secrets** (Settings → Secrets and variables → Actions): `DATABASE_URL`, `OPENAI_API_KEY`
  — consumed only by the ingestion workflow. This `OPENAI_API_KEY` is the **OpenRouter** one.
- **Render service env vars**: `DATABASE_URL`, `OPENAI_API_KEY`, `CORS_ORIGINS` — all marked `sync: false` in
  `render.yaml`, so they must be filled in by hand in the Render dashboard (not auto-provisioned). This
  `OPENAI_API_KEY` is the **real OpenAI** one; despite sharing a name it is a different key from the secret above.
- **Vercel project env var**: `NEXT_PUBLIC_API_URL` — the Render service's public URL.

`OPENAI_BASE_URL` / `OPENAI_MODEL` aren't secret and are baked into `.github/workflows/ingestion.yml` — nothing to
configure by hand for them there. They are intentionally **absent** from `render.yaml`: adding them back would
re-provision OpenRouter routing on every deploy, overriding the dashboard and sending the OpenAI key to the wrong
host (a 401). Their absence is load-bearing, not an oversight.

### One-time provisioning

1. **Neon** — create a project, copy the connection string. It goes into local `.env`, the GitHub secret, and
   the Render env var below.
2. **GitHub** — `gh secret set DATABASE_URL` and `gh secret set OPENAI_API_KEY` on this repo (or via the
   Settings UI).
3. **Render** — dashboard.render.com → New → Blueprint → select this repo (it reads `render.yaml`
   automatically) → Apply. Then open the `news-polar-api` service → Environment and fill in the three vars
   above. Note the resulting `https://*.onrender.com` URL.
4. **Vercel** — vercel.com/new → Import this repo → set **Root Directory to `frontend`** (required — the repo
   root isn't the Next.js app) → add `NEXT_PUBLIC_API_URL` = the Render URL from step 3 → Deploy.
5. Back on Render, set `CORS_ORIGINS` to the Vercel URL from step 4.

An interactive wizard for steps 3–5 can be regenerated any time with the `wizard` skill.

### Sharing dashboard access

Inviting collaborators to Render/Vercel is separate from the git workflow below — it only affects who can see
dashboards/logs, not how code ships (that's still just a GitHub push).

- **Vercel** — a personal (Hobby) project can't have collaborators directly. Dashboard → scope switcher (top
  left) → **Create Team** → move the project in via Project → Settings → General → **Transfer Project** → then
  **Team Settings → Members → Invite**.
- **Render** — dashboard → workspace switcher (top left) → **New Team**. If there's no "Transfer" option under
  the service's Settings, the fastest path is re-running the Blueprint deploy (step 3 above) from inside the new
  Team workspace — the database (Neon) is unaffected either way. Then **Team Settings → People → Invite**.

### Making a change

Both Render and Vercel auto-deploy from the branch they track (`main`) — there's no manual deploy step for
ordinary code changes:

1. Branch, edit, and test locally before pushing:
   ```bash
   git checkout -b my-change
   PYTHONPATH=. pytest tests/ -q                    # if you touched Python
   cd frontend && npm run lint && npm run build      # if you touched the frontend
   ```
2. Commit and push, then merge to `main` (directly or via PR).
3. On merge, Render rebuilds/redeploys the API and Vercel rebuilds/redeploys the frontend automatically — no
   action needed. The GitHub Actions ingestion cron is unaffected and just picks up the new code on its next
   scheduled or manually dispatched run.
4. **Exception — DB migrations**: new files in `sql/migrations/` need no manual step either; they're re-applied
   idempotently on every API startup (`src/db/migrations.py`), so a Render redeploy is enough.
5. **Exception — new/changed secrets**: env vars (a new API key, a changed `DATABASE_URL`, etc.) do **not**
   sync from git. Update them by hand in every place they're consumed: the Render dashboard, the Vercel
   dashboard (if frontend-facing), and `gh secret set <NAME>` for GitHub Actions.
6. Verify: `curl https://<render-url>/api/health`, then load the Vercel URL and confirm the frontend renders
   data with no CORS errors in the browser console.

### Operating it

- Trigger an ingestion run manually: `gh workflow run ingestion.yml` (or Actions tab → "Scheduled ingestion" →
  Run workflow).
- Check ingestion logs: the workflow run's "Upload ingestion logs" artifact, the run log directly, or the
  `ingestion_runs` table (per-source history).
- Check API health: `curl https://<render-url>/api/health`.
- Redeploy backend: push to the branch Render tracks (auto-deploy), or "Manual Deploy" in the Render dashboard.
- Redeploy frontend: push to the branch Vercel tracks (auto-deploy).

## Repository layout

```
src/crawling/     one BaseCrawler subclass per news source + comment fetchers
src/nlp/          AI classification, summary, bias, Q&A assistant (all OpenAI-SDK, routed via openai_config.py)
src/lexicon/      lexicon expansion + deterministic word matching
src/analysis/     windows, comment scoring, aggregation, event grouping, alerts (the deterministic core)
src/db/           one module per concern (articles, classification, comments, analysis, summary, bias, alerts,
                  events, trending, browse = read-only API queries)
src/api/          FastAPI app (src/api/app.py)
pipeline/         CLI entry points that wire src/* together (crawl.py, classify_articles.py, ...)
frontend/         Next.js app (App Router) — the only actively developed UI
web/               legacy static HTML/JS UI, served by src/api/app.py only if frontend/ isn't running
sql/               schema.sql + numbered, idempotent migrations
scripts/           run_ingestion.sh (what GitHub Actions runs), cron helpers (local-machine alternative, unused in prod)
docs/               architecture rationale, exact algorithms, data contracts, ADRs — see below
```

## Further reading

- `CLAUDE.md` — instructions and conventions for AI coding agents working in this repo.
- `CONTEXT.md` — domain glossary for the ingestion/crawl layer.
- `docs/architecture/overview.md` — the *why* behind the design (determinism, batch-over-streaming, signal
  separation).
- `docs/algorithms/` — exact formulas for article windows, comment scoring, aggregation.
- `docs/contracts/` — ID/versioning contracts and data-quality invariants.
- `docs/adr/` — architecture decision records (parallel crawl hardening, decoupled classification, ...).
- `docs/roadmap.md` — the original RFC target architecture (Airflow DAGs, GCS, BigQuery staging). This was the
  aspirational design before the project shipped; the live system substitutes Postgres for BigQuery and has no
  Airflow/GCS in the loop. Kept for historical context, not a description of what's running today.
