# Handoff — 2026-08-31 — alerts perf, Neon egress, assistant UX

Continues the session whose input was the root-level `HANDOFF.md` (untracked).
That document's Bug A and Bug B are **both closed**. Its §5 "Neon 5GB" open
question is **answered**. Read that file only for background on the two-key
OpenAI/OpenRouter split; everything else in it is superseded by this document.

**UPDATE — the run completed successfully. Nothing is blocking.** See §2.
The next session starts from the "suggested next work" list in §6.

---

## 1. Where things stand right now

Branch `main`, three commits pushed today. Read the commit messages for the
full reasoning and measurements — they are detailed and not repeated here:

| Commit | What |
|---|---|
| `b2423f4` | `/api/alerts` re-clustered the corpus 14× per request |
| `3589121` | migration deadlock killing ingestion + assistant stonewalling greetings |
| `a92a836` | TTL cache on event clustering; dropped an unused column |

158 tests pass (`PYTHONPATH=. pytest tests/ -q`). Four new test files:
`tests/test_event_bias_distribution.py`, `test_migrations_retry.py`,
`test_qa_conversational.py`, `test_events_cache.py`.

Untracked, not committed, not mine to commit without asking: `HANDOFF.md`,
`deploy_wizard.sh`, `rotate_openai_key_wizard.sh`, `demo/`.

Branch `demo-agent-swarm` is 50 ahead / 3 behind `main`. It will pick these up
on its next merge from main. Nicole (`nicolevaisman@gmail.com`) commits to
`main` directly — check `origin/main` before editing shared files.

### Verified working in production

| Endpoint | Before | Now |
|---|---|---|
| `GET /api/alerts` (Render) | no response in 85s | 1.4–1.9s |
| `POST /api/ai/ask` (Render) | no response in 120s | ~3–20s (20s cold) |
| `POST /api/ask` (Vercel proxy) | 502 | 3.3–3.8s |
| `GET /api/trending` (local) | 1.76s | 0.74s |
| `GET /api/events/{id}/timeline` (local) | 1.62s | 0.63s |

Assistant verified through the live site, not just Render:
greetings answer, aggregate questions answer, out-of-domain still refuses.

---

## 2. RESOLVED — ingestion run 33433312779

```
https://github.com/shakedarazi/News_Polar_Analysis/actions/runs/33433312779
```

**conclusion=success, 39m13s**, on `a92a836`. First green run in at least five
attempts. Every stage completed; zero `STEP FAILED`, zero `DeadlockDetected`,
zero quota errors.

```
19:57:30  run started
19:58:07  crawl finished
19:58:11  article-text backfill finished
20:11:04  comment fetch finished      <- ran 12m53s; previously died in 9s
20:30:39  polarity analysis finished  <- 19m35s, draining the comment backlog
20:35:55  classification finished     <- classified=80 failed=0
```

The 39-minute duration is the proof, not a warning. Every earlier run ended at
~17 min *because* `fetch_comments` crashed instantly in `apply_migrations()`.
A long run means it survived and did real work.

### Both OpenAI keys are now verified live

This closes the last item carried over from the original `HANDOFF.md`.
The providers are distinguishable by the model id they record:

```
classification_model  openai/gpt-4o-mini  n=1336   (ingestion -> OpenRouter, GitHub Actions)
summary_model         gpt-4o-mini         n=2      (site AI  -> real OpenAI, Render)
```

`OPENAI_INGESTION_API_KEY` had never been exercised before this run. It has now
classified 80 new articles with 0 failures.

### Data after the run

```
total articles 1387 | total comments 44226 | classified 1336 | analysed 1120
```

### Production, measured after the run

| | |
|---|---|
| `/api/alerts` (Render) | 0.57s / 1.15s |
| `/api/trending` (Render) | 0.22s |
| `/api/ask` (Vercel proxy) | 15.4s cold, ~3-4s warm |

## 3. Neon data transfer quota — the thing most likely to bite

The handoff's "Neon says 5GB" mystery was **data transfer, not storage**.
Storage genuinely is ~69 MB; that is why measuring it from SQL never explained
anything. The real error, from runs 33392702163 / 33353940634 / 33333842159
(every step failed, not just one):

```
ERROR: Your project has exceeded the data transfer quota. Upgrade your plan to increase limits.
```

Cause, now fixed: `/api/alerts` and `/api/trending` both rebuilt the event
clustering, which reads every classified article. `AppShell` polls both every
30s (`frontend/src/lib/liveConfig.ts`, `LIVE_POLL_INTERVAL_MS = 30_000`), on
every page, in every open tab. One tab pulled **~17 GB/day**, exhausting a
5 GB/month quota in roughly seven hours, repeatedly.

After `a92a836`: ~0.07 GB/day **total** (process-level cache, so no longer
proportional to tab count), projected ~2.1 GB/month.

### What is still not verified

