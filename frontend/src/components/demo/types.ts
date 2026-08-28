/**
 * Typed contract for the demo SSE protocol.
 * Single source of truth: demo/EVENTS.md — keep in exact sync.
 */

export interface AgentInfo {
  id: string;
  name_he: string;
  role_he: string;
  emoji: string;
  tier: number;
  tier_label_he: string;
  persona_he: string;
}

export type SceneId =
  | "arch"
  | "intake"
  | "lexicon"
  | "rag"
  | "rounds"
  | "learning"
  | "economy"
  | "summary";

export interface SceneEvent {
  type: "scene";
  ts: number;
  scene: SceneId;
  idx: number;
  total: number;
  title_he: string;
  subtitle_he: string;
}

export interface GateEvent {
  type: "gate";
  ts: number;
  gate_id: string;
  hint_he: string;
  /** null in presenter mode — the gate waits for /control/advance */
  autoplay_ms: number | null;
}

export interface GateClearedEvent {
  type: "gate_cleared";
  ts: number;
  gate_id: string;
}

export type ArchStepId =
  | "crawl"
  | "windows"
  | "comments"
  | "lexicon"
  | "analyze"
  | "db"
  | "agents";

export interface ArchStepEvent {
  type: "arch_step";
  ts: number;
  step: ArchStepId;
  idx: number;
  label_he: string;
  detail_he: string;
  status: "active" | "done";
}

export interface ShowcaseEvent {
  type: "showcase";
  ts: number;
  article_id: string;
  title: string;
  source: string;
  url: string;
  published_at: string;
  excerpt: string;
  windows: number;
  mean_dominance: number | null;
  max_dominance: number | null;
  comments: number;
  audience_mean: number | null;
  audience_p85: number | null;
  top_category_he: string | null;
  top_count: number;
  reference: string | null;
}

export interface RetrievalEvent {
  type: "retrieval";
  ts: number;
  title: string;
  neighbors: NeighborInfo[];
  tokens_full_est: number;
  tokens_context_est: number;
  note_he: string;
}

export interface EconomyEvent {
  type: "economy";
  ts: number;
  total_tokens: number;
  total_cost_usd: number;
  llm_calls: number;
  allllm_tokens_est: number;
  allllm_cost_est: number;
  note_he: string;
}

export interface LlmModeEvent {
  type: "llm_mode";
  ts: number;
  mode: "live" | "offline";
  label_he: string;
}

export type PhaseId =
  | "intake"
  | "retrieve"
  | "classify"
  | "analyze"
  | "critique"
  | "learn"
  | "summary";

export interface PhaseEvent {
  type: "phase";
  ts: number;
  phase: PhaseId;
  label_he: string;
  round: number;
  total_rounds: number;
  round_label_he: string;
}

export type AgentStateId =
  | "idle"
  | "working"
  | "waiting"
  | "debating"
  | "done"
  | "error";

export interface AgentStatusEvent {
  type: "agent_status";
  ts: number;
  agent: string;
  state: AgentStateId;
  task_he?: string;
}

export type MessageKind = "data" | "request" | "response" | "challenge" | "help";

export interface AgentMessageEvent {
  type: "message";
  ts: number;
  from: string;
  to: string;
  kind: MessageKind;
  summary_he: string;
}

export type ReasoningLevel = "info" | "decision" | "warn";

export interface ReasoningEvent {
  type: "reasoning";
  ts: number;
  agent: string;
  level: ReasoningLevel;
  text_he: string;
}

export type ScrapeStrategy =
  | "direct"
  | "alt_selector"
  | "archive_org"
  | "rss"
  | "skip";

export type ScrapeStatus = "trying" | "failed" | "success" | "skipped";

export interface ScrapeStepEvent {
  type: "scrape_step";
  ts: number;
  url: string;
  article_title: string;
  step_idx: number;
  strategy: ScrapeStrategy;
  status: ScrapeStatus;
  note_he?: string;
}

export interface NeighborInfo {
  title: string;
  category: string;
  score: number;
}

export type ClassificationMethod = "baseline" | "knn" | "llm";

export interface ClassificationEvent {
  type: "classification";
  ts: number;
  article_id: string;
  title: string;
  predicted: string;
  reference: string | null;
  /** null when no reference label exists */
  correct: boolean | null;
  confidence: number;
  method: ClassificationMethod;
  neighbors?: NeighborInfo[];
}

export interface DebateStartEvent {
  type: "debate_start";
  ts: number;
  debate_id: string;
  article_id: string;
  title: string;
  participants: string[];
  reason_he: string;
}

export interface DebateTurnEvent {
  type: "debate_turn";
  ts: number;
  debate_id: string;
  agent: string;
  text_he: string;
}

