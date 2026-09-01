# Handoff — 2026-09-01 — demo/site gap and end-to-end parity

**Next session's brief (from the user):** work out what the *final* decision is
for the demo relative to the site, and whether the gap between them can be
closed — i.e. take what the demo asserts and implement it end-to-end in the
site as well.

> **Decided 2026-09-01, after this file was written.** The demo stays
> **isolated and frozen**. `demo-agent-swarm` is not merged into `main`; it is
> tagged **`exhibit-2026-09`**, and `/demo` never ships to production. Nothing
> from the demo reaches the site by moving files — only by being reimplemented
> in `src/` + `frontend/` as ordinary work on `main`. Section 1 below asks the
> question; this is the answer, so read section 1 as history.
>
> Every doc it points at (`demo/**`, the repair-module and explainer-copy-lens
> handoffs) lives on that tag, not on `main`:
> `git show exhibit-2026-09:demo/README.md`.

This session did not touch that question. It was spent on data readiness for
the showcase. Everything below either establishes the ground the parity work
stands on, or is a trap that cost time here and should not cost it twice.

---

## 1. The parity question — what is actually known

I did **not** audit demo-vs-site feature parity. What I established is only the
structural situation, which the next session should confirm before planning:

- `demo/` (25 files) is tracked **only on `demo-agent-swarm`**. On `main` the
  directory does not exist. Same for `run_demo.sh`.
- The site that will be shown — Render (`src/api/app.py`) and Vercel
  (`frontend/`) — deploys from **`main`**. So today the demo and the site share
  a database and nothing else.
- `demo-agent-swarm` is **52 commits ahead** of `origin/main` and carries the
  whole demo layer plus its explainer copy.

The authoritative statement of what the demo claims versus what is really
computed is already written: **`demo/README.md`, the section
"פנקס היושרה (מה אמיתי ומה מפושט)"** (starts ~line 121, runs to ~line 646),
including "מגבלות שחייבות להיאמר אם שואלים" (~line 275). That ledger is the
natural input to a parity audit — read it before deciding what to port. Do not
re-derive it.

Also read first, do not duplicate:
- `docs/handoffs/2026-09-01-repair-module-and-the-merge-after-the-show.md` —
  the demo-side handoff written at 00:23 today. It names the repair-loop module
  as the one unfinished piece, and explicitly frames "the merge that waits".
- `docs/handoffs/2026-08-31-explainer-copy-lens.md`
- `demo/HANDOFF3.md`, `demo/EVENTS.md`, `demo/WRITING.md`

**The decision the user wants made is not recorded anywhere I could find.**
Whether `demo-agent-swarm` merges into `main` after the show, stays a parallel
exhibit, or gets cherry-picked feature-by-feature — that is an open product
question. Ask it directly rather than inferring; no PR exists for the 52
commits, and Nicole (`nicolevaisman@gmail.com`) commits to `main` directly, so
this needs coordination, not a unilateral merge.

One concrete finding from the demo branch's own commit `6afbabb` that bears on
parity: the polarization lexicon derives from the **Simchon polarization
paper**, not the Big Five openness work, and there is a stated gap between that
research dictionary and what the pipeline actually scores. If demo copy makes
research claims the site's `src/analysis/` cannot back, that gap is a parity
item, not a wording item.

---

## 2. Data state as of 01:40 (this is what the demo will show)

The showcase is **this afternoon**. The corpus was filled overnight.

| Metric | Start of evening | Now |
|---|---|---|
| Articles | 1,392 | 1,415 |
| Comments | 45,780 | 50,548 |
| Analyzed | 81.3% | 92.0% |
| `audience_mean` | 55.4% | 61.6% |
| Classified | 96.0% | 99.9% |
| AI summaries | 12 | 890 |
| Bias labels | 7 | 774 (+118 correctly "not applicable") |
| Active events | 8 | 14 |
| `windows_features` / dominance | 100% | 100% |

Audience coverage by source: mako 92.2% · news12 95.0% · haaretz 70.0% ·
channel14 68.4% · ynet 41.2%.

Three facts about that table someone will ask about:

- **ynet's 41.2% is real, not a bug.** Verified against the live talkbacks API:
  articles with 0 stored comments return 0 live items (HTTP 200), while control
  articles match exactly (19→19, 48→48). 386 ynet articles genuinely have no
  talkbacks.
- **The 118 unlabelled bias rows are correct behaviour.** `src/nlp/bias.py`
  stores `label=None` when the model answers `applicable=false`. Sampling shows
  weather forecasts, road accidents, births, obituaries. Worth showing as a
  feature — the system declines rather than inventing a label.
- **499 articles (35%) have under 400 characters of extracted text.** This is
  the known `Extracted text too short` crawler-extraction weakness. Those are
  the articles with no summary. Not fixable by re-running.

---

## 3. Two new scripts — uncommitted, and that is a live risk

Both exist on disk only, in a working tree currently checked out on
`demo-agent-swarm`:

- `scripts/backfill_now.sh` — manual uncapped ingestion. Same steps as
  `scripts/run_ingestion.sh` without the runner-clock caps and with a
  configurable age gate.
