"use client";

import type { EconomyEvent } from "./types";

interface EconomySceneProps {
  economy: EconomyEvent | null;
}

/**
 * Scene 8 — what the AI layer cost, against the "everything through an LLM"
 * strawman the architecture avoids.
 *
 * The honest number here is the PREPARE cost, not the run cost: showtime
 * replays a cache and therefore spends nothing, and reporting $0 would be true
 * but meaningless. What the model actually cost is what it cost to build.
 *
 * Both sides come from the backend, and the strawman side is the one the
 * economy module measures (every article and every comment as its own call)
 * rather than a rounder estimate computed here — one quantity, one number.
 */
export function EconomyScene({ economy }: EconomySceneProps) {
  return (
    <section className="dk-card flex h-full flex-col items-center justify-center gap-8 p-8">
      <div className="grid w-[88%] grid-cols-2 gap-6">
        {/* what it really cost */}
        <div className="dk-scale-in flex flex-col items-center gap-2 rounded-2xl border border-[var(--dk-good)]/40 bg-[var(--dk-good)]/5 px-8 py-7">
          <div className="text-lg font-bold text-[var(--dk-good)]">
            כל שכבת ה־AI — פעם אחת, אופליין
          </div>
          <div className="text-6xl font-black tracking-tight" dir="ltr">
            ${(economy?.total_cost_usd ?? 0).toFixed(4)}
          </div>
          <div className="text-base text-[var(--dk-ink-2)]" dir="rtl">
            {(economy?.total_tokens ?? 0).toLocaleString("he-IL")} טוקנים ·{" "}
            {economy?.model_calls ?? 0} קריאות מודל
          </div>
          <div className="mt-1 text-center text-[14px] leading-snug text-[var(--dk-ink-3)]">
            חילוץ מסגור וניתוח קונטרסטיבי לכל האירועים. לקסיקון, אחזור, סטטיסטיקה
            ואימות — בלי טוקנים בכלל.
          </div>
          <div className="mt-1 rounded-full bg-[var(--dk-good)]/10 px-3 py-1 text-[13px] font-semibold text-[var(--dk-good)]">
            הריצה שעל המסך: {economy?.showtime_calls ?? 0} קריאות · $0
          </div>
        </div>

        {/* the strawman */}
        <div className="dk-scale-in flex flex-col items-center gap-2 rounded-2xl border border-[var(--dk-bad)]/30 bg-[var(--dk-bad)]/5 px-8 py-7 opacity-90">
          <div className="text-lg font-bold text-[var(--dk-bad)]">
            אילו הכל היה LLM
          </div>
          <div
            className="text-6xl font-black tracking-tight text-[var(--dk-ink-2)]"
            dir="ltr"
          >
            ${(economy?.allllm_cost_est ?? 0).toFixed(4)}
          </div>
          <div className="text-base text-[var(--dk-ink-2)]" dir="rtl">
            ‎~{(economy?.allllm_tokens_est ?? 0).toLocaleString("he-IL")} טוקנים
            ·{" "}
            {economy?.allllm_calls
              ? `${economy.allllm_calls.toLocaleString("he-IL")} קריאות`
              : `${(economy?.corpus_articles ?? 0).toLocaleString("he-IL")} כתבות`}
          </div>
          <div className="mt-1 text-center text-[14px] leading-snug text-[var(--dk-ink-3)]">
            {economy?.note_he ?? "אומדן — כל שלב כקריאת מודל על הטקסט המלא"}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 rounded-full border border-[var(--dk-border)] px-6 py-2.5 text-[15px] text-[var(--dk-ink-2)]">
        <span aria-hidden>⚙️</span>
        אותה ריצה בדיוק היא גם בנצ&#39;מרק חינמי ב־GitHub Actions — אם רווח
        הסמך מפסיק להצטמצם או שהאחזור מפסיק לנצח את חיפוש המילים, ה־CI נכשל
      </div>
    </section>
  );
}