- Whether the quota is **already exhausted for this billing period**. If so,
  runs keep failing regardless of the code until the monthly reset (2026-09-01,
  i.e. tomorrow). Only the Neon Console → Usage page shows this; it is not
  visible from SQL and I could not reach it.
- ~2.1 GB/month is ~40% of a 5 GB quota just for the cache refresh, assuming the
  Render instance never idles. The dial is `EVENTS_CACHE_TTL_SECONDS`
  (default 300). Raising it to 900 would cut that to ~0.7 GB/month.
- Whether the plan is actually 5 GB. Worth confirming against the Console
  rather than inferring from the error text.

**Ask the user for a screenshot of Neon Console → Usage** if runs keep failing
on quota. That is the fastest way to separate "code still wrong" from "out of
quota until tomorrow".

---

## 4. Context that is easy to get wrong

- **`get_events()` results are cached for 5 minutes.** A DB write will not show
  up in `/api/alerts`, `/api/trending`, or `/api/events` until the TTL expires.
  Call `src.analysis.event_grouping.reset_events_cache()` if you need immediacy.
  This surprises people debugging "why didn't my new article appear".
- **Ingestion runs pick up the code at trigger time.** A run started before a
  push does not contain that push. I wasted ~20 minutes waiting on a run that
  could not validate anything; the user correctly told me to cancel it. Always
  check `headSha` against `main` before drawing conclusions from a run.
- **`GET /api/events/{id}` does not exist** — the route is
  `/api/events/{id}/timeline` (`src/api/app.py:225`). A plain 404 with
  `{"detail":"Not Found"}` in ~1ms is the router, not the handler.
- **`/api/events` returns a bare list**, not `{"items": [...]}`.
- **Alert detection still runs synchronously inside `GET /api/alerts`**
  (`src/api/app.py:268`). It is fast now, but a notification-bell poll can still
  trigger corpus-wide work. This is the real architectural fix and is not done.
- The two-key OpenAI/OpenRouter split is Nicole's (`69652e5`) and is correct.
  An earlier attempt in this line of work (`413ea6d`) was reverted (`3f55ab5`).
  **Do not reintroduce it.**

---

## 5. Known-good verification recipes

Local API for HTTP-level checks — `.claude/launch.json` now has an `api` entry,
so use the preview tooling (`preview_start` with `{name: "api"}`), not Bash.

Timing the alerts handler exactly as the endpoint does:

```python
from src.db.alerts import detect_and_save_alerts, list_alerts, count_unread
# time each; that is the whole of api_alerts()
```

Proving a refactor of the detectors changed nothing — compare
`detect_all_alerts()` against the standalone `events=None` path and assert the
payloads are equal, not just the counts. This caught nothing but is the reason
`b2423f4` could be pushed with confidence.

`.env` has a working `DATABASE_URL` (Neon) and a real `OPENAI_API_KEY`. Scripts
in this session loaded it with a regex one-liner because `python-dotenv` is not
installed in `.venv`.

---

## 6. Suggested next work, roughly in order

1. **Watch the next scheduled run** (cron, every 6h). One green run proves the
   deadlock fix under one interleaving, not all of them. If a later run fails on
   `DeadlockDetected` again, raise `_MAX_ATTEMPTS` in `src/db/migrations.py`.
2. **Watch Neon usage over the next few days.** The egress fix is verified by
   measurement, not by a month of data. §3 has the numbers and the dial.
3. **Move alert detection out of the GET.** The remaining ~5s of
   `detect_and_save_alerts` is the save/dedup path and was never examined.
4. **Assistant is single-turn.** `answer_question(question)` takes no history,
   so "מה הכוונה?" is structurally unanswerable; it currently replies with a
   capability list instead. Real follow-ups need a conversation contract across
   `src/nlp/qa.py`, `POST /api/ai/ask`, and `frontend/src/app/api/ask/route.ts`.
   **This is a product decision the user has not made yet — ask before building.**
5. `rotate_openai_key_wizard.sh` stage 1 greps `OPENAI_BASE_URL` anywhere in
   `render.yaml` and matches a comment. Fix to
   `grep -qE '^\s*-\s*key:\s*OPENAI_BASE_URL'`.
6. No PR exists for `demo-agent-swarm`'s 50 commits. Coordinate with Nicole
   before opening one.

---

## 7. Suggested skills

- **`diagnosing-bugs`** — if the ingestion run failed for a reason not in the
  §2 table. The three known signatures are already classified; anything else is
  a fresh diagnosis.
- **`tdd`** — for the multi-turn assistant (item 4). It is a contract change
  across three layers and the existing tests in `tests/test_qa_conversational.py`
  pin the single-turn behaviour that would need revisiting.
- **`code-review`** with `since main~3` — the three commits today were written
  and self-verified in one session with no second reader. The event cache in
  particular introduces shared mutable process state.
- **`wizard`** — only if the Neon plan needs changing; that is dashboard work
  the agent cannot do itself.

Do **not** reach for `research` or workflow orchestration here. The remaining
work is small, local, and well-specified.
