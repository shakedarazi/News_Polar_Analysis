"use client";

import { MetricsChart } from "./MetricsChart";
import type { LearnEvent, MetricEvent } from "./types";

interface LearningSceneProps {
  metrics: MetricEvent[];
  learned: number;
  learnedItems: LearnEvent[];
}

/**
 * Scene 6 — what was learned: the accuracy arc front and center, next to the
 * actual corrected examples that entered the memory during this run.
 */
export function LearningScene({
  metrics,
  learned,
  learnedItems,
}: LearningSceneProps) {
  return (
    <section className="grid h-full min-h-0 grid-cols-[1.4fr_1fr] gap-4">
      <MetricsChart metrics={metrics} learned={learned} />

      <div className="dk-card flex min-h-0 flex-col gap-2 overflow-hidden p-5">
        <h2 className="flex items-center gap-2 text-lg font-bold text-[var(--dk-ink-2)]">
          <span aria-hidden>🧠</span> מה נכנס לזיכרון בריצה הזו
        </h2>
        <p className="text-[13px] leading-snug text-[var(--dk-ink-3)]">
          לא אימון מודל — דוגמאות מתוקנות מהדיבייטים שמצטרפות לאינדקס
          ול־few-shots של הסיווג הבא.
        </p>
        <ol className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden pt-1">
          {learnedItems.length === 0 && (
            <li className="dk-breathe pt-6 text-center text-[var(--dk-ink-3)]">
              לא נדרשו תיקונים בריצה הזו
            </li>
          )}
          {learnedItems.slice(-6).map((item, i) => (
            <li
              key={`${item.ts}-${i}`}
              className="dk-fade-up rounded-xl border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)] px-3.5 py-2.5 text-[15px] leading-snug"
            >
              {item.text_he}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
