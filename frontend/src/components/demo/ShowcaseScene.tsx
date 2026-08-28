"use client";

import type { ShowcaseEvent } from "./types";

const SOURCE_LABELS: Record<string, string> = {
  ynet: "ynet",
  haaretz: "הארץ",
  mako: "מאקו",
  news12: "N12",
  reshet13: "רשת 13",
  channel14: "ערוץ 14",
};

interface FieldCardProps {
  label: string;
  value: string;
  note: string;
}

/** one product field + a one-line annotation of what it means */
function FieldCard({ label, value, note }: FieldCardProps) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/70 px-4 py-3">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[15px] font-semibold text-[var(--dk-ink-2)]">
          {label}
        </span>
        <span
          className="text-2xl font-bold tracking-tight text-[var(--dk-accent)]"
          dir="ltr"
        >
          {value}
        </span>
      </div>
      <p className="text-[13px] leading-snug text-[var(--dk-ink-3)]">{note}</p>
    </div>
  );
}

const fmt = (v: number | null | undefined, digits = 2): string =>
  v === null || v === undefined ? "—" : v.toFixed(digits);

interface ShowcaseSceneProps {
  showcase: ShowcaseEvent | null;
}

/**
 * Scene 3 — a real article, and the exact polarity fields the real Trust site
 * shows for it, each annotated. This is what turns the demo from "a nice
 * animation" into "this is how the product actually fills up".
 */
export function ShowcaseScene({ showcase }: ShowcaseSceneProps) {
  if (!showcase) {
    return (
      <section className="dk-card flex h-full items-center justify-center">
        <p className="dk-breathe text-xl text-[var(--dk-ink-3)]">
          לקסי בוחר כתבה להצגה מעמיקה…
        </p>
      </section>
    );
  }

  return (
    <section className="dk-card dk-scale-in flex h-full min-h-0 flex-col gap-4 overflow-hidden p-6">
      {/* the Ben Simhon algorithm in one strip — still zero AI */}
      <div className="flex items-center justify-center gap-2 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/70 px-4 py-2.5 text-[14px] text-[var(--dk-ink-2)]">
        <span className="font-bold text-[var(--dk-ink)]">
          האלגוריתם (בן שמחון), בלי AI:
        </span>
        <span>טקסט מלא</span>
        <span className="text-[var(--dk-accent)]">←</span>
        <span>חלונות משפטים</span>
        <span className="text-[var(--dk-accent)]">←</span>
        <span>ספירת מילים מהלקסיקון</span>
        <span className="text-[var(--dk-accent)]">←</span>
        <span>
          דומיננטיות = חלקה של הקטגוריה השלטת בכל חלון
        </span>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[1.15fr_1fr] gap-6 overflow-hidden">
      {/* the raw material — a real article from the snapshot */}
      <article className="flex min-h-0 flex-col gap-3 overflow-hidden">
        <div className="flex items-center gap-2 text-sm text-[var(--dk-ink-3)]">
          <span className="rounded-full border border-[var(--dk-border)] px-2.5 py-0.5 font-semibold text-[var(--dk-ink-2)]">
            {SOURCE_LABELS[showcase.source] ?? showcase.source}
          </span>
          {showcase.published_at && (
            <span dir="ltr">{showcase.published_at}</span>
          )}
          <span className="mr-auto rounded-full bg-[var(--dk-good)]/10 px-2.5 py-0.5 text-[12px] font-semibold text-[var(--dk-good)]">
            כתבה אמיתית מהמאגר
          </span>
        </div>
        <h3 className="text-[26px] font-bold leading-snug">{showcase.title}</h3>
        <p className="min-h-0 overflow-hidden text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
          {showcase.excerpt}…
        </p>
        {showcase.top_category_he && (
          <div className="mt-auto flex items-center gap-2 rounded-xl border border-[var(--dk-accent)]/30 bg-[var(--dk-accent-dim)] px-4 py-2.5 text-[15px]">
            <span className="text-xl">📖</span>
            <span>
              הלקסיקון מצא{" "}
              <b>
                {showcase.top_count} מופעי {showcase.top_category_he}
              </b>{" "}
              — ספירה דטרמיניסטית, מילה במילה
            </span>
          </div>
        )}
      </article>

      {/* the product view — the fields as the site shows them, annotated */}
      <div className="flex min-h-0 flex-col gap-2.5 overflow-hidden">
        <h4 className="flex items-center gap-2 text-lg font-bold text-[var(--dk-ink-2)]">
          <span aria-hidden>🖥️</span> כך זה נראה באתר Trust
        </h4>
        <FieldCard
          label="חלונות (windows)"
          value={String(showcase.windows)}
          note="הכתבה נחתכת למקטעי משפטים — כל חלון נבדק בנפרד מול הלקסיקון"
        />
        <FieldCard
          label="דומיננטיות ממוצעת"
          value={fmt(showcase.mean_dominance)}
          note="כמה קטגוריה אחת שולטת במילות הקיטוב של חלון (0–1); ממוצע על כל החלונות"
        />
        <FieldCard
          label="דומיננטיות שיא"
          value={fmt(showcase.max_dominance)}
          note="החלון הקיצוני ביותר בכתבה — פסקה אחת יכולה להקצין גם בכתבה מאוזנת"
        />
        <FieldCard
          label={`תגובות גולשים (${showcase.comments})`}
          value={fmt(showcase.audience_mean, 3)}
          note="audience_mean — שיעור מילות הקיטוב בתגובות, משוקלל לפי לייקים"
        />
        <FieldCard
          label="קיטוב קהל p85"
          value={fmt(showcase.audience_p85, 3)}
          note="audience_p85 — הזנב הקולני: ה־15% המקוטבים ביותר של התגובות"
        />
      </div>
      </div>
    </section>
  );
}
