# Handoff — 2026-09-01 — site audit, and the fixes that follow

**Next session's brief (from the user):** work the audit findings below into
fixes. **Do not remove reshet13 or news12 from the display.** Everything else
on the list: yes.

Two PRs shipped and were verified in production before this audit ran:
[#12](https://github.com/shakedarazi/News_Polar_Analysis/pull/12) (two-axis
lexicon reach, semantic events, CI) and
[#13](https://github.com/shakedarazi/News_Polar_Analysis/pull/13) (within-event
outlet comparison, framing extraction + verifier). Read their descriptions and
[ADR 0006](../adr/0006-compare-outlets-within-events-not-across-them.md) rather
than re-deriving any of it. `main` is at `9bed761`, clean, CI green, Render and
Vercel both live and confirmed serving the new work.

---

## 1. The one decision that is already made

reshet13 and news12 **stay on screen**. The audit proposed hiding them; the user
said no. That closes the option of deleting them from `/about`, from
`/api/sources`, or from the source charts.

**It does not settle what to do instead**, and the next session has to pick one
and say which:

- **Repair them.** reshet13 returns HTTP 403 on every run — a header/UA or
  fetch-path problem, possibly solvable. news12's crawler is *fine*; its feed is
  the dead thing (see §2), so repairing it means finding a live Channel-12 feed
  on mako, not touching `FeedDomCrawler`.
- **Label them.** Keep them listed and mark them as not currently ingesting, so
  a reader understands why two of six sources have no bars.

Repairing reshet13 and labelling news12 is a coherent combination; do not assume
one answer covers both. Ask if it is not obvious from the sources' state at the
time.

---

## 2. The audit findings, in the order they should be fixed

Each was verified against the live database and the deployed site during this
session — these are measurements, not suspicions.

### Severe — claims the site makes that are not true

**A. `מחלוקת בקהל` is permanently zero.** All 1,302 rows of
`article_comments_agg`: 871 are exactly `0.0`, **zero** are above it, the rest
NULL. Cause: `controversy = 4p(1−p)` needs dislikes, and **none of the 50,543
rows in `comments_features` carries one** — no source exposes dislike counts.
The card sits in the first row of the article page and in the quick-view modal,
beside real metrics.
Two render sites: `frontend/src/app/articles/[id]/page.tsx:94` and
`frontend/src/components/ArticleDetailModal.tsx:169`. The column stays in
`src/` (it is a live pipeline metric that would work if a source ever exposed
dislikes) — this is a display decision only.

**B. reshet13 has never worked.** Every `ingestion_runs` row for it:
`crashed=True`, `403 Client Error: Forbidden for url: https://13tv.co.il/news`.
Zero articles in the database, ever. `/about` advertises it as a data source.

**C. news12's feed is abandoned.** Confirmed by fetching it directly: the
newest item in
`https://rcs.mako.co.il/rss/31750a2610f26110VgnVCM1000005201000aRCRD.xml` is
dated **7 August 2026**. The crawler discovers the same 20 URLs every run and
skips all of them. All 20 stored articles are from 23 August, 19 of them from
one `news-israel-elections` section.
Worth knowing: **news12 is hosted on mako.co.il** — same domain, same DOM
selectors, a different feed. It is a section of mako, not a separate site.

Net effect of B and C: of six declared sources, **three are live** (ynet, mako,
haaretz). channel14 is alive but tiny — 19 articles, and discovery returned 0 on
two of the last three runs.

### Medium

**D. An article does not link to its event.** 328 articles carry `event_id` and
none of them say so. `get_article_detail` in `src/db/browse.py` does not even
select the column. The event page links out to articles; nothing links back.

**E. Small samples are unmarked in the two older source charts.** news12 (19
analysed) and channel14 (13) occupy the same bar width as ynet (291) in
`#compare` and `#axes`; the count is only in the tooltip. The new
`EventDeviationChart` already handles this correctly (`n=2 · אין רווח`) — copy
that treatment, do not invent a second one.

**F. Stale copy in `/events`.** The `EmptyState` at
`frontend/src/app/events/page.tsx:58` still describes events as matched on
`כותרת דומה`. That is the pre-semantic description; the intro paragraph above it
was already corrected.

### Minor

**G.** English mid-sentence in a Hebrew page: `frontend/src/app/about/page.tsx`
around line 41, `מילים רגשית/ideologically charged`.

**H.** `/about` never mentions the two-axis research lexicon or semantic events,
both of which are surfaced in three places on the site. It gained
`השוואה בתוך אירוע` and `מסגור ואימות` sections in PR #13; these two are the
remaining gap.

