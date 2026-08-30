# Demo layer — event contract (backend ⇄ dashboard)

This is the single source of truth for the SSE protocol between the demo agent
backend (`demo/server.py`, port **8010**) and the kiosk dashboard
(`frontend/src/app/demo/`). Both sides must match this file exactly.

## Endpoints

- `GET http://localhost:8010/events` — SSE stream. Each SSE `data:` line is one
  JSON object with a `type` field (schemas below). CORS is open (`*`).
- `GET http://localhost:8010/state` — full JSON snapshot for initial render /
  recovery after refresh: `{agents: AgentInfo[], phase: PhaseEvent|null,
  agent_states: {agentId: AgentStatusEvent}, feed: ReasoningEvent[] (last 50),
  scene: SceneEvent|null, gate: GateEvent|null, arch_steps: ArchStepEvent[],
  showcase: ShowcaseEvent|null, event_map: EventMapEvent|null,
  framings: FramingEvent[], contrast: ContrastEvent|null,
  verifier: VerifierEvent|null, audience: AudienceGapEvent[],
  profile: ProfileEvent|null, economy: EconomyEvent|null,
  llm_mode: LlmModeEvent|null, autoplay: bool}`.
- `POST http://localhost:8010/control/advance` — HITL: clear the currently
  open gate (presenter pressed space / the on-screen button). Returns
  `{ok, advanced: bool}`; `advanced=false` means no gate was open.
- `POST http://localhost:8010/control/restart` — reset the demo loop to its
  opening state (used by the kiosk auto-restart).
- `GET http://localhost:8010/facts` — static explainer facts, read from
  `demo/data/explainer_facts.json` on every request. Returns
  `{available: false}` when the file has not been built. This endpoint has
  nothing to do with the SSE stream: it backs the deep-dive modules, which are
  navigated by the presenter rather than driven by the runner. Shape:
  `{corpus, constants, identity_example, worked_example, sources[], windows,
  comments, lexicon, retrieval, framing}` — see `demo/snapshot/build_explainer_facts.py`
  for the producer and `frontend/src/components/demo/explain/facts.ts` for the
  mirror. `retrieval` additionally carries the clustering threshold sweep,
  which is **recomputed on every build** (six clusterings over the snapshot),
  so the table on the wall is the experiment rather than a remembered result. `framing` is derived entirely from the on-disk LLM caches —
  no model is called — and includes the reason breakdown for every quote the
  verifier rejected.

Every event also carries `ts` (epoch milliseconds).

## Two ways in

The dashboard opens on a **hub** (`HubScene`), not on the waterfall. From there
the presenter can enter any module directly — digits `1..8`, click, `Esc` to go
back. Two kinds of module exist:

- **the narrated run** — the nine-scene waterfall below, driven by the backend
  over SSE. Unchanged.
- **explainer modules** (`frontend/src/components/demo/explain/`) — static
  diagrams of one subsystem, fed by `GET /facts`. No SSE, no runner state, no
  gates. They are readable while the run is mid-scene, and they still render
  (diagrams only, measured strips omitted) when `/facts` is unavailable.
  Live: `scraping`, `algorithm`, `retrieval`, `framing`. The remaining three
  tiles are disabled and labelled "בבנייה".

## The scene machine

The runner is a linear waterfall of 9 scenes, each with a HITL gate at its end:

`arch → intake → lexicon → event_map → framing → audience → profile → economy → summary`

Scenes 1–3 are the deterministic pipeline before any AI. Scenes 4–6 follow ONE
story: which outlets covered it, how each framed it, what each audience did with
it. Scene 7 zooms out to every event in the snapshot. The dashboard switches its
whole layout on the `scene` event. With `DEMO_AUTOPLAY=1` gates auto-clear after
`autoplay_ms`; with `DEMO_AUTOPLAY=0` they wait for `/control/advance`.

Each loop runs one of the precomputed showcase events, rotating, so a kiosk
running all day does not repeat the same story every five minutes.

`showcase`, `event_map`, `framings`, `contrast`, `verifier` and `audience` are
scene-scoped: a `scene` event clears them, so a mid-scene refresh never shows a
card from the previous scene. `profile` and `economy` persist to the summary.

## AgentInfo (roster, served by /state)