- `scripts/enrich_via_api.py` — bulk summary/bias backfill that drives the
  deployed Render API rather than calling OpenAI locally.

**Decide whether these belong in the repo.** If the showcase is presented from
a different machine, they are not there. They are deliberately separate from
`run_ingestion.sh` so loosening one cannot silently loosen the scheduled job.

### Command for before the showcase

Run at least an hour ahead, never minutes before:

```bash
scripts/backfill_now.sh --min-age-hours 2 --force
```

Expected gain: ~78 haaretz articles that were too young last night (~74 with
real audience), plus a top-up of everything fetched young. Measured growth for
articles first fetched near publication: **8 of 9 grew, median +14 comments,
one went 5 → 414**. So the re-fetch improves representativeness, not just
volume.

---

## 4. Traps that cost time here

- **The working tree switches branches under you.** At 00:05 it moved from
  `main` to `demo-agent-swarm` mid-run, silently. `.github/workflows/ingestion.yml`
  appeared to revert. Check `git status -sb` before trusting any file's
  contents. The demo branch's own handoff records the mirror-image trap
  (sitting on `main`, where `demo/` does not exist).
- **`--force` re-fetch is safe for ynet/mako/channel14, unsafe for haaretz.**
  `src/crawling/comments/haaretz.py:148` derives `source_comment_id` from the
  comment's *rank* on the page, because the DOM exposes no stable id. Ranks
  shift as comments arrive, so a second fetch maps old ids onto different
  comments. `scripts/backfill_now.sh` hard-codes haaretz to a 24h gate and
  never forces it. Preserve that if you touch the script.
- **The local `.env` has no real OpenAI key.** `OPENAI_API_KEY` there is an
  `sk-or-...` OpenRouter key with `OPENAI_BASE_URL=https://openrouter.ai/api/v1`
  — the same credit pool the scheduled classify spends. The real OpenAI key
  lives only in Render's environment. That is why `enrich_via_api.py` drives the
  deployed API. (The root `HANDOFF.md` claims otherwise; it is wrong.)
  `src/nlp/openai_config.py` deliberately has **no fallback** from
  `OPENAI_INGESTION_API_KEY` to `OPENAI_API_KEY` — keep it that way.
- **Provider is readable from the model column.** OpenRouter writes
  `openai/gpt-4o-mini`; real OpenAI writes bare `gpt-4o-mini`. Used this to
  confirm the overnight enrichment spent zero OpenRouter credit.
- **GitHub's cron is not on the hour.** `0 */6 * * *` fired at gaps of 4h31m to
  9h09m over the last week, and the 18:00 UTC slot never fired at all. Trigger
  manually; do not plan around the schedule.
- **`get_events()` is cached 5 minutes.** A DB write will not appear in
  `/api/alerts`, `/api/trending` or `/api/events` until the TTL expires. Call
  `src.analysis.event_grouping.reset_events_cache()` when you need immediacy.
- **Do not edit a running bash script.** bash reads by byte offset.
- Column names differ from what the previous handoff assumed: it is
  `categorized_at`, not `classified_at`; `first_seen_at`, not `crawled_at`.

---

## 5. Work completed this session

Pushed to `main`: [`b3e3649`](https://github.com/shakedarazi/News_Polar_Analysis/commit/b3e3649)
— ingestion timeout 60 → 90 minutes. The five runs that ever succeeded took
29.4 / 33.7 / 37.9 / 52.0 / 57.3 minutes, so 60 left under three minutes of
headroom, and a timeout kills the log-upload step too.

Two ingestion runs succeeded back to back (39.2 min, 25.2 min), the first
successes since 2026-08-28. That validates all three of yesterday's fixes:
the migration deadlock retry, the event-clustering cache, and the
`OPENAI_INGESTION_API_KEY` OpenRouter split — which had never actually been
exercised by a run until now.

Neon's data-transfer quota did not trigger. It was never a storage problem;
`EVENTS_CACHE_TTL_SECONDS` (default 300) remains the dial if it returns.

Not done, deliberately: alert detection still runs synchronously inside
`GET /api/alerts` (`src/api/app.py:268`), and the assistant is still
single-turn. Both are noted in the superseded root `HANDOFF.md`.

---

## 6. Suggested skills

- **`grilling`** — the actual first task is extracting a decision the user has
  not yet made (merge / parallel exhibit / cherry-pick). Stress-test it before
  writing code; a wrong answer here wastes 52 commits' worth of work.
- **`domain-modeling`** — if the demo asserts concepts the site has no name for,
  that belongs in `CONTEXT.md` / an ADR before it becomes an endpoint. The
  Simchon-lexicon provenance question is exactly this shape.
- **`code-review` with `since origin/main`** — to see the 52 commits as one
  reviewable change before proposing any merge.
- **`tdd`** — for anything ported from demo into `src/` + `frontend/`; a parity
  feature crosses API, DB and UI and needs the contract pinned first.

Do **not** reach for `research` or workflow orchestration. The work is a
decision followed by local, well-specified porting.