export interface DebateEndEvent {
  type: "debate_end";
  ts: number;
  debate_id: string;
  verdict_he: string;
  final_category: string;
  changed: boolean;
}

export interface MetricEvent {
  type: "metric";
  ts: number;
  round: number;
  label_he: string;
  accuracy: number;
  n: number;
  learned: number;
  duration_s: number;
}

export interface TokensEvent {
  type: "tokens";
  ts: number;
  agent: string;
  prompt: number;
  completion: number;
  cost_usd: number;
  total_tokens: number;
  total_cost_usd: number;
}

export interface LearnEvent {
  type: "learn";
  ts: number;
  agent: string;
  text_he: string;
  memory_size: number;
}

export interface InsightEvent {
  type: "insight";
  ts: number;
  question_he: string;
  text_he: string;
  source_he: string;
}

export interface RunSummaryEvent {
  type: "run_summary";
  ts: number;
  rounds: MetricEvent[];
  total_articles: number;
  debates: number;
  links_recovered: number;
  total_cost_usd: number;
  headline_he: string;
}

export interface ResetEvent {
  type: "reset";
  ts: number;
}

export type DemoEvent =
  | SceneEvent
  | GateEvent
  | GateClearedEvent
  | ArchStepEvent
  | ShowcaseEvent
  | RetrievalEvent
  | EconomyEvent
  | LlmModeEvent
  | PhaseEvent
  | AgentStatusEvent
  | AgentMessageEvent
  | ReasoningEvent
  | ScrapeStepEvent
  | ClassificationEvent
  | DebateStartEvent
  | DebateTurnEvent
  | DebateEndEvent
  | MetricEvent
  | TokensEvent
  | LearnEvent
  | InsightEvent
  | RunSummaryEvent
  | ResetEvent;

/** Cumulative token totals (subset of TokensEvent served by /state). */
export interface TokensTotals {
  total_tokens: number;
  total_cost_usd: number;
  agent?: string;
}

/** GET /state snapshot shape (round/total_rounds live inside the phase event). */
export interface StateSnapshot {
  agents?: AgentInfo[];
  phase?: PhaseEvent | null;
  agent_states?: Record<string, AgentStatusEvent>;
  metrics?: MetricEvent[];
  feed?: ReasoningEvent[];
  scene?: SceneEvent | null;
  gate?: GateEvent | null;
  arch_steps?: ArchStepEvent[];
  showcase?: ShowcaseEvent | null;
  retrieval?: RetrievalEvent | null;
  economy?: EconomyEvent | null;
  learned?: LearnEvent[];
  llm_mode?: LlmModeEvent | null;
  autoplay?: boolean;
  tokens?: TokensTotals | null;
}

/* ---------- reduced dashboard state ---------- */

export type StreamMode = "connecting" | "live" | "mock";

export interface AgentLiveStatus {
  state: AgentStateId;
  task_he?: string;
}

export interface FeedItem {
  id: number;
  agent: string;
  level: ReasoningLevel;
  text_he: string;
}

export interface Beam {
  id: number;
  from: string;
  to: string;
  kind: MessageKind;
  summary_he: string;
}

export interface ScrapeUrlTrack {
  url: string;
  article_title: string;
  /** steps in arrival order */
  steps: Array<{
    strategy: ScrapeStrategy;
    status: ScrapeStatus;
    note_he?: string;
  }>;
}

export interface DebateSession {
  start: DebateStartEvent;
  turns: DebateTurnEvent[];
  end: DebateEndEvent | null;
}

export interface DemoState {
  mode: StreamMode;
  /** backend pacing mode (from /state): false = presenter-controlled (HITL) */
  autoplay: boolean;
  agents: AgentInfo[];
  agentStatus: Record<string, AgentLiveStatus>;
  /** id of the most recently active (working/debating) agent */
  activeAgent: string | null;
  scene: SceneEvent | null;
  gate: GateEvent | null;
  archSteps: ArchStepEvent[];
  showcase: ShowcaseEvent | null;
  retrieval: RetrievalEvent | null;
  economy: EconomyEvent | null;
  learnedItems: LearnEvent[];
  llmMode: LlmModeEvent | null;
  phase: PhaseEvent | null;
  feed: FeedItem[];
  beams: Beam[];
  scrape: ScrapeUrlTrack[];
  classification: { id: number; ev: ClassificationEvent } | null;
  debate: DebateSession | null;
  metrics: MetricEvent[];
  learned: number;
  tokens: {
    totalTokens: number;
    totalCostUsd: number;
    lastAgent: string | null;
    /** bumps on every tokens event — drives the tick animation */
    pulse: number;
  };
  insight: { id: number; ev: InsightEvent } | null;
  summary: RunSummaryEvent | null;
}