```json
{
  "id": "nova",
  "name_he": "נובה",
  "role_he": "סוכנת מסגור",
  "emoji": "🤖",
  "tier": 4,
  "tier_label_he": "מודל שפה על גבי האחזור",
  "persona_he": "קוראת מי המבצע ולמי מיוחסת האחריות"
}
```

Fixed roster (ids): `scout` (🛰️ סוכן איסוף, tier 2), `lexi` (📖 אנליסט
לקסיקון, tier 1), `librarian` (🗂️ סוכנת אחזור RAG, tier 3), `nova` (🤖 סוכנת
מסגור, tier 4), `amit` (🎓 המאמת, tier 5).

## Event types

### scene  (top-level layout switch; see "The scene machine")
`{"type":"scene","scene":"arch|intake|lexicon|event_map|framing|audience|profile|economy|summary","idx":1,"total":9,"title_he":"...","subtitle_he":"..."}`

### gate / gate_cleared  (HITL pause point between scenes)
```json
{"type":"gate","gate_id":"s1-arch","hint_he":"נכיר את הסוכנים — איסוף","autoplay_ms":12000}
{"type":"gate_cleared","gate_id":"s1-arch"}
```
`autoplay_ms` is `null` in presenter mode (`DEMO_AUTOPLAY=0`) — the gate waits
indefinitely for `POST /control/advance`.

### arch_step  (architecture scene — pipeline diagram animation)
`{"type":"arch_step","step":"crawl|windows|comments|lexicon|analyze|db|agents","idx":0,"label_he":"Crawl","detail_he":"...","status":"active|done"}`
Steps follow the chronological order of the real scheduled ingestion run
(`scripts/run_ingestion.sh` in GitHub Actions, every 6 hours).

### showcase  (lexicon scene — real raw material + the product's fields)
`{"type":"showcase","article_id":"...","title":"...","source":"ynet","source_he":"ynet","url":"...","published_at":"2026-08-20","excerpt":"...","windows":14,"mean_dominance":0.41,"max_dominance":0.8,"comments":52,"audience_mean":0.031,"audience_p85":0.07,"top_category_he":"ביטחון","top_count":9}`
Numeric fields may be `null` (e.g. no comments / no lexicon words).

### event_map  (retrieval scene — the same story at other outlets)
```json
{"type":"event_map","event_id":"...","seed_title":"...","seed_source":"mako",
 "topic_he":"כלכלה","keyword_found":0,"semantic_found":2,"total":2,
 "versions":[{"source":"ynet","source_he":"ynet","title":"...","score":0.93,"keyword_overlap":0.04}]}
```
`keyword_found` vs `semantic_found` is the load-bearing comparison of the whole
demo: both are computed live, not replayed.

### framing  (one per version — the LLM's variables, already verified)
```json
{"type":"framing","article_id":"...","source":"haaretz","source_he":"הארץ","title":"...","url":"...",
 "actor":"נתניהו","responsibility":"יו\"ר ועד העובדים","voice":"active|passive|null",
 "lead_perspective":"...","loaded_terms":["פרועה","לא חוקית"],"lex_top_he":"פוליטיקה"}
```
`loaded_terms` contains ONLY terms that passed grounding — a term the verifier
rejected never appears in this event.

### contrast  (the retrieval-augmented step — each version against the others)
```json
{"type":"contrast","event_id":"...","shared_he":"מה כל הגרסאות מסכימות עליו",
 "per_source":[{"source":"mako","source_he":"mako","distinctive_he":"...","evidence_he":"ציטוט או null"}]}
```
`evidence_he` is `null` when the verifier rejected the quote as paraphrase.

### verifier  (the grounding pass — the only agent that removes output)
```json
{"type":"verifier","checked_terms":9,"dropped_terms":[{"source_he":"mako","term":"..."}],
 "rejected_quotes":[{"source_he":"ynet","quote":"..."}],
 "terms_total":250,"terms_rejected":4,"actors_total":142,"actors_rejected":0,
 "quotes_total":144,"quotes_rejected":33,"lead_chars":500}
```
`checked_terms`/`dropped_terms`/`rejected_quotes` are this event, computed live.
The `*_total` fields are the rate across the whole snapshot. `lead_chars` is the
window both the extractor and the verifier use — they must be the same number.

