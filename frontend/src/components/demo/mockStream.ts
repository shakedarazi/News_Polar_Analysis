import type { DemoEvent, MetricEvent } from "./types";

/**
 * Scripted mock event loop (~95s) covering every event type in
 * demo/EVENTS.md. Used with ?mock=1 or automatically when the backend is
 * unreachable — this is also the kiosk fallback.
 */

/** Omit that distributes over a union (plain Omit collapses DemoEvent). */
type DistributiveOmit<T, K extends PropertyKey> = T extends unknown
  ? Omit<T, K>
  : never;

type MockEvent = DistributiveOmit<DemoEvent, "ts">;

type TimedEvent = { at: number; ev: MockEvent };

const URL_1 = "https://www.ynet.co.il/news/article/rj8kp11";
const URL_2 = "https://www.israelhayom.co.il/news/politics/article/1873";
const URL_3 = "https://www.maariv.co.il/breaking-news/article-1129";

function metric(
  round: number,
  label_he: string,
  accuracy: number,
  n: number,
  learned: number,
  duration_s: number,
): Omit<MetricEvent, "ts"> {
  return { type: "metric", round, label_he, accuracy, n, learned, duration_s };
}

function buildTimeline(): TimedEvent[] {
  const tl: TimedEvent[] = [];
  const push = (at: number, ev: TimedEvent["ev"]) => tl.push({ at, ev });

  /* ── round 1 · intake ─────────────────────────────────────────── */
  push(0, {
    type: "phase",
    phase: "intake",
    label_he: "איסוף כתבות",
    round: 1,
    total_rounds: 3,
    round_label_he: "סבב 1 — בלי RAG",
  });
  push(200, { type: "agent_status", agent: "scout", state: "working", task_he: "סורק 8 קישורים…" });
  push(400, { type: "reasoning", agent: "scout", level: "info", text_he: "התחלתי סריקה של 8 קישורים מ־3 אתרי חדשות" });

  // URL 1 — direct success
  push(1_200, { type: "scrape_step", url: URL_1, article_title: "הקבינט אישר את מתווה הסיוע ההומניטרי", step_idx: 0, strategy: "direct", status: "trying", note_he: "" });
  push(2_600, { type: "scrape_step", url: URL_1, article_title: "הקבינט אישר את מתווה הסיוע ההומניטרי", step_idx: 0, strategy: "direct", status: "success", note_he: "נטען ב־0.8 שניות" });
  push(2_900, { type: "message", from: "scout", to: "nova", kind: "data", summary_he: "כתבה 1/8 נאספה" });

  // URL 2 — direct fails → selector fails → archive.org succeeds
  push(3_800, { type: "scrape_step", url: URL_2, article_title: "מחלוקת בקואליציה סביב תקציב הביטחון", step_idx: 0, strategy: "direct", status: "trying", note_he: "" });
  push(5_200, { type: "scrape_step", url: URL_2, article_title: "מחלוקת בקואליציה סביב תקציב הביטחון", step_idx: 0, strategy: "direct", status: "failed", note_he: "403 — חסימת בוטים" });
  push(5_400, { type: "reasoning", agent: "scout", level: "warn", text_he: "האתר חוסם — עובר לסלקטור חלופי" });
  push(5_600, { type: "scrape_step", url: URL_2, article_title: "מחלוקת בקואליציה סביב תקציב הביטחון", step_idx: 1, strategy: "alt_selector", status: "trying", note_he: "" });
  push(7_000, { type: "scrape_step", url: URL_2, article_title: "מחלוקת בקואליציה סביב תקציב הביטחון", step_idx: 1, strategy: "alt_selector", status: "failed", note_he: "התבנית השתנתה" });
  push(7_200, { type: "message", from: "scout", to: "librarian", kind: "help", summary_he: "צריך עותק ארכיון" });
  push(7_400, { type: "scrape_step", url: URL_2, article_title: "מחלוקת בקואליציה סביב תקציב הביטחון", step_idx: 2, strategy: "archive_org", status: "trying", note_he: "" });
  push(9_200, { type: "scrape_step", url: URL_2, article_title: "מחלוקת בקואליציה סביב תקציב הביטחון", step_idx: 2, strategy: "archive_org", status: "success", note_he: "עותק מ־archive.org" });
  push(9_400, { type: "reasoning", agent: "scout", level: "decision", text_he: "קישור שבור שוחזר דרך archive.org ✓" });

  // URL 3 — everything fails → skip
  push(10_200, { type: "scrape_step", url: URL_3, article_title: "עלייה חדה במחירי הדיור במרכז", step_idx: 0, strategy: "direct", status: "trying", note_he: "" });
  push(11_400, { type: "scrape_step", url: URL_3, article_title: "עלייה חדה במחירי הדיור במרכז", step_idx: 0, strategy: "direct", status: "failed", note_he: "404" });
  push(11_700, { type: "scrape_step", url: URL_3, article_title: "עלייה חדה במחירי הדיור במרכז", step_idx: 1, strategy: "alt_selector", status: "failed", note_he: "" });
  push(12_300, { type: "scrape_step", url: URL_3, article_title: "עלייה חדה במחירי הדיור במרכז", step_idx: 2, strategy: "archive_org", status: "trying", note_he: "" });
  push(13_600, { type: "scrape_step", url: URL_3, article_title: "עלייה חדה במחירי הדיור במרכז", step_idx: 2, strategy: "archive_org", status: "failed", note_he: "אין עותק" });
  push(13_900, { type: "scrape_step", url: URL_3, article_title: "עלייה חדה במחירי הדיור במרכז", step_idx: 3, strategy: "rss", status: "failed", note_he: "לא בפיד" });
  push(14_200, { type: "scrape_step", url: URL_3, article_title: "עלייה חדה במחירי הדיור במרכז", step_idx: 4, strategy: "skip", status: "skipped", note_he: "הכתבה דולגה" });
  push(14_400, { type: "reasoning", agent: "scout", level: "warn", text_he: "כתבה אחת דולגה — כל האסטרטגיות נכשלו" });
  push(14_700, { type: "agent_status", agent: "scout", state: "done", task_he: "7/8 כתבות נאספו" });
  push(14_800, { type: "tokens", agent: "scout", prompt: 640, completion: 42, cost_usd: 0.00014, total_tokens: 682, total_cost_usd: 0.00014 });

  /* ── round 1 · classify (no RAG) ──────────────────────────────── */
  push(15_500, {
    type: "phase",
    phase: "classify",
    label_he: "סיווג",
    round: 1,
    total_rounds: 3,
    round_label_he: "סבב 1 — בלי RAG",
  });
  push(15_700, { type: "agent_status", agent: "lexi", state: "working", task_he: "סופר מילות קיטוב…" });
  push(15_900, { type: "agent_status", agent: "nova", state: "working", task_he: "מסווגת: הקבינט אישר את מתווה…" });
  push(16_400, { type: "message", from: "lexi", to: "nova", kind: "data", summary_he: "ציון לקסיקון 0.72" });
  push(17_200, { type: "reasoning", agent: "lexi", level: "info", text_he: "זוהו 14 מילים מקטבות בכתבת הקבינט" });
  push(18_000, { type: "classification", article_id: "a1", title: "הקבינט אישר את מתווה הסיוע ההומניטרי", predicted: "פוליטיקה", reference: "פוליטיקה", correct: true, confidence: 0.71, method: "baseline" });
  push(18_200, { type: "tokens", agent: "nova", prompt: 812, completion: 64, cost_usd: 0.00021, total_tokens: 1_558, total_cost_usd: 0.00035 });
  push(20_500, { type: "classification", article_id: "a2", title: "מחלוקת בקואליציה סביב תקציב הביטחון", predicted: "כלכלה", reference: "ביטחון", correct: false, confidence: 0.48, method: "baseline" });
  push(20_800, { type: "reasoning", agent: "nova", level: "warn", text_he: "ביטחון עצמי נמוך (0.48) — בלי דוגמאות דומות קשה להכריע" });
  push(23_000, { type: "classification", article_id: "a3", title: "עלייה חדה במחירי הדיור במרכז", predicted: "כלכלה", reference: null, correct: null, confidence: 0.66, method: "baseline" });
  push(23_300, { type: "tokens", agent: "nova", prompt: 790, completion: 58, cost_usd: 0.0002, total_tokens: 2_406, total_cost_usd: 0.00055 });

  /* ── round 1 · analyze + wrap ─────────────────────────────────── */
  push(24_500, {
    type: "phase",
    phase: "analyze",
    label_he: "ניתוח קיטוב",
    round: 1,
    total_rounds: 3,
    round_label_he: "סבב 1 — בלי RAG",
  });
  push(24_800, { type: "agent_status", agent: "lexi", state: "working", task_he: "מחשב מדדי קיטוב…" });
  push(25_600, { type: "reasoning", agent: "lexi", level: "decision", text_he: "רמת הקיטוב הגבוהה ביותר: כתבות פוליטיקה (0.81)" });
  push(26_400, { type: "agent_status", agent: "lexi", state: "done" });
  push(26_600, { type: "agent_status", agent: "nova", state: "done" });
  push(27_500, { ...metric(1, "בלי RAG", 0.62, 8, 0, 41.2) });
  push(28_500, { type: "insight", question_he: "מה הנושא המקטב ביותר בסבב?", text_he: "כתבות על תקציב הביטחון ריכזו את שיא מילות הקיטוב — פי 2.3 מהממוצע", source_he: "מבוסס על נתוני הלקסיקון בלבד" });

  /* ── round 2 · retrieve (RAG on) ──────────────────────────────── */
  push(33_000, {
    type: "phase",
    phase: "retrieve",
    label_he: "אחזור RAG",
    round: 2,
    total_rounds: 3,
    round_label_he: "סבב 2 — עם RAG",
  });
  push(33_300, { type: "agent_status", agent: "librarian", state: "working", task_he: "מאחזרת שכנים דומים…" });
  push(33_600, { type: "message", from: "nova", to: "librarian", kind: "request", summary_he: "בקשת שכנים לכתבה 2" });
  push(35_000, { type: "reasoning", agent: "librarian", level: "info", text_he: "חיפוש וקטורי על 1,200 כתבות מתויגות" });
  push(36_200, { type: "message", from: "librarian", to: "nova", kind: "data", summary_he: "5 שכנים דומים" });
  push(36_500, { type: "reasoning", agent: "librarian", level: "decision", text_he: "3 מתוך 5 השכנים הקרובים מסווגים 'ביטחון'" });

  /* ── round 2 · classify with kNN ──────────────────────────────── */
  push(38_000, {
    type: "phase",
    phase: "classify",
    label_he: "סיווג",
    round: 2,
    total_rounds: 3,
    round_label_he: "סבב 2 — עם RAG",
  });
  push(38_300, { type: "agent_status", agent: "nova", state: "working", task_he: "מסווגת עם שכנים…" });
  push(39_500, {
    type: "classification",
    article_id: "a2",
    title: "מחלוקת בקואליציה סביב תקציב הביטחון",
    predicted: "ביטחון",
    reference: "ביטחון",
    correct: true,
    confidence: 0.84,
    method: "knn",
    neighbors: [
      { title: "דיוני התקציב: מערכת הביטחון דורשת תוספת", category: "ביטחון", score: 0.91 },
      { title: "הרמטכ\"ל הציג את צורכי הצבא לקבינט", category: "ביטחון", score: 0.87 },
      { title: "ויכוח קואליציוני על סדרי העדיפויות", category: "פוליטיקה", score: 0.82 },
    ],
  });
  push(39_800, { type: "tokens", agent: "nova", prompt: 1_050, completion: 71, cost_usd: 0.00027, total_tokens: 3_527, total_cost_usd: 0.00082 });
  push(40_100, { type: "reasoning", agent: "nova", level: "decision", text_he: "השכנים הכריעו: ביטחון (0.84) — התיקון של הסבב הקודם" });
  push(42_500, {
    type: "classification",
    article_id: "a4",
    title: "ההייטק מתאושש: זינוק בגיוסי הון",
    predicted: "כלכלה",
    reference: "כלכלה",
    correct: true,
    confidence: 0.9,
    method: "llm",
    neighbors: [
      { title: "גל גיוסים חדש בחברות הסטארט־אפ", category: "כלכלה", score: 0.93 },
      { title: "קרנות ההון סיכון חוזרות להשקיע", category: "כלכלה", score: 0.9 },
      { title: "שוק העבודה בהייטק מתייצב", category: "כלכלה", score: 0.86 },
    ],
  });
  push(42_800, { type: "tokens", agent: "nova", prompt: 995, completion: 63, cost_usd: 0.00025, total_tokens: 4_585, total_cost_usd: 0.00107 });

  /* ── round 2 · critique + debate ──────────────────────────────── */
  push(44_500, {
    type: "phase",
    phase: "critique",
    label_he: "ביקורת עמיתים",
    round: 2,
    total_rounds: 3,
    round_label_he: "סבב 2 — עם RAG",
  });
  push(44_800, { type: "agent_status", agent: "amit", state: "working", task_he: "בודק סיווגים חלשים…" });
  push(45_600, { type: "message", from: "amit", to: "nova", kind: "challenge", summary_he: "ערעור על כתבה 5" });
  push(46_200, { type: "agent_status", agent: "nova", state: "debating" });
  push(46_300, { type: "agent_status", agent: "amit", state: "debating" });
  push(46_500, {
    type: "debate_start",
    debate_id: "d1",
    article_id: "a5",
    title: "מחאת הסטודנטים: אלפים צעדו מול הקריה",
    participants: ["nova", "amit"],
    reason_he: "ביטחון נמוך (0.44)",
  });
  push(48_000, { type: "debate_turn", debate_id: "d1", agent: "amit", text_he: "סיווגת 'חברה', אבל מילות המפתח כאן פוליטיות מובהקות — 'קואליציה', 'ממשלה', 'מחאה'." });
  push(51_500, { type: "debate_turn", debate_id: "d1", agent: "nova", text_he: "המחאה אזרחית, לא מפלגתית. השכן הקרוב ביותר (0.79) מסווג 'חברה'." });
  push(55_000, { type: "debate_turn", debate_id: "d1", agent: "amit", text_he: "אבל שלושת הבאים אחריו מסווגים 'פוליטיקה', והכתבה מצטטת שרים בתגובה." });
  push(58_500, { type: "debate_turn", debate_id: "d1", agent: "nova", text_he: "מקבלת. ההקשר הפוליטי דומיננטי — משנה ל'פוליטיקה'." });
  push(61_000, {
    type: "debate_end",
    debate_id: "d1",
    verdict_he: "הסיווג שונה ל'פוליטיקה' בעקבות העימות",
    final_category: "פוליטיקה",
    changed: true,
  });
  push(61_200, { type: "tokens", agent: "amit", prompt: 1_420, completion: 180, cost_usd: 0.00046, total_tokens: 6_185, total_cost_usd: 0.00153 });
  push(61_400, { type: "agent_status", agent: "nova", state: "working" });
  push(61_500, { type: "agent_status", agent: "amit", state: "done" });
  push(62_000, { type: "reasoning", agent: "amit", level: "decision", text_he: "עימות אחד הסתיים בשינוי סיווג — הרשת למדה משהו" });
  push(63_000, { ...metric(2, "עם RAG", 0.78, 8, 0, 44.6) });

  /* ── round 3 · learn ──────────────────────────────────────────── */
  push(65_000, {
    type: "phase",
    phase: "learn",
    label_he: "למידה עצמית",
    round: 3,
    total_rounds: 3,
    round_label_he: "סבב 3 — עם RAG + למידה",
  });
  push(65_300, { type: "agent_status", agent: "nova", state: "working", task_he: "מעדכנת זיכרון…" });
  push(66_000, { type: "learn", agent: "nova", text_he: "נוספה דוגמה מתוקנת: מחאת הסטודנטים → פוליטיקה", memory_size: 4 });
  push(68_000, { type: "learn", agent: "nova", text_he: "נוספה דוגמה מתוקנת: תקציב הביטחון → ביטחון", memory_size: 7 });
  push(68_400, { type: "reasoning", agent: "nova", level: "info", text_he: "7 דוגמאות מתוקנות בזיכרון — נשלפות בכל סיווג חדש" });

  /* ── round 3 · classify with memory ───────────────────────────── */
  push(70_000, {
    type: "phase",
    phase: "classify",
    label_he: "סיווג",
    round: 3,
    total_rounds: 3,
    round_label_he: "סבב 3 — עם RAG + למידה",
  });
  push(70_600, { type: "message", from: "nova", to: "librarian", kind: "request", summary_he: "שכנים + זיכרון" });
  push(71_800, { type: "message", from: "librarian", to: "nova", kind: "response", summary_he: "5 שכנים, 2 מהזיכרון" });
  push(73_000, {
    type: "classification",
    article_id: "a6",
    title: "עימות סוער במליאה על חוק הגיוס",
    predicted: "פוליטיקה",
    reference: "פוליטיקה",
    correct: true,
    confidence: 0.93,
    method: "knn",
    neighbors: [
      { title: "מחאת הסטודנטים: אלפים צעדו מול הקריה", category: "פוליטיקה", score: 0.88 },
      { title: "הקבינט אישר את מתווה הסיוע", category: "פוליטיקה", score: 0.85 },
      { title: "ויכוח קואליציוני על סדרי העדיפויות", category: "פוליטיקה", score: 0.83 },
    ],
  });
  push(73_300, { type: "reasoning", agent: "nova", level: "decision", text_he: "דוגמה מהזיכרון הכריעה — ביטחון עצמי 0.93" });
  push(73_500, { type: "tokens", agent: "nova", prompt: 1_130, completion: 66, cost_usd: 0.00028, total_tokens: 8_120, total_cost_usd: 0.00214 });
  push(76_000, { type: "classification", article_id: "a7", title: "שיא חדש בייצוא הגז הטבעי", predicted: "כלכלה", reference: "כלכלה", correct: true, confidence: 0.95, method: "knn" });
  push(77_500, { type: "agent_status", agent: "nova", state: "done" });
  push(78_500, { ...metric(3, "עם RAG+למידה", 0.88, 8, 7, 39.8) });

  /* ── summary ──────────────────────────────────────────────────── */
  push(80_000, {
    type: "phase",
    phase: "summary",
    label_he: "סיכום",
    round: 3,
    total_rounds: 3,
    round_label_he: "סבב 3 — עם RAG + למידה",
  });
  push(80_500, { type: "insight", question_he: "מה שיפר את הדיוק הכי הרבה?", text_he: "שליפת שכנים דומים (RAG) הוסיפה 16 נקודות דיוק; הזיכרון המתוקן הוסיף עוד 10", source_he: "מבוסס על מדדי הסבבים בלבד" });
  push(85_000, { type: "tokens", agent: "amit", prompt: 1_650, completion: 210, cost_usd: 0.00052, total_tokens: 9_980, total_cost_usd: 0.00266 });
  push(85_500, {
    type: "run_summary",
    rounds: [
      { ...metric(1, "בלי RAG", 0.62, 8, 0, 41.2), ts: 0 },
      { ...metric(2, "עם RAG", 0.78, 8, 0, 44.6), ts: 0 },
      { ...metric(3, "עם RAG+למידה", 0.88, 8, 7, 39.8), ts: 0 },
    ],
    total_articles: 24,
    debates: 3,
    links_recovered: 2,
    total_cost_usd: 0.0093,
    headline_he: "הדיוק עלה מ־62% ל־88% בשלושה סבבים",
  });
  push(95_500, { type: "reset" });

  return tl.sort((a, b) => a.at - b.at);
}

export interface MockController {
  stop: () => void;
}

/** Emits the scripted loop, repeating forever until stopped. */
export function startMockStream(
  emit: (ev: DemoEvent) => void,
): MockController {
  const timeline = buildTimeline();
  let stopped = false;
  const timers = new Set<ReturnType<typeof setTimeout>>();

  const schedule = (fn: () => void, ms: number) => {
    const t = setTimeout(() => {
      timers.delete(t);
      if (!stopped) fn();
    }, ms);
    timers.add(t);
  };

  const runLoop = () => {
    for (const { at, ev } of timeline) {
      schedule(() => emit({ ...ev, ts: Date.now() } as DemoEvent), at);
    }
    // restart shortly after the reset event
    const total = timeline[timeline.length - 1]?.at ?? 0;
    schedule(runLoop, total + 4_000);
  };

  runLoop();

  return {
    stop: () => {
      stopped = true;
      for (const t of timers) clearTimeout(t);
      timers.clear();
    },
  };
}
