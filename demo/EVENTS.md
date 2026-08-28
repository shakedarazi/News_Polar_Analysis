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
  feed: ReasoningEvent[] (last 50), tokens: {total_tokens, total_cost_usd}}`.
  (`round`/`total_rounds` live inside the phase event.)
- `POST http://localhost:8010/control/restart` — reset the demo loop to its
  opening state (used by the kiosk auto-restart).

Every event also carries `ts` (epoch milliseconds).

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
