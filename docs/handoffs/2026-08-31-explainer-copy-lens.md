# Handoff — explainer modules: the writing lens, and what still needs it

**Date:** 2026-08-31
**Branch:** `demo-agent-swarm` (28 commits ahead of `main`)
**HEAD:** `685729e`
**Working tree:** clean except `deploy_wizard.sh` (untracked, pre-existing, not ours)

## What this session was

The kiosk's nine explainer modules were all built and factually correct, and the
user's verdict was that the *writing* was unreadable — buzzwords, argument-shaped
paragraphs, numbers buried mid-sentence, too many tabs. The session produced a
writing standard, applied it to one module as a calibration, and built the one
new capability the user asked for along the way.

Three things landed. See the commit messages for the reasoning behind each — they
are written to be read and are not repeated here.

- `6835555` — the repair loop (`demo/core/framing.py`, `demo/snapshot/run_repair.py`,
  `RepairModule.tsx`, `tests/test_repair.py`). Ninth hub tile; the map is 3x3 now.
- `d03f79b` — **`demo/WRITING.md`**, the standard, plus `EconomyModule.tsx` rewritten
  through it (6 tabs → 4, 841 Hebrew words → 395).
- `d48d521`, `685729e` — Economy dropped to 3 tabs; the bounded-index / eviction
  measurement (`retrieval.slots`) and the panel that explains it.

## The rule everything follows from

`demo/WRITING.md` is the operative document. Its one rule:

> **A panel states one engineering decision: what was chosen, against what, and
> what it cost or saved.**

Plus the volume budget that enforces it — **3–4 tabs per module, ≤2 panels per tab,
one or two short sentences per panel; the numbers carry the rest.** Read it before
touching any module copy.

`RepairModule.tsx` and the rewritten `EconomyModule.tsx` are the two reference
implementations of the register.

## What is left

### 1. Rewrite the six remaining explainer modules through the lens

Not started. Each needs both the copy rewrite and tab consolidation:

| module | file | tabs now | target |
|---|---|---|---|
| scraping | `ScrapingModule.tsx` | 4 | 3–4, copy only |
| algorithm | `AlgorithmModule.tsx` | 6 | 3–4 |
| **retrieval** | `RetrievalModule.tsx` | **5** | **3** |
| framing | `FramingModule.tsx` | 5 | 3–4 |
| audience | `AudienceModule.tsx` | 6 | 3–4 |
| stats | `StatsModule.tsx` | 6 | 3–4 |

Retrieval is the agreed next one: 5 tabs, and its "האינדקס" tab now carries 3
panels (I added the freshness panel there rather than bolt a 6th tab on — that
overload is expected to be resolved by the rewrite).

The user's stated process: **one module per subagent, each given the module's full
context**, calibrate on one, take critique, then fan out the rest in parallel.
Brief each agent with `demo/WRITING.md`, the module file, `explain/kit.tsx`, the
module's builder function in `demo/snapshot/build_explainer_facts.py`, its slice of
`demo/data/explainer_facts.json`, and the relevant honesty-ledger items.

Verification each agent must run: no `facts` field silently disappears from the
file, `cd frontend && npm run lint`, and `PYTHONPATH=. pytest tests/ -q` if the
builder was touched.

### 2. Topic material to place, by module (from `demo/WRITING.md`)

Only two of these are done. The rest are real in the code and unsaid on screen:

- **tiers** — done, Economy tab 1.
- **RAG** — done, Economy tab 2 (only the contrast call retrieves).
- **why AI and not classical classification** — → framing module.
- **structured output** — `response_format={"type":"json_object"}` in `src/nlp/*`,
  but the demo extractors hand-parse (`_json_object`) and verify deterministically.
  A real difference, worth stating → framing module.
- **GitHub Actions as the free scheduler** — `.github/workflows/ingestion.yml`,
  free `ubuntu-latest`, 6h cron; it replaced OS cron and APScheduler and is why
  Render is free to idle → scraping module.

### 3. Open, not blocking

- The `retrieval.slots` table (window/K and the FIFO/LRU/LFU/RR replay) is typed in
  `facts.ts` and only partly on screen — the full table lands with the retrieval
  rewrite.
- Older presenter decisions: pinning the three showcase events (selection is
  automatic via `showcase_score`, no `event_id` flag exists); whether to re-run
  `export_snapshot.py` closer to the show (forces `prepare_demo.py` + `run_repair.py`
  + README number updates); whether to tighten the verifier (ledger item 19).

## Constraints that stay in force

- **Do not touch `src/`, `pipeline/`, `sql/`, `scripts/`.** Reading is fine; the
  facts builder imports from them. `demo/` and `frontend/` are fair game.
- **No network dependency at showtime.** Every new capability needs a deterministic
  fallback.
- **Nothing unverified reaches the screen.** Numbers come from `facts`, never typed
  by hand. Claim strength is preserved — an estimate stays labelled an estimate.
- **Every simplification or staging goes in the honesty ledger** (`demo/README.md`,
  now at item 47).
- **Commit by component**, and keep the show-day checklist in `demo/README.md` current.
- Slow narrated pacing and the HITL gates stay as they are.

## Running the thing

```bash
source .venv/bin/activate && PYTHONPATH=. python demo/server.py   # :8010
cd frontend && npm run dev                                        # :3000
```

Gotcha that cost time twice: **never run `npm run build` while `next dev` is
running** — it clobbers `frontend/.next` and the dev server starts 500ing on
`_buildManifest.js.tmp.*`. Recovery is stop the server, `rm -rf frontend/.next`,
restart.

Full gate before any commit:

```bash
PYTHONPATH=. pytest tests/ -q          # 220 passing
cd frontend && npm run lint && npm run build
DEMO_SPEED=0.02 PYTHONPATH=. python demo/benchmark.py
```

## Suggested skills

- **`domain`** (`docs/agents/domain.md`) — for `CONTEXT.md` / ADR conventions if any
  of the remaining work turns into a recorded decision.
- **`issue-tracker`** (`docs/agents/issue-tracker.md`) — the six module rewrites are
  a natural set of GitHub issues if the next session wants them tracked rather than
  done in one pass.