### audience_gap  (one per version — what the readers made of it)
```json
{"type":"audience_gap","article_id":"...","source":"mako","source_he":"mako","title":"...",
 "mean_dominance":0.68,"num_comments":511,"audience_mean":0.02,"audience_p85":0.055,
 "article_topic_he":"כלכלה","comment_topic_he":"פוליטיקה","hijacked":true,
 "top_comment":{"text":"...","like_count":94}}
```
`hijacked` = the readers' dominant lexicon topic differs from the article's.

### profile  (aggregate scene — every event in the snapshot, not the showcase)
```json
{"type":"profile","events_total":69,"min_cell_events":10,
 "outlets":[{"source":"ynet","n":66,"mean":0.0173,"lo":0.0045,"hi":0.0309,"significant":true,
             "mix_top":[["ביטחון",0.008],["משפט",-0.006]]}],
 "curve_source":"ynet","curve_source_he":"ynet",
 "sampling_curve":[{"n":3,"mean":0.02,"lo":-0.02,"hi":0.06,"width":0.0852}],
 "topic_cells":[{"source":"ynet","topic_he":"ביטחון","n":30,"mean":0.0071,"lo":-0.01,"hi":0.02,
                 "usable":true,"significant":false,"top_mix":[["ביטחון",0.01]]}],
 "change_scans":[{"source":"ynet","topic_he":"ביטחון","n":30,"at":"...","shift":-0.028,
                  "p_value":0.107,"detected":false,"before_mean":0.0,"after_mean":0.0,"power_1sd":0.68}],
 "power_table":[{"n":20,"power_1sd":0.47,"power_half_sd":0.17}],
 "coverage":{"ynet":{"covered":66,"total_events":69,"share":0.95,"in_snapshot":624}}}
```
`mean`/`lo`/`hi` are `null` for an outlet with fewer than 3 events — the UI must
render "not enough evidence", never a number. `covered` is only meaningful next
to `in_snapshot`: it mixes editorial selection with how much of that outlet was
crawled.

### economy  (token-economy scene)
`{"type":"economy","model_calls":214,"cached_outputs":214,"total_tokens":120698,"total_cost_usd":0.0289,"showtime_calls":0,"corpus_articles":752,"allllm_tokens_est":789600,"allllm_cost_est":0.1779,"note_he":"אומדן..."}`
`total_cost_usd` is what building the whole AI layer cost, once, offline.
`showtime_calls` is 0 by construction: the kiosk replays a cache.

### llm_mode  (model-provenance indicator)
`{"type":"llm_mode","mode":"cached","label_he":"פלט מודל אמיתי, מוקלט מראש — הקיוסק לא תלוי רשת"}`

### phase
`{"type":"phase","phase":"intake|retrieve|framing|audience|profile","label_he":"..."}`

### agent_status
`{"type":"agent_status","agent":"nova","state":"idle|working|waiting|done|error","task_he":"מנתחת מסגור: הארץ"}`

### message  (drives edge animation on the agent map)
`{"type":"message","from":"librarian","to":"nova","kind":"data|request|response|challenge|help","summary_he":"2 גרסאות של אותו אירוע"}`

### reasoning  (activity feed; `level` colors the row)
`{"type":"reasoning","agent":"amit","level":"info|decision|warn","text_he":"..."}`

### scrape_step  (decision-tree tracker during intake)
`{"type":"scrape_step","url":"...","article_title":"...","step_idx":0,"strategy":"direct|alt_selector|archive_org|rss|skip","status":"trying|failed|success|skipped","note_he":"..."}`

### insight  (grounded Q&A moment at the end of a scene)
`{"type":"insight","question_he":"על מה הקוראים בעצם דיברו?","text_he":"...","source_he":"ספירת לקסיקון על טקסט התגובות"}`

### run_summary  (end of the loop → summary overlay, then reset)
```json
{"type":"run_summary","headline_he":"אותו אירוע, 3 מערכות, 3 מסגורים שונים",
 "event_headline":"...","topic_he":"כלכלה","keyword_found":0,"keyword_total":2,
 "events_total":69,"outlets":[{"source_he":"ynet","n":66,"mean":0.0173,"significant":true}],
 "terms_total":250,"terms_rejected":4,"quotes_total":144,"quotes_rejected":33,
 "links_recovered":2,"dropped":1,"total_cost_usd":0.0289}
```

### reset
`{"type":"reset"}` — dashboard clears transient state and returns to opening screen.
