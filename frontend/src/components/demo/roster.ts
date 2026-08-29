import type {
  AgentInfo,
  AgentStateId,
  MessageKind,
  PhaseId,
  ScrapeStrategy,
} from "./types";

/**
 * Fixed roster per demo/EVENTS.md — used as a fallback until /state answers,
 * and by the mock stream.
 */
export const DEFAULT_AGENTS: AgentInfo[] = [
  {
    id: "scout",
    name_he: "סקאוט",
    role_he: "סוכן איסוף",
    emoji: "🛰️",
    tier: 2,
    tier_label_he: "כלים",
    persona_he: "עקשן, לא מוותר על קישור שבור",
  },
  {
    id: "lexi",
    name_he: "לקסי",
    role_he: "אנליסט לקסיקון",
    emoji: "📖",
    tier: 1,
    tier_label_he: "לקסיקון",
    persona_he: "מדויק, סופר כל מילה",
  },
  {
    id: "librarian",
    name_he: "הספרנית",
    role_he: "סוכנת אחזור RAG",
    emoji: "🗂️",
    tier: 3,
    tier_label_he: "אחזור",
    persona_he: "מוצאת את אותו סיפור גם בלי מילה משותפת",
  },
  {
    id: "nova",
    name_he: "נובה",
    role_he: "סוכנת מסגור",
    emoji: "🤖",
    tier: 4,
    tier_label_he: "מודל שפה",
    persona_he: "קוראת מי המבצע ולמי מיוחסת האחריות",
  },
  {
    id: "amit",
    name_he: "עמית",
    role_he: "המאמת",
    emoji: "🎓",
    tier: 5,
    tier_label_he: "אימות",
    persona_he: "ביטוי שאינו בטקסט לא עולה למסך",
  },
];

/**
 * Per-agent hue, keyed by tier (1–5). CVD-validated set on the kiosk surface
 * (#0d1424) via the dataviz validator — do not reorder or restep casually.
 * Every colored surface also carries the agent's emoji + name (secondary
 * encoding), so color never stands alone.
 */
const TIER_COLORS: Record<number, string> = {
  1: "#3987e5", // blue
  2: "#d95926", // orange
  3: "#199e70", // aqua
  4: "#c98500", // yellow
  5: "#d55181", // magenta
};

export function agentColor(agent: AgentInfo | undefined): string {
  if (!agent) return "#64748b";
  return TIER_COLORS[agent.tier] ?? "#64748b";
}

/** message-kind → beam color (per spec: data=blue, request=purple, challenge=orange, help=pink) */
export const KIND_COLORS: Record<MessageKind, string> = {
  data: "#60a5fa",
  request: "#a78bfa",
  response: "#7dd3fc",
  challenge: "#fb923c",
  help: "#f472b6",
};

export const KIND_LABELS_HE: Record<MessageKind, string> = {
  data: "נתונים",
  request: "בקשה",
  response: "תשובה",
  challenge: "ערעור",
  help: "עזרה",
};

export const STATE_LABELS_HE: Record<AgentStateId, string> = {
  idle: "ממתין",
  working: "עובד",
  waiting: "מחכה",
  done: "סיים",
  error: "שגיאה",
};

export const PHASE_LABELS_HE: Record<PhaseId, string> = {
  intake: "איסוף כתבות",
  retrieve: "אחזור סמנטי",
  framing: "חילוץ מסגור · אימות",
  audience: "פערי קהל",
  profile: "פרופיל מצטבר",
};

export const STRATEGY_LABELS_HE: Record<ScrapeStrategy, string> = {
  direct: "גישה ישירה",
  alt_selector: "סלקטור חלופי",
  archive_org: "archive.org",
  rss: "RSS",
  skip: "דילוג",
};

/** Fixed vertical order of the scrape decision tree. */
export const STRATEGY_ORDER: ScrapeStrategy[] = [
  "direct",
  "alt_selector",
  "archive_org",
  "rss",
  "skip",
];

export function findAgent(
  agents: AgentInfo[],
  id: string,
): AgentInfo | undefined {
  return agents.find((a) => a.id === id);
}
