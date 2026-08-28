import type { DemoEvent, MetricEvent, SceneId } from "./types";

/**
 * Scripted mock event loop (~2.5 min) covering every event type in
 * demo/EVENTS.md, scene by scene. Used with ?mock=1 or automatically when the
 * backend is unreachable — this is also the kiosk fallback. Gates auto-clear
 * (there is no backend to advance).
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

const TITLE_1 = "הקבינט אישר את מתווה הסיוע ההומניטרי";
const TITLE_2 = "מחלוקת בקואליציה סביב תקציב הביטחון";
const TITLE_3 = "עלייה חדה במחירי הדיור במרכז";

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
  let t = 0;
  const push = (delta: number, ev: MockEvent) => {
    t += delta;
    tl.push({ at: t, ev });
  };
  const scene = (
    scene: SceneId,
    idx: number,
    title_he: string,
    subtitle_he: string,
  ) =>
    push(0, { type: "scene", scene, idx, total: 8, title_he, subtitle_he });
  const gate = (gate_id: string, hint_he: string, holdMs = 4_000) => {
    push(600, { type: "gate", gate_id, hint_he, autoplay_ms: holdMs });
    push(holdMs, { type: "gate_cleared", gate_id });
  };

  push(0, { type: "llm_mode", mode: "offline", label_he: "מקומי · דטרמיניסטי" });

  /* ── scene 1 · architecture ───────────────────────────────────── */
  scene("arch", 1, "הארכיטקטורה", "הפייפליין הדטרמיניסטי — הבסיס של הכל");
  const arch: Array<[string, string, string]> = [
    ["crawl", "Crawl", "קרולרים לכל מקור — דדופ לפי sha256 של הכתובת"],
    ["windows", "Windows", "כל כתבה נחתכת לחלונות משפטים"],
    ["comments", "Comments", "איסוף תגובות גולשים לכתבות בנות 24+ שעות"],
    ["lexicon", "Lexicon", "מילון קיטוב שנבנה פעם אחת אופליין"],
    ["analyze", "Analyze", "ספירה ודומיננטיות לכל חלון — דטרמיניסטי"],
    ["db", "Postgres", "בדיוק בסדר הזה רץ הכל ב־GitHub Actions כל 6 שעות"],
    ["agents", "שכבת הסוכנים", "ומעל הכל: חמשת הסוכנים של הדמו"],
  ];
  arch.forEach(([step, label_he, detail_he], idx) => {
    push(400, {
      type: "arch_step",
      step,
      idx,
      label_he,
      detail_he,
      status: "active",
    } as MockEvent);
    push(1_700, {
      type: "arch_step",
      step,
      idx,
      label_he,
      detail_he,
      status: "done",
    } as MockEvent);
  });
  gate("s1-arch", "נכיר את הסוכנים — איסוף");

  /* ── scene 2 · intake ─────────────────────────────────────────── */
  scene("intake", 2, "איסוף — עוד בלי AI", "קרולרים דטרמיניסטיים; קישור שבור מפעיל עץ החלטות, לא קריסה");
  push(0, { type: "phase", phase: "intake", label_he: "איסוף כתבות", round: 1, total_rounds: 3, round_label_he: "סבב 1 — בלי RAG" });
  push(200, { type: "agent_status", agent: "scout", state: "working", task_he: "סורק 8 קישורים…" });
  push(200, { type: "reasoning", agent: "scout", level: "info", text_he: "התחלתי סריקה של 8 קישורים מ־3 אתרי חדשות" });

  // URL 1 — direct success
  push(800, { type: "scrape_step", url: URL_1, article_title: TITLE_1, step_idx: 0, strategy: "direct", status: "trying", note_he: "" });
  push(1_400, { type: "scrape_step", url: URL_1, article_title: TITLE_1, step_idx: 0, strategy: "direct", status: "success", note_he: "נטען ב־0.8 שניות" });
  push(300, { type: "message", from: "scout", to: "nova", kind: "data", summary_he: "כתבה 1/8 נאספה" });

  // URL 2 — direct fails → selector fails → archive.org succeeds
  push(900, { type: "scrape_step", url: URL_2, article_title: TITLE_2, step_idx: 0, strategy: "direct", status: "trying", note_he: "" });
  push(1_400, { type: "scrape_step", url: URL_2, article_title: TITLE_2, step_idx: 0, strategy: "direct", status: "failed", note_he: "403 — חסימת בוטים" });
  push(200, { type: "reasoning", agent: "scout", level: "warn", text_he: "האתר חוסם — עובר לסלקטור חלופי" });
  push(200, { type: "scrape_step", url: URL_2, article_title: TITLE_2, step_idx: 1, strategy: "alt_selector", status: "trying", note_he: "" });
  push(1_400, { type: "scrape_step", url: URL_2, article_title: TITLE_2, step_idx: 1, strategy: "alt_selector", status: "failed", note_he: "התבנית השתנתה" });
  push(200, { type: "message", from: "scout", to: "librarian", kind: "help", summary_he: "צריך עותק ארכיון" });
  push(200, { type: "scrape_step", url: URL_2, article_title: TITLE_2, step_idx: 2, strategy: "archive_org", status: "trying", note_he: "" });
  push(1_800, { type: "scrape_step", url: URL_2, article_title: TITLE_2, step_idx: 2, strategy: "archive_org", status: "success", note_he: "עותק מ־archive.org" });
  push(200, { type: "reasoning", agent: "scout", level: "decision", text_he: "קישור שבור שוחזר דרך archive.org ✓" });

  // URL 3 — everything fails → skip
  push(800, { type: "scrape_step", url: URL_3, article_title: TITLE_3, step_idx: 0, strategy: "direct", status: "failed", note_he: "404" });
  push(600, { type: "scrape_step", url: URL_3, article_title: TITLE_3, step_idx: 1, strategy: "alt_selector", status: "failed", note_he: "" });
  push(600, { type: "scrape_step", url: URL_3, article_title: TITLE_3, step_idx: 2, strategy: "archive_org", status: "failed", note_he: "אין עותק" });
  push(600, { type: "scrape_step", url: URL_3, article_title: TITLE_3, step_idx: 3, strategy: "rss", status: "failed", note_he: "לא בפיד" });
  push(400, { type: "scrape_step", url: URL_3, article_title: TITLE_3, step_idx: 4, strategy: "skip", status: "skipped", note_he: "הכתבה דולגה" });
  push(200, { type: "reasoning", agent: "scout", level: "warn", text_he: "כתבה אחת דולגה — כל האסטרטגיות נכשלו" });
  push(300, { type: "agent_status", agent: "scout", state: "done", task_he: "7/8 כתבות נאספו" });
  gate("s2-intake", "אל הליבה הדטרמיניסטית — הלקסיקון");

  /* ── scene 3 · lexicon core + product view ────────────────────── */
  scene("lexicon", 3, "האלגוריתם — עדיין בלי AI", "לקסיקון הקיטוב של בן שמחון — כך נולדים השדות שבאתר");
  push(300, { type: "agent_status", agent: "lexi", state: "working", task_he: "סופר מילות קיטוב…" });
  push(900, { type: "reasoning", agent: "lexi", level: "info", text_he: "14 חלונות, דומיננטיות ממוצעת 0.41" });
  push(600, {
    type: "showcase",
    article_id: "a2",
    title: TITLE_2,
    source: "ynet",
    url: URL_2,
    published_at: "2026-08-21",
    excerpt:
      "שר האוצר ושר הביטחון נפגשו הערב לדיון נוסף על תוספת התקציב למערכת הביטחון. בקואליציה מעריכים כי המחלוקת תגיע להכרעה רק בקבינט, בעוד גורמים באופוזיציה טוענים כי מדובר בסדרי עדיפויות שגויים",
    windows: 14,
    mean_dominance: 0.41,
    max_dominance: 0.8,
    comments: 52,
    audience_mean: 0.031,
    audience_p85: 0.07,
    top_category_he: "ביטחון",
    top_count: 9,
    reference: "ביטחון",
  });
  push(1_800, { type: "reasoning", agent: "lexi", level: "decision", text_he: "הלקסיקון (מחקר בן שמחון) מצביע חזק על ביטחון (9 מופעים)" });
  push(1_200, { type: "agent_status", agent: "lexi", state: "done" });
  gate("s3-lexicon", "ומאיפה מגיע ההקשר? — אחזור");

  /* ── scene 4 · RAG ────────────────────────────────────────────── */
  scene("rag", 4, "כאן נכנס ה־AI: אחזור (RAG)", "כתבות שתויגו בעבר משמשות תקדימים לכתבה החדשה");
  push(300, { type: "agent_status", agent: "librarian", state: "working", task_he: "מאחזרת שכנים דומים…" });
  push(700, { type: "reasoning", agent: "librarian", level: "info", text_he: "חיפוש וקטורי על 1,200 כתבות מתויגות" });
  push(900, {
    type: "retrieval",
    title: TITLE_2,
    neighbors: [
      { title: "דיוני התקציב: מערכת הביטחון דורשת תוספת", category: "ביטחון", score: 0.91 },
      { title: "הרמטכ\"ל הציג את צורכי הצבא לקבינט", category: "ביטחון", score: 0.87 },
      { title: "ויכוח קואליציוני על סדרי העדיפויות", category: "פוליטיקה", score: 0.82 },
      { title: "אושר תקציב הביניים למשרדי הממשלה", category: "פוליטיקה", score: 0.79 },
      { title: "בכירים לשעבר: הדרג המדיני מתמהמה", category: "ביטחון", score: 0.77 },
    ],
    tokens_full_est: 1_830,
    tokens_context_est: 140,
    note_he: "אומדן טוקנים להמחשה — כותרת + שכנים במקום הכתבה המלאה",
  });
  push(1_500, { type: "message", from: "librarian", to: "nova", kind: "data", summary_he: "5 שכנים דומים" });
  push(400, { type: "reasoning", agent: "librarian", level: "decision", text_he: "3 מתוך 5 השכנים הקרובים מסווגים 'ביטחון'" });
  push(600, { type: "agent_status", agent: "librarian", state: "done" });
  gate("s4-rag", "אל שלושת הסבבים — הקשת עולה");

  /* ── scene 5 · the rounds ─────────────────────────────────────── */
  scene("rounds", 5, "סיווג · ביקורת · שיפור", "חוקי אצבע ← RAG ← RAG + זיכרון");

  // round 1 — baseline
  push(0, { type: "phase", phase: "classify", label_he: "אחזור · סיווג · ביקורת", round: 1, total_rounds: 3, round_label_he: "סבב 1 — בלי RAG" });
  push(300, { type: "agent_status", agent: "nova", state: "working", task_he: "מסווגת בלי הקשר…" });
  push(500, { type: "reasoning", agent: "nova", level: "warn", text_he: "בסבב הזה אני עובדת עיוורת — בלי מאגר ובלי הקשר" });
  push(1_500, { type: "classification", article_id: "a1", title: TITLE_1, predicted: "פוליטיקה", reference: "פוליטיקה", correct: true, confidence: 0.71, method: "baseline" });
  push(2_400, { type: "classification", article_id: "a2", title: TITLE_2, predicted: "כלכלה", reference: "ביטחון", correct: false, confidence: 0.48, method: "baseline" });
  push(300, { type: "reasoning", agent: "nova", level: "warn", text_he: "ביטחון עצמי נמוך (0.48) — בלי דוגמאות דומות קשה להכריע" });
  push(2_000, { type: "classification", article_id: "a3", title: TITLE_3, predicted: "כלכלה", reference: null, correct: null, confidence: 0.66, method: "baseline" });
  push(1_500, metric(1, "בלי RAG", 0.57, 7, 0, 41.2));
  push(800, { type: "insight", question_he: "מה מוקד הקיטוב בסבב?", text_he: "כתבות על תקציב הביטחון ריכזו את שיא מילות הקיטוב — פי 2.3 מהממוצע", source_he: "מבוסס על נתוני הלקסיקון בלבד" });
  gate("s5-r1", "אל סבב 2 — מדליקים את ה־RAG", 5_000);

  // round 2 — kNN + debate
  push(0, { type: "phase", phase: "classify", label_he: "אחזור · סיווג · ביקורת", round: 2, total_rounds: 3, round_label_he: "סבב 2 — עם RAG" });
  push(300, { type: "message", from: "nova", to: "librarian", kind: "request", summary_he: "צריכה הקשר" });
  push(800, { type: "message", from: "librarian", to: "nova", kind: "data", summary_he: "5 שכנים דומים" });
  push(900, {
    type: "classification",
    article_id: "a2",
    title: TITLE_2,
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
  push(400, { type: "tokens", agent: "nova", prompt: 1_050, completion: 71, cost_usd: 0.00027, total_tokens: 3_527, total_cost_usd: 0.00082 });
  push(400, { type: "reasoning", agent: "nova", level: "decision", text_he: "השכנים הכריעו: ביטחון (0.84) — התיקון של הסבב הקודם" });

  push(1_500, { type: "agent_status", agent: "amit", state: "debating" });
  push(100, { type: "agent_status", agent: "nova", state: "debating" });
  push(200, { type: "message", from: "amit", to: "nova", kind: "challenge", summary_he: "אני לא משוכנע" });
  push(300, { type: "debate_start", debate_id: "d1", article_id: "a5", title: "מחאת הסטודנטים: אלפים צעדו מול הקריה", participants: ["nova", "amit"], reason_he: "ביטחון נמוך (0.44)" });
  push(1_500, { type: "debate_turn", debate_id: "d1", agent: "amit", text_he: "סיווגת 'חברה', אבל מילות המפתח כאן פוליטיות מובהקות — 'קואליציה', 'ממשלה', 'מחאה'." });
  push(3_400, { type: "debate_turn", debate_id: "d1", agent: "nova", text_he: "המחאה אזרחית, לא מפלגתית. השכן הקרוב ביותר (0.79) מסווג 'חברה'." });
  push(3_400, { type: "debate_turn", debate_id: "d1", agent: "amit", text_he: "אבל שלושת הבאים אחריו מסווגים 'פוליטיקה', והכתבה מצטטת שרים בתגובה." });
  push(3_400, { type: "debate_turn", debate_id: "d1", agent: "nova", text_he: "מקבלת. ההקשר הפוליטי דומיננטי — משנה ל'פוליטיקה'." });
  push(2_400, { type: "debate_end", debate_id: "d1", verdict_he: "הסיווג שונה ל'פוליטיקה' בעקבות העימות", final_category: "פוליטיקה", changed: true });
  push(300, { type: "learn", agent: "nova", text_he: "נלמד: \"מחאת הסטודנטים…\" → פוליטיקה", memory_size: 1 });
  push(200, { type: "agent_status", agent: "amit", state: "done" });
  push(100, { type: "agent_status", agent: "nova", state: "working" });
  push(1_200, metric(2, "עם RAG", 0.75, 8, 1, 44.6));
  gate("s5-r2", "אל סבב 3 — מוסיפים זיכרון", 5_000);

  // round 3 — memory
  push(0, { type: "phase", phase: "classify", label_he: "אחזור · סיווג · ביקורת", round: 3, total_rounds: 3, round_label_he: "סבב 3 — עם RAG + למידה" });
  push(400, { type: "reasoning", agent: "nova", level: "decision", text_he: "יש לי כבר תיקון בזיכרון + מאגר שגדל מהסבבים הקודמים" });
  push(1_400, {
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
    ],
  });
  push(400, { type: "reasoning", agent: "nova", level: "decision", text_he: "דוגמה מהזיכרון הכריעה — ביטחון עצמי 0.93" });
  push(2_000, { type: "classification", article_id: "a7", title: "שיא חדש בייצוא הגז הטבעי", predicted: "כלכלה", reference: "כלכלה", correct: true, confidence: 0.95, method: "knn" });
  push(300, { type: "agent_status", agent: "nova", state: "done" });
  push(1_200, metric(3, "עם RAG+למידה", 0.88, 8, 1, 39.8));
  gate("s5-r3", "מה נלמד? — סצנת הלמידה", 5_000);

  /* ── scene 6 · learning ───────────────────────────────────────── */
  scene("learning", 6, "למידה", "זיכרון מצטבר, לא אימון מודל");
  push(400, { type: "reasoning", agent: "nova", level: "decision", text_he: "דוגמה מתוקנת אחת בזיכרון — נשלפת בכל סיווג חדש" });
  push(1_800, { type: "reasoning", agent: "amit", level: "decision", text_he: "בלי לאמן אף מודל: 57% ← 88%. הצטברות ראיות, לא backprop" });
  gate("s6-learning", "וכמה כל זה עלה? — כלכלת טוקנים");

  /* ── scene 7 · economy ────────────────────────────────────────── */
  scene("economy", 7, "כלכלת טוקנים", "דטרמיניסטי כשאפשר, מודל שפה רק כשצריך");
  push(400, {
    type: "economy",
    total_tokens: 3_527,
    total_cost_usd: 0.0008,
    llm_calls: 2,
    allllm_tokens_est: 94_000,
    allllm_cost_est: 0.021,
    note_he: "אומדן: אותן 24 כתבות אילו כל שלב היה קריאת LLM על הטקסט המלא",
  });
  push(1_500, { type: "reasoning", agent: "amit", level: "decision", text_he: "2 קריאות מודל בלבד — כי הדטרמיניסטי עשה את רוב העבודה" });
  gate("s7-economy", "לסיכום");

  /* ── scene 8 · summary ────────────────────────────────────────── */
  scene("summary", 8, "סיכום", "");
  push(400, {
    type: "run_summary",
    rounds: [
      { ...metric(1, "בלי RAG", 0.57, 7, 0, 41.2), ts: 0 },
      { ...metric(2, "עם RAG", 0.75, 8, 1, 44.6), ts: 0 },
      { ...metric(3, "עם RAG+למידה", 0.88, 8, 1, 39.8), ts: 0 },
    ],
    total_articles: 23,
    debates: 1,
    links_recovered: 1,
    total_cost_usd: 0.0008,
    headline_he: "הדיוק עלה מ־57% ל־88% בשלושה סבבים",
  });
  gate("s8-summary", "ריצה חדשה מההתחלה", 9_000);
  push(500, { type: "reset" });

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
