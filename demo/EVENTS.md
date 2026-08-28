# Demo layer — event contract (backend ⇄ dashboard)

This is the single source of truth for the SSE protocol between the demo agent
backend (`demo/server.py`, port **8010**) and the kiosk dashboard
(`frontend/src/app/demo/`). Both sides must match this file exactly.

## Endpoints

- `GET http://localhost:8010/events` — SSE stream. Each SSE `data:` line is one
  JSON object with a `type` field (schemas below). CORS is open (`*`).
- `GET http://localhost:8010/state` — full JSON snapshot for initial render /
  recovery after refresh: `{agents: AgentInfo[], phase: PhaseEvent|null,
  agent_states: {agentId: AgentStatusEvent}, metrics: MetricEvent[],
  feed: ReasoningEvent[] (last 50), scene: SceneEvent|null, gate:
  GateEvent|null, arch_steps: ArchStepEvent[], showcase: ShowcaseEvent|null,
  retrieval: RetrievalEvent|null, economy: EconomyEvent|null,
  learned: LearnEvent[] (last 10), llm_mode: LlmModeEvent|null,
  autoplay: bool, tokens: {total_tokens, total_cost_usd}}`.
  (`round`/`total_rounds` live inside the phase event.)
- `POST http://localhost:8010/control/advance` — HITL: clear the currently
  open gate (presenter pressed space / the on-screen button). Returns
  `{ok, advanced: bool}`; `advanced=false` means no gate was open.
- `POST http://localhost:8010/control/restart` — reset the demo loop to its
  opening state (used by the kiosk auto-restart).

Every event also carries `ts` (epoch milliseconds).

## The scene machine

The runner is a linear waterfall of 8 scenes, each with a HITL gate at its
end: `arch → intake → lexicon → rag → rounds → learning → economy → summary`.
The dashboard switches its whole layout on the `scene` event; `phase` events
(with `round`) are emitted only inside the `rounds` scene. With
`DEMO_AUTOPLAY=1` gates auto-clear after `autoplay_ms`; with `DEMO_AUTOPLAY=0`
they wait for `/control/advance`.

## AgentInfo (roster, served by /state)

```json
{
  "id": "nova",
  "name_he": "נובה",
  "role_he": "סוכנת סיווג",
  "emoji": "🤖",
  "tier": 4,
  "tier_label_he": "RAG + מודל שפה + זיכרון",
  "persona_he": "בטוחה בעצמה, אוהבת להסביר למה"
}
```

Fixed roster (ids): `scout` (🛰️ סוכן איסוף, tier 2), `lexi` (📖 אנליסט
לקסיקון, tier 1), `librarian` (🗂️ סוכנת אחזור RAG, tier 3), `nova` (🤖 סוכנת
סיווג, tier 4), `amit` (🎓 מבקר־על, tier 5).

## Event types

### scene  (top-level layout switch; see "The scene machine")
`{"type":"scene","scene":"arch|intake|lexicon|rag|rounds|learning|economy|summary","idx":1,"total":8,"title_he":"...","subtitle_he":"..."}`

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
`{"type":"showcase","article_id":"...","title":"...","source":"ynet","url":"...","published_at":"2026-08-20","excerpt":"...","windows":14,"mean_dominance":0.41,"max_dominance":0.8,"comments":52,"audience_mean":0.031,"audience_p85":0.07,"top_category_he":"ביטחון","top_count":9,"reference":"ביטחון"}`
Numeric fields may be `null` (e.g. no comments / no lexicon words).

### retrieval  (RAG scene — neighbors + token-savings comparison)
`{"type":"retrieval","title":"...","neighbors":[{"title":"...","category":"...","score":0.91}],"tokens_full_est":1830,"tokens_context_est":140,"note_he":"אומדן..."}`

### economy  (token-economy scene)
`{"type":"economy","total_tokens":9980,"total_cost_usd":0.0027,"llm_calls":6,"allllm_tokens_est":94000,"allllm_cost_est":0.021,"note_he":"אומדן..."}`

### llm_mode  (LIVE/local indicator; re-emitted on degrade)
`{"type":"llm_mode","mode":"live|offline","label_he":"מודל ענן חי"}`

### phase
`{"type":"phase","phase":"intake|retrieve|classify|analyze|critique|learn|summary","label_he":"...","round":1,"total_rounds":3,"round_label_he":"סבב 1 — בלי RAG"}`

### agent_status
`{"type":"agent_status","agent":"nova","state":"idle|working|waiting|debating|done|error","task_he":"מסווגת: <כותרת>..."}`

### message  (drives edge animation on the agent map)
`{"type":"message","from":"librarian","to":"nova","kind":"data|request|response|challenge|help","summary_he":"5 שכנים דומים"}`

### reasoning  (activity feed; `level` colors the row)
`{"type":"reasoning","agent":"amit","level":"info|decision|warn","text_he":"..."}`

### scrape_step  (decision-tree tracker during intake)
`{"type":"scrape_step","url":"...","article_title":"...","step_idx":0,"strategy":"direct|alt_selector|archive_org|rss|skip","status":"trying|failed|success|skipped","note_he":"..."}`

### classification
`{"type":"classification","article_id":"...","title":"...","predicted":"פוליטיקה","reference":"פוליטיקה","correct":true,"confidence":0.82,"method":"baseline|knn|llm","neighbors":[{"title":"...","category":"...","score":0.91}]}`
Method badges (he): baseline=חוקי אצבע, knn=שכנים (RAG), llm=מודל שפה + RAG.
`correct` is `null` when no reference label exists.

### debate_start / debate_turn / debate_end
```json
{"type":"debate_start","debate_id":"d1","article_id":"...","title":"...","participants":["nova","amit"],"reason_he":"ביטחון נמוך (0.44)"}
{"type":"debate_turn","debate_id":"d1","agent":"amit","text_he":"..."}
{"type":"debate_end","debate_id":"d1","verdict_he":"...","final_category":"ביטחון","changed":true}
```

### metric  (one per finished round → line chart)
`{"type":"metric","round":1,"label_he":"בלי RAG","accuracy":0.62,"n":8,"learned":0,"duration_s":41.2}`

### tokens  (after every LLM call; totals are cumulative for the whole demo)
`{"type":"tokens","agent":"nova","prompt":812,"completion":64,"cost_usd":0.00021,"total_tokens":15230,"total_cost_usd":0.0041}`

### learn  (self-improvement memory update)
`{"type":"learn","agent":"nova","text_he":"נוספה דוגמה מתוקנת: ...","memory_size":7}`

### insight  (grounded Q&A moment at end of round)
`{"type":"insight","question_he":"מה הנושא המקטב ביותר בסבב?","text_he":"...","source_he":"מבוסס על נתוני הלקסיקון בלבד"}`

### run_summary  (end of full 5-min loop → summary overlay, then reset)
`{"type":"run_summary","rounds":[MetricEvent...],"total_articles":24,"debates":3,"links_recovered":2,"total_cost_usd":0.0093,"headline_he":"הדיוק עלה מ־62% ל־88% בשלושה סבבים"}`

### reset
`{"type":"reset"}` — dashboard clears transient state and returns to opening screen.
