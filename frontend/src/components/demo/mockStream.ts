import type { DemoEvent, SceneId } from "./types";

/**
 * Scripted mock event loop (~2 min) covering every event type in
 * demo/EVENTS.md, scene by scene. Used with ?mock=1 or automatically when the
 * backend is unreachable — this is also the kiosk fallback. Gates auto-clear
 * (there is no backend to advance).
 *
 * The content is NOT invented: it is the real showcase event and the real
 * measured profile from the snapshot, copied here so the fallback screen shows
 * true numbers rather than plausible-looking ones. The header still marks the
 * run as "מצב הדגמה", because nothing here is being computed live.
 */

/** Omit that distributes over a union (plain Omit collapses DemoEvent). */
type DistributiveOmit<T, K extends PropertyKey> = T extends unknown
  ? Omit<T, K>
  : never;

type MockEvent = DistributiveOmit<DemoEvent, "ts">;

type TimedEvent = { at: number; ev: MockEvent };

const T_MAKO = "למרות ההודעה על חזרה לשגרה: הכאוס בנתב\"ג נמשך אל תוך הלילה";
const T_YNET =
  "בנתב\"ג הודיעו על צעדים להקלת העומס, אך החשש מכאוס בחגים עדיין קיים | זו הסיבה";
const T_HAARETZ =
  "נתניהו הורה להדיח מהליכוד את יו\"ר ועד העובדים ברשות שדות התעופה עקב השביתה";
