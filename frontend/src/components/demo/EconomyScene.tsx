"use client";

import type { DemoState, EconomyEvent } from "./types";

interface EconomySceneProps {
  economy: EconomyEvent | null;
  tokens: DemoState["tokens"];
}

/**
 * Scene 7 — token economy: what this run actually cost vs. the
 * "everything through an LLM" strawman the architecture avoids.
 */
export function EconomyScene({ economy, tokens }: EconomySceneProps) {
  const actualTokens = economy?.total_tokens ?? tokens.totalTokens;
  const actualCost = economy?.total_cost_usd ?? tokens.totalCostUsd;

  return (
    <section className="dk-card flex h-full flex-col items-center justify-center gap-8 p-8">
      <div className="grid w-[88%] grid-cols-2 gap-6">
        {/* this run */}
        <div className="dk-scale-in flex flex-col items-center gap-2 rounded-2xl border border-[var(--dk-good)]/40 bg-[var(--dk-good)]/5 px-8 py-7">
          <div className="text-lg font-bold text-[var(--dk-good)]">
            הריצה הזו — דטרמיניסטי כשאפשר
          </div>
          <div className="text-6xl font-black tracking-tight" dir="ltr">
            ${actualCost.toFixed(4)}
          </div>
          <div className="text-base text-[var(--dk-ink-2)]" dir="rtl">
            {actualTokens.toLocaleString("he-IL")} טוקנים ·{" "}
            {economy?.llm_calls ?? 0} קריאות מודל
          </div>
          <div className="mt-1 text-center text-[14px] leading-snug text-[var(--dk-ink-3)]">
            לקסיקון, kNN וספירות — בלי טוקנים. מודל שפה רק בסיווגים קשים
            ובדיבייטים.
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
          </div>
          <div className="mt-1 text-center text-[14px] leading-snug text-[var(--dk-ink-3)]">
            {economy?.note_he ?? "אומדן — כל שלב כקריאת מודל על הטקסט המלא"}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 rounded-full border border-[var(--dk-border)] px-6 py-2.5 text-[15px] text-[var(--dk-ink-2)]">
        <span aria-hidden>⚙️</span>
        אותה ריצה בדיוק היא גם בנצ&#39;מרק חינמי ב־GitHub Actions — אם קשת
        הדיוק נשברת, ה־CI נכשל
      </div>
    </section>
  );
}