**I.** `src/db/events.py`'s module docstring still describes the superseded
lexical grouping ("title overlap").

---

## 3. What is on screen right now, so the next session does not re-survey

Verified live at `https://news-polar-analysis.vercel.app`.

- **`/`** — 5 summary cards + live indicator; `#trend`, `#compare`,
  `#within-event` (new), `#axes`, `#sources`, `#topics`, `#leading`; filter
  sidebar and trending widget.
- **`/articles`** — table: source · title · category · lean · comments · mean
  polarity · peak polarity · date. Filters and a quick-view modal.
- **`/articles/[id]`** — analysis status bar; 4 cards (mean, peak, **מחלוקת**,
  comments analysed); second-reading two-axis panel; AI summary; political lean;
  **framing card** (new); per-sentence dominance; top comments.
- **`/events`** and **`/events/[id]`** — the latter gained
  **`איך כל מקור נבדל באירוע הזה`** (new).
- **`/assistant`**, **`/about`** (5 sections), global notification bell and dark
  mode.

Every component under `frontend/src/components/` is referenced; there is no dead
component. Every API route is consumed by the frontend.

---

## 4. Traps that cost time in this session

- **The working tree is on `main` and `demo/` is physically present** as
  untracked files (`demo/data/` holds real headlines and comments). It will not
  reach production through git, but it is there. The tracked demo code lives
  only on the `exhibit-2026-09` tag: `git show exhibit-2026-09:demo/README.md`.
- **A stale API server survives across sessions.** Port 8000 was held by a
  process started at 00:06 serving old code, which returned `Not Found` for the
  new routes and looked like a bug in them. Check `lsof -ti:8000` before
  believing a 404.
- **`npm run build` clobbers a running dev server's `.next`.** Stop the preview
  first, then build.
- **Browser-pane screenshots ignore scroll** and the pane is often hidden, so
  `computer scroll` times out. Verify with `javascript_tool` — reading
  `innerText` and `getBoundingClientRect()` is stronger evidence than an image
  anyway, and it is how every chart in PR #13 was checked.
- **`from src.analysis.event_stats import median` then `median = median(...)`**
  shadows the function and raises `UnboundLocalError`. Bit twice; the locals are
  named `event_median` now.
- **Nothing on the `src/api/` import path may pull in numpy** — CI asserts it.
  `src/analysis/event_stats.py` is pure Python for exactly this reason.

## 5. Constraints still in force

Carried forward from
[the previous handoff](2026-09-01-demo-site-gap-and-end-to-end-parity.md); all
re-confirmed this session.

- The local `.env` `DATABASE_URL` points at **production Neon**, and
  `src/db/config.py` auto-loads it. A "unit" test that touches the DB is hitting
  production.
- The local `OPENAI_API_KEY` is an **OpenRouter** key on the same credit pool as
  the scheduled classify. The real OpenAI key exists only in Render's
  environment. Provenance is readable from the model column: OpenRouter writes
  `openai/gpt-4o-mini`, real OpenAI writes bare `gpt-4o-mini`. Four framing rows
  in production carry the OpenRouter marker from local verification; the rest
  come from Render. `src/nlp/openai_config.py` deliberately has **no fallback**
  from `OPENAI_INGESTION_API_KEY` to `OPENAI_API_KEY` — keep it that way.
- **`--force` comment re-fetch is unsafe for haaretz** (`source_comment_id`
  derives from rank on the page). `scripts/backfill_now.sh` hard-codes haaretz to
  a 24h gate and never forces it. Preserve that.
- Migrations are re-applied on every `init_db.py` run and every API startup with
  no version table, so all DDL must be idempotent. `010_framing.sql` is applied
  in production.
- `get_events()` is cached 5 minutes; call
  `src.analysis.event_grouping.reset_events_cache()` when you need immediacy.
- Nicole (`nicolevaisman@gmail.com`) commits to `main` directly.
- `scripts/backfill_now.sh` is the user's to run, not the agent's.

## 6. Suggested skills

- **`tdd`** — D and E cross DB, API and UI. Pin the contract first, the way
  `tests/test_event_stats.py` pins the within-event construction.
- **`grilling`** — for §1. "Don't remove them from display" is a constraint, not
  a plan; the actual choice between repairing and labelling is still open and is
  worth stress-testing before code is written.
- **`domain-modeling`** — if news12 stops being modelled as a peer of mako
  (it is a section of the same site), that is a `CONTEXT.md` entry before it is
  an endpoint change.

Do **not** reach for `research` or workflow orchestration. Every item is local
and specified.
