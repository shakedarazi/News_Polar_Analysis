"use client";

/**
 * The hub: every part of the system is a door, and the presenter picks which
 * one to open.
 *
 * The nine-scene waterfall still exists and is still the best narrated path,
 * but it is now one tile among many rather than the only way in — an
 * exhibition audience arrives mid-run, asks about one thing, and leaves.
 */

export type ModuleId =
  | "scraping"
  | "algorithm"
  | "run"
  | "retrieval"
  | "framing"
  | "audience"
  | "stats"
  | "economy";

export interface ModuleDef {
  id: ModuleId;
  icon: string;
  title_he: string;
  sub_he: string;
  /** what the visitor will actually be shown — not a category label */
  promise_he: string;
  ready: boolean;
}

export const MODULES: ModuleDef[] = [
  {
    id: "run",
    icon: "▶",
    title_he: "ההצגה המונחית",
    sub_he: "תשע סצנות, סיפור אחד מקצה לקצה",
    promise_he:
      "המסלול המלא: מאיסוף ועד פרופיל הערוץ, עם עצירה לשאלות בכל שלב",
    ready: true,
  },
  {
    id: "scraping",
    icon: "🕸",
    title_he: "האיסוף",
    sub_he: "גילוי, זהות, עץ חילוץ, כשל",
    promise_he:
      "עץ ההחלטות שרץ על כל כתבה — ולמה הארץ יוצא 349 תווים בממוצע",
    ready: true,
  },
  {
    id: "algorithm",
    icon: "🧮",
    title_he: "האלגוריתם",
    sub_he: "חלונות, ניקוי, לקסיקון, מספרים",
    promise_he:
      "כל מדד עם הנוסחה שלו, התחום שלו, ומה ערך מסוים באמת אומר",
    ready: true,
  },
  {
    id: "retrieval",
    icon: "🗂",
    title_he: "אחזור סמנטי",
    sub_he: "איך נמצא אותו אירוע בלי מילה משותפת",
    promise_he: "17 מתוך 77 — כמה גרסאות חיפוש מילולי היה מוצא, ולמה",
    ready: true,
  },
  {
    id: "framing",
    icon: "🤖",
    title_he: "מסגור ואימות",
    sub_he: "מה המודל מחלץ ומה המאמת פוסל",
    promise_he: "כלל הפסילה, שיעוריו בפועל — וביקורת על המאמת עצמו",
    ready: true,
  },
  {
    id: "audience",
    icon: "💬",
    title_he: "אות הקהל",
    sub_he: "מה הקוראים עשו מהסיפור",
    promise_he: "שקלול לייקים, אחוזון 85, וחטיפת נושא",
    ready: true,
  },
  {
    id: "stats",
    icon: "📊",
    title_he: "הסטטיסטיקה",
    sub_he: "השוואה בתוך אירוע, בוטסטראפ, עוצמה",
    promise_he: "למה ממוצע גולמי לערוץ מודד בחירת סיפורים ולא מסגור",
    ready: true,
  },
  {
    id: "economy",
    icon: "🪙",
    title_he: "כלכלת טוקנים",
    sub_he: "מטמון, עלות, ומה נחסך",
    promise_he: "איפה בכלל נדרש מודל, וכמה עלתה כל השכבה",
    ready: true,
  },
];

interface HubSceneProps {
  onEnter: (id: ModuleId) => void;
}

export function HubScene({ onEnter }: HubSceneProps) {
  return (
    <section className="flex h-full min-h-0 flex-col gap-4">
      <header className="shrink-0 text-center">
        <h2 className="text-3xl font-black">מפת המערכת</h2>
        <p className="mt-1 text-[15px] text-[var(--dk-ink-2)]">
          בחרו נושא — או הקישו את המספר שלו. אין סדר מחייב.
        </p>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-4 grid-rows-2 gap-3">
        {MODULES.map((m, i) => (
          <button
            key={m.id}
            onClick={() => m.ready && onEnter(m.id)}
            disabled={!m.ready}
            className={`dk-card group flex flex-col items-start gap-1.5 p-4 text-right transition-all ${
              m.ready
                ? "hover:border-[var(--dk-accent)]/60 hover:bg-[var(--dk-accent-dim)]/30"
                : "cursor-not-allowed opacity-40"
            }`}
          >
            <div className="flex w-full items-center gap-2">
              <span className="text-2xl" aria-hidden>
                {m.icon}
              </span>
              <span className="text-[19px] font-bold">{m.title_he}</span>
              <span
                dir="ltr"
                className="ms-auto flex h-6 w-6 items-center justify-center rounded-md border border-[var(--dk-border)] font-mono text-[13px] text-[var(--dk-ink-3)]"
              >
                {i + 1}
              </span>
            </div>
            <div className="text-[13px] text-[var(--dk-ink-3)]">{m.sub_he}</div>
            <p className="mt-auto text-[13.5px] leading-snug text-[var(--dk-ink-2)]">
              {m.promise_he}
            </p>
            {!m.ready && (
              <span className="rounded-full border border-[var(--dk-warn)]/40 px-2 py-0.5 text-[11.5px] font-semibold text-[var(--dk-warn)]">
                בבנייה
              </span>
            )}
          </button>
        ))}
      </div>
    </section>
  );
}