const U_MAKO = "https://www.mako.co.il/news-israel/2026_q3/Article-a1.htm";
const U_YNET = "https://www.ynet.co.il/news/article/rj8kp11";
const U_HAARETZ = "https://www.haaretz.co.il/news/politi/2026-08-24/ty-article";

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
    push(0, { type: "scene", scene, idx, total: 9, title_he, subtitle_he });
  const gate = (gate_id: string, hint_he: string, holdMs = 4_000) => {
    push(600, { type: "gate", gate_id, hint_he, autoplay_ms: holdMs });
    push(holdMs, { type: "gate_cleared", gate_id });
  };

  push(0, {
    type: "llm_mode",
    mode: "cached",
    label_he: "פלט מודל אמיתי, מוקלט מראש",
  });

  /* ── scene 1 · architecture ───────────────────────────────────── */
  scene("arch", 1, "הארכיטקטורה", "הפייפליין הדטרמיניסטי — הבסיס של הכל");
  const arch: Array<[string, string, string]> = [
    ["crawl", "Crawl", "קרולרים לכל מקור — דדופ לפי sha256 של הכתובת"],
    ["windows", "Windows", "כל כתבה נחתכת לחלונות משפטים"],
    ["comments", "Comments", "איסוף תגובות גולשים לכתבות בנות 24+ שעות"],
    ["lexicon", "Lexicon", "מילון קיטוב שנבנה פעם אחת אופליין"],
    ["analyze", "Analyze", "ספירה ודומיננטיות לכל חלון — דטרמיניסטי"],
    ["db", "Postgres", "בדיוק בסדר הזה רץ הכל ב־GitHub Actions כל 6 שעות"],
    ["agents", "שכבת הסוכנים", "איסוף, לקסיקון, אחזור, מסגור ואימות"],
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
    push(1_500, {
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
  scene(
    "intake",
    2,
    "איסוף — עוד בלי AI",
    "מנה מעורבת של כתבות; קישור שבור מפעיל עץ החלטות, לא קריסה",
  );
  push(0, { type: "phase", phase: "intake", label_he: "איסוף כתבות" });
  push(200, {
    type: "agent_status",
    agent: "scout",
    state: "working",
    task_he: "מושך את המנה הבאה…",
  });
  push(200, {
    type: "reasoning",
    agent: "scout",
    level: "info",
    text_he: "נחיל הסוכנים מתעורר — מושכים את המנה הבאה מהמקורות",
  });
  push(800, { type: "scrape_step", url: U_YNET, article_title: T_YNET, step_idx: 0, strategy: "direct", status: "trying", note_he: "" });
  push(1_200, { type: "scrape_step", url: U_YNET, article_title: T_YNET, step_idx: 0, strategy: "direct", status: "success", note_he: "נטען מהמקור" });
  push(700, { type: "scrape_step", url: U_MAKO, article_title: T_MAKO, step_idx: 0, strategy: "direct", status: "trying", note_he: "" });
  push(1_100, { type: "scrape_step", url: U_MAKO, article_title: T_MAKO, step_idx: 0, strategy: "direct", status: "failed", note_he: "‏404 — הכתובת השתנתה" });
  push(200, { type: "reasoning", agent: "scout", level: "warn", text_he: "קישור בעייתי — מפעיל עץ החלטות (3 שלבים)" });
  push(900, { type: "scrape_step", url: U_MAKO, article_title: T_MAKO, step_idx: 1, strategy: "alt_selector", status: "failed", note_he: "מבנה הדף שונה" });
  push(1_100, { type: "scrape_step", url: U_MAKO, article_title: T_MAKO, step_idx: 2, strategy: "archive_org", status: "success", note_he: "נמצא עותק בארכיון האינטרנט" });
  push(300, { type: "reasoning", agent: "scout", level: "decision", text_he: "שוחזר בהצלחה — אף כתבה לא הולכת לאיבוד" });
  push(600, { type: "scrape_step", url: U_HAARETZ, article_title: T_HAARETZ, step_idx: 0, strategy: "direct", status: "success", note_he: "נטען מהמקור" });
  push(400, { type: "agent_status", agent: "scout", state: "idle", task_he: "" });
  gate("s2-intake", "אל הליבה הדטרמיניסטית — הלקסיקון");

  /* ── scene 3 · lexicon ────────────────────────────────────────── */
  scene(
    "lexicon",
    3,
    "האלגוריתם — עדיין בלי AI",
    "חלונות, ספירה, דומיננטיות — כך נולדים השדות שבאתר",
  );
  push(400, {
    type: "agent_status",
    agent: "lexi",
    state: "working",
    task_he: "מריץ לקסיקון…",
  });
  push(1_200, {
    type: "showcase",
    article_id: "mock-mako",
    title: T_MAKO,
    source: "mako",
    source_he: "mako",
    url: U_MAKO,
    published_at: "2026-08-24",
    excerpt:
      "השיבושים בנתב\"ג שהותירו אלפי נוסעים מול תורים, עיכובים וחוסר ודאות נמשכים אל תוך הלילה, למרות ההודעה על חזרה לשגרה",
    windows: 34,
    mean_dominance: 0.68,
    max_dominance: 1.0,
    comments: 511,
    audience_mean: 0.0208,
    audience_p85: 0.0556,
    top_category_he: "כלכלה",
    top_count: 22,
  });
  push(600, {
    type: "reasoning",
    agent: "lexi",
    level: "decision",
    text_he: "ספירה דטרמיניסטית, אפס קריאות למודל שפה",
  });
  push(400, { type: "agent_status", agent: "lexi", state: "idle", task_he: "" });
  gate("s3-lexicon", "ומי עוד סיקר את הסיפור הזה? — אחזור סמנטי");

  /* ── scene 4 · event map ──────────────────────────────────────── */
  scene(
    "event_map",
    4,
    "כאן נכנס ה־AI: מי עוד סיקר את זה?",
    "כותרות של אותו אירוע כמעט לא חולקות מילים",
  );
  push(0, { type: "phase", phase: "retrieve", label_he: "אחזור סמנטי" });
  push(300, {
    type: "agent_status",
    agent: "librarian",
    state: "working",
    task_he: "מחפשת את אותו סיפור…",
  });
  push(900, {
    type: "reasoning",
    agent: "librarian",
    level: "warn",
    text_he: "חיפוש מילולי על הכותרות מוצא 0 מתוך 2 — הכותרות לא חולקות מילים",
  });
  push(1_400, {
    type: "event_map",
    event_id: "mock-event",
    seed_title: T_MAKO,
    seed_source: "mako",
    topic_he: "כלכלה",
    keyword_found: 0,
    semantic_found: 2,
    total: 2,
    versions: [
      { source: "ynet", source_he: "ynet", title: T_YNET, score: 0.925, keyword_overlap: 0.043 },
      { source: "haaretz", source_he: "הארץ", title: T_HAARETZ, score: 0.903, keyword_overlap: 0.0 },
    ],
  });
  push(900, {
    type: "message",
    from: "librarian",
    to: "nova",
    kind: "data",
    summary_he: "2 גרסאות של אותו אירוע",
  });
  push(600, { type: "agent_status", agent: "librarian", state: "idle", task_he: "" });
  gate("s4-event_map", "איך כל אחת מספרת את זה? — מסגור");

  /* ── scene 5 · framing + verifier ─────────────────────────────── */
  scene(
    "framing",
    5,
    "המסגור: מי המבצע, למי האחריות",
    "מודל שפה מחלץ את מה שהלקסיקון עיוור אליו — ומאמת פוסל מה שאינו בטקסט",
  );
  push(0, { type: "phase", phase: "framing", label_he: "חילוץ מסגור · אימות" });
  push(400, {
    type: "reasoning",
    agent: "nova",
    level: "decision",
    text_he: "הלקסיקון סופר מילים. מי מוצג כמבצע ולמי מיוחסת האחריות — את זה אני מחלצת",
  });
  push(900, {
    type: "framing",
    article_id: "mock-mako",
    source: "mako",
    source_he: "mako",
    title: T_MAKO,
    url: U_MAKO,
    actor: null,
    responsibility: "ועד העובדים והנהלת רשת",
    voice: "passive",
    lead_perspective: "נוסעים",
    loaded_terms: ["כאוס"],
    lex_top_he: "כלכלה",
  });
  push(1_500, {
    type: "framing",
    article_id: "mock-ynet",
    source: "ynet",
    source_he: "ynet",
    title: T_YNET,
    url: U_YNET,
    actor: "רשות שדות התעופה",
    responsibility: null,
    voice: "active",
    lead_perspective: "נתב\"ג",
    loaded_terms: ["כאוס", "חשש"],
    lex_top_he: "כלכלה",
  });
  push(1_500, {
    type: "framing",
    article_id: "mock-haaretz",
    source: "haaretz",
    source_he: "הארץ",
    title: T_HAARETZ,
    url: U_HAARETZ,
    actor: "נתניהו",
    responsibility: "יו\"ר ועד העובדים ברשות שדות התעופה",
    voice: "active",
    lead_perspective: "נתניהו",
    loaded_terms: ["פרועה", "לא חוקית"],
    lex_top_he: "פוליטיקה",
  });
  push(1_600, {
    type: "contrast",
    event_id: "mock-event",
    shared_he:
      "כל הגרסאות מסכימות על כך שהיו שיבושים משמעותיים בנתב\"ג בעקבות השביתה.",
    per_source: [
      {
        source: "mako",
        source_he: "mako",
        distinctive_he:
          "הגרסה מדגישה את הכאוס הנמשך ואת חילופי ההאשמות בין ועד העובדים להנהלה.",
        evidence_he: "הכאוס נמשך אל תוך הלילה",
      },
      {
        source: "ynet",
        source_he: "ynet",
        distinctive_he:
          "הגרסה מתמקדת בצעדים שננקטו להקלת העומס ובחשש מעיצומים עתידיים.",
        evidence_he: null,
      },
      {
        source: "haaretz",
        source_he: "הארץ",
        distinctive_he:
          "הגרסה מתמקדת בהחלטת נתניהו להדיח את יו\"ר ועד העובדים בעקבות השביתה.",
        evidence_he: null,
      },
    ],
  });
  push(1_400, {
    type: "reasoning",
    agent: "amit",
    level: "decision",
    text_he:
      "אני לא דעה שנייה של מודל. כל ביטוי חייב להימצא באותו טקסט שנובה קראה",
  });
  push(1_200, {
    type: "verifier",
    checked_terms: 5,
    dropped_terms: [],
    rejected_quotes: [
      { source_he: "ynet", quote: "החשש מכאוס בחגים עדיין קיים לדברי הרשות" },
    ],
    terms_total: 250,
    terms_rejected: 4,
    actors_total: 142,
    actors_rejected: 0,
    quotes_total: 144,
    quotes_rejected: 33,
    lead_chars: 500,
  });
  gate("s5-framing", "ומה הקוראים עשו מזה? — הקהל");

  /* ── scene 6 · audience ───────────────────────────────────────── */
  scene(
    "audience",
    6,
    "אותו אירוע, קהלים שונים",
    "מה הקוראים עשו מהסיפור — ומתי חטפו אותו לנושא אחר",
  );
  push(0, { type: "phase", phase: "audience", label_he: "פערי קהל" });
  push(500, {
    type: "audience_gap",
    article_id: "mock-mako",
    source: "mako",
    source_he: "mako",
    title: T_MAKO,
    mean_dominance: 0.68,
    num_comments: 511,
    audience_mean: 0.0208,
    audience_p85: 0.0556,
    article_topic_he: "כלכלה",
    comment_topic_he: "פוליטיקה",
    hijacked: true,
    top_comment: {
      text: "ככה זה כשאין משילות כלל. דרך אגב, ועד העובדים הבריוני הוא ליכודניק",
      like_count: 0,
    },
  });
  push(1_600, {
    type: "audience_gap",
    article_id: "mock-ynet",
    source: "ynet",
    source_he: "ynet",
    title: T_YNET,
    mean_dominance: 0.811,
    num_comments: 26,
    audience_mean: 0.0231,
    audience_p85: 0.069,
    article_topic_he: "כלכלה",
    comment_topic_he: "פוליטיקה",
    hijacked: true,
    top_comment: { text: "איכשהו, כולם קשורים לליכוד, שמתם לב?", like_count: 51 },
  });
  push(1_600, {
    type: "audience_gap",
    article_id: "mock-haaretz",
    source: "haaretz",
    source_he: "הארץ",
    title: T_HAARETZ,
    mean_dominance: 0.444,
    num_comments: 13,
    audience_mean: 0.0195,
    audience_p85: 0.0588,
    article_topic_he: "פוליטיקה",
    comment_topic_he: "פוליטיקה",
    hijacked: false,
    top_comment: {
      text: "ואת כל זה הוא עשה מתוך ההופעה של עדן בן זקן?? מנהיג דגול",
      like_count: 18,
    },
  });
  push(1_500, {
    type: "insight",
    question_he: "על מה הקוראים בעצם דיברו?",
    text_he:
      "ב־2 מתוך 3 הגרסאות הנושא שהקוראים דיברו עליו שונה מהנושא של הכתבה — mako: כלכלה ← פוליטיקה, ynet: כלכלה ← פוליטיקה",
    source_he: "ספירת לקסיקון על טקסט התגובות, אותו מילון בדיוק",
  });
  gate("s6-audience", "ומה זה אומר על הערוץ עצמו? — פרופיל");

  /* ── scene 7 · profile ────────────────────────────────────────── */
  scene(
    "profile",
    7,
    "פרופיל הערוץ",
    "כל ערוץ מול חציון אותו אירוע — ומה עוד אין מספיק ראיות לומר",
  );
  push(0, { type: "phase", phase: "profile", label_he: "פרופיל מצטבר" });
  push(500, {
    type: "profile",
    events_total: 69,
    min_cell_events: 10,
    outlets: [
      { source: "ynet", n: 66, mean: 0.0173, lo: 0.0045, hi: 0.0309, significant: true, mix_top: [["ביטחון", 0.0075], ["משפט", -0.0062]] },
      { source: "mako", n: 51, mean: -0.0233, lo: -0.0379, hi: -0.0088, significant: true, mix_top: [["פוליטיקה", -0.0163], ["ביטחון", 0.0129]] },
      { source: "haaretz", n: 28, mean: -0.0224, lo: -0.0664, hi: 0.0158, significant: false, mix_top: [["ביטחון", -0.0422], ["משפט", 0.0241]] },
      { source: "news12", n: 1, mean: null, lo: null, hi: null, significant: false, mix_top: [["זהות/דת", -0.0278], ["פוליטיקה", 0.0171]] },
    ],
    curve_source: "ynet",
    curve_source_he: "ynet",
    sampling_curve: [
      { n: 3, mean: 0.0128, lo: -0.0297, hi: 0.0555, width: 0.0852 },
      { n: 5, mean: 0.0206, lo: -0.0206, hi: 0.0587, width: 0.0793 },
      { n: 10, mean: 0.0149, lo: -0.0188, hi: 0.048, width: 0.0668 },
      { n: 20, mean: 0.0133, lo: -0.0108, hi: 0.0369, width: 0.0478 },
      { n: 40, mean: 0.0157, lo: -0.0015, hi: 0.0325, width: 0.034 },
      { n: 66, mean: 0.0173, lo: 0.0045, hi: 0.0309, width: 0.0264 },
    ],
    topic_cells: [
      { source: "ynet", topic_he: "ביטחון", n: 30, mean: 0.0071, lo: -0.0105, hi: 0.0241, usable: true, significant: false, top_mix: [["ביטחון", -0.0267]] },
      { source: "mako", topic_he: "ביטחון", n: 28, mean: -0.0054, lo: -0.0215, hi: 0.0108, usable: true, significant: false, top_mix: [["ביטחון", 0.0303]] },
      { source: "ynet", topic_he: "פוליטיקה", n: 15, mean: 0.0257, lo: -0.0013, hi: 0.0504, usable: true, significant: false, top_mix: [["ביטחון", 0.0176]] },
      { source: "haaretz", topic_he: "פוליטיקה", n: 12, mean: -0.0145, lo: -0.0623, hi: 0.0296, usable: true, significant: false, top_mix: [["משפט", 0.0284]] },
      { source: "ynet", topic_he: "חברה", n: 9, mean: 0.0248, lo: -0.0069, hi: 0.0577, usable: false, significant: false, top_mix: [["חברה", 0.0192]] },
      { source: "haaretz", topic_he: "ביטחון", n: 8, mean: -0.0566, lo: -0.1214, hi: -0.0034, usable: false, significant: false, top_mix: [["ביטחון", -0.0761]] },
    ],
    change_scans: [
      { source: "ynet", topic_he: "ביטחון", n: 30, at: "2026-08-24 09:00", shift: -0.028, p_value: 0.107, detected: false, before_mean: 0.021, after_mean: -0.007, power_1sd: 0.68 },
      { source: "mako", topic_he: "ביטחון", n: 28, at: "2026-08-24 11:00", shift: 0.0276, p_value: 0.375, detected: false, before_mean: -0.019, after_mean: 0.009, power_1sd: 0.58 },
    ],
    power_table: [
      { n: 20, power_1sd: 0.47, power_half_sd: 0.17 },
      { n: 40, power_1sd: 0.77, power_half_sd: 0.26 },
      { n: 75, power_1sd: 0.97, power_half_sd: 0.42 },
    ],
    coverage: {
      ynet: { covered: 66, total_events: 69, share: 0.96, in_snapshot: 624 },
      mako: { covered: 51, total_events: 69, share: 0.74, in_snapshot: 290 },
      haaretz: { covered: 28, total_events: 69, share: 0.41, in_snapshot: 235 },
      news12: { covered: 1, total_events: 69, share: 0.01, in_snapshot: 20 },
      channel14: { covered: 0, total_events: 69, share: 0, in_snapshot: 9 },
    },
  });
  gate("s7-profile", "וכמה כל זה עלה? — כלכלת טוקנים", 6_000);

  /* ── scene 8 · economy ────────────────────────────────────────── */
  scene("economy", 8, "כלכלת טוקנים", "דטרמיניסטי כשאפשר, מודל שפה רק כשצריך");
  push(400, {
    type: "economy",
    model_calls: 214,
    cached_outputs: 214,
    total_tokens: 120_698,
    total_cost_usd: 0.0289,
    showtime_calls: 0,
    corpus_articles: 752,
    allllm_tokens_est: 789_600,
    allllm_cost_est: 0.1779,
    note_he: "אומדן: אותן כתבות אילו כל שלב היה קריאת מודל על הטקסט המלא",
  });
  push(1_200, {
    type: "reasoning",
    agent: "amit",
    level: "decision",
    text_he: "כל שכבת ה־AI עלתה $0.0289 — 214 קריאות, פעם אחת, אופליין",
  });
  gate("s8-economy", "לסיכום");

  /* ── scene 9 · summary ────────────────────────────────────────── */
  scene("summary", 9, "סיכום", "");
  push(400, {
    type: "run_summary",
    headline_he: "אותו אירוע, 3 מערכות, 3 מסגורים שונים",
    event_headline: T_MAKO,
    topic_he: "כלכלה",
    keyword_found: 0,
    keyword_total: 2,
    events_total: 69,
    outlets: [
      { source_he: "ynet", n: 66, mean: 0.0173, significant: true },
      { source_he: "mako", n: 51, mean: -0.0233, significant: true },
      { source_he: "הארץ", n: 28, mean: -0.0224, significant: false },
    ],
    terms_total: 250,
    terms_rejected: 4,
    quotes_total: 144,
    quotes_rejected: 33,
    links_recovered: 1,
    dropped: 0,
    total_cost_usd: 0.0289,
  });
  gate("s9-summary", "ריצה חדשה — סיפור אחר", 9_000);
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
