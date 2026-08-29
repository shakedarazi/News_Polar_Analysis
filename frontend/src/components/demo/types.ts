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
  | "event_map"
  | "framing"
  | "audience"
  | "profile"
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
  source_he: string;
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
}

export interface EventMapVersion {
  source: string;
  source_he: string;
  title: string;
  /** cosine similarity to the seed version */
  score: number;
  /** Jaccard overlap of the two headlines — the baseline being beaten */
  keyword_overlap: number;
}

export interface EventMapEvent {
  type: "event_map";
  ts: number;
  event_id: string;
  seed_title: string;
  seed_source: string;
  topic_he: string | null;
  keyword_found: number;
  semantic_found: number;
  total: number;
  versions: EventMapVersion[];
}

export type FramingVoice = "active" | "passive" | null;

export interface FramingEvent {
  type: "framing";
  ts: number;
  article_id: string;
  source: string;
  source_he: string;
  title: string;
  url: string;
  actor: string | null;
  responsibility: string | null;
  voice: FramingVoice;
  lead_perspective: string | null;
  /** only terms that passed grounding — rejected ones never reach the client */
  loaded_terms: string[];
  lex_top_he: string | null;
}

export interface ContrastItem {
  source: string;
  source_he: string;
  distinctive_he: string | null;
  /** null when the verifier rejected the quote as paraphrase */
  evidence_he: string | null;
}

export interface ContrastEvent {
  type: "contrast";
  ts: number;
  event_id: string;
  shared_he: string | null;
  per_source: ContrastItem[];
}

export interface VerifierEvent {
  type: "verifier";
  ts: number;
  /** this event, checked live */
  checked_terms: number;
  dropped_terms: Array<{ source_he: string; term: string }>;
  rejected_quotes: Array<{ source_he: string; quote: string }>;
  /** the rate across the whole snapshot */
  terms_total: number;
  terms_rejected: number;
  actors_total: number;
  actors_rejected: number;
  quotes_total: number;
  quotes_rejected: number;
  /** the window both the extractor and the verifier use */
  lead_chars: number;
}

export interface TopComment {
  text: string;
  like_count: number;
}

export interface AudienceGapEvent {
  type: "audience_gap";
  ts: number;
  article_id: string;
  source: string;
  source_he: string;
  title: string;
  mean_dominance: number | null;
  num_comments: number | null;
  audience_mean: number | null;
  audience_p85: number | null;
  article_topic_he: string | null;
  comment_topic_he: string | null;
  /** the readers' dominant lexicon topic differs from the article's */
  hijacked: boolean;
  top_comment: TopComment | null;
}

export interface OutletProfile {
  source: string;
  n: number;
  /** null below 3 events — render "not enough evidence", never a number */
  mean: number | null;
  lo: number | null;
  hi: number | null;
  significant: boolean;
  mix_top: Array<[string, number]>;
}

export interface CurvePoint {
  n: number;
  mean: number;
  lo: number;
  hi: number;
  width: number;
}

export interface TopicCell {
  source: string;
  topic_he: string;
  n: number;
  mean: number | null;
  lo: number | null;
  hi: number | null;
  usable: boolean;
  significant: boolean;
  top_mix: Array<[string, number]>;
}

export interface ChangeScan {
  source: string;
  topic_he: string;
  n: number;
  at: string;
  shift: number;
  p_value: number;
  detected: boolean;
  before_mean: number;
  after_mean: number;
  /** share of 1-SD shifts this series length would actually catch */
  power_1sd: number;
}

export interface CoverageRow {
  covered: number;
  total_events: number;
  share: number;
  /** read `covered` only next to this: coverage mixes editorial selection
      with how much of that outlet was crawled */
  in_snapshot: number;
}

export interface ProfileEvent {
  type: "profile";
  ts: number;
  events_total: number;
  min_cell_events: number;
  outlets: OutletProfile[];
  curve_source: string;
  curve_source_he: string;
  sampling_curve: CurvePoint[];
  topic_cells: TopicCell[];
  change_scans: ChangeScan[];
  power_table: Array<{ n: number; power_1sd: number; power_half_sd: number }>;
  coverage: Record<string, CoverageRow>;
}

export interface EconomyEvent {
  type: "economy";
  ts: number;
  model_calls: number;
  cached_outputs: number;
  total_tokens: number;
  total_cost_usd: number;
  /** 0 by construction: the kiosk replays a cache */
  showtime_calls: number;
  corpus_articles: number;
  allllm_tokens_est: number;
  allllm_cost_est: number;
  note_he: string;
}

export interface LlmModeEvent {
  type: "llm_mode";
  ts: number;
  mode: "cached";
  label_he: string;
}

export type PhaseId =
  | "intake"
  | "retrieve"
  | "framing"
  | "audience"
  | "profile";

export interface PhaseEvent {
  type: "phase";
  ts: number;
  phase: PhaseId;
  label_he: string;
}

export type AgentStateId = "idle" | "working" | "waiting" | "done" | "error";

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
  headline_he: string;
  event_headline: string;
  topic_he: string | null;
  keyword_found: number;
  keyword_total: number;
  events_total: number;
  outlets: Array<{
    source_he: string;
    n: number;
    mean: number | null;
    significant: boolean;
  }>;
  terms_total: number;
  terms_rejected: number;
  quotes_total: number;
  quotes_rejected: number;
  links_recovered: number;
  dropped: number;
  total_cost_usd: number;
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
  | EventMapEvent
  | FramingEvent
  | ContrastEvent
  | VerifierEvent
  | AudienceGapEvent
  | ProfileEvent
  | EconomyEvent
  | LlmModeEvent
  | PhaseEvent
  | AgentStatusEvent
  | AgentMessageEvent
  | ReasoningEvent
  | ScrapeStepEvent
  | InsightEvent
  | RunSummaryEvent
  | ResetEvent;

/** GET /state snapshot shape. */
export interface StateSnapshot {
  agents?: AgentInfo[];
  phase?: PhaseEvent | null;
  agent_states?: Record<string, AgentStatusEvent>;
  feed?: ReasoningEvent[];
  scene?: SceneEvent | null;
  gate?: GateEvent | null;
  arch_steps?: ArchStepEvent[];
  showcase?: ShowcaseEvent | null;
  event_map?: EventMapEvent | null;
  framings?: FramingEvent[];
  contrast?: ContrastEvent | null;
  verifier?: VerifierEvent | null;
  audience?: AudienceGapEvent[];
  profile?: ProfileEvent | null;
  economy?: EconomyEvent | null;
  llm_mode?: LlmModeEvent | null;
  autoplay?: boolean;
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

export interface DemoState {
  mode: StreamMode;
  /** backend pacing mode (from /state): false = presenter-controlled (HITL) */
  autoplay: boolean;
  agents: AgentInfo[];
  agentStatus: Record<string, AgentLiveStatus>;
  /** id of the most recently active (working) agent */
  activeAgent: string | null;
  scene: SceneEvent | null;
  gate: GateEvent | null;
  archSteps: ArchStepEvent[];
  showcase: ShowcaseEvent | null;
  eventMap: EventMapEvent | null;
  framings: FramingEvent[];
  contrast: ContrastEvent | null;
  verifier: VerifierEvent | null;
  audience: AudienceGapEvent[];
  profile: ProfileEvent | null;
  economy: EconomyEvent | null;
  llmMode: LlmModeEvent | null;
  phase: PhaseEvent | null;
  feed: FeedItem[];
  beams: Beam[];
  scrape: ScrapeUrlTrack[];
  insight: { id: number; ev: InsightEvent } | null;
  summary: RunSummaryEvent | null;
}
