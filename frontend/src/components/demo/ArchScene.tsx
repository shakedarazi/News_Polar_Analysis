"use client";

import type { ArchStepEvent, ArchStepId } from "./types";

const PIPELINE_ORDER: ArchStepId[] = [
  "crawl",
  "windows",
  "comments",
  "lexicon",
  "analyze",
  "db",
];

const STEP_ICONS: Record<ArchStepId, string> = {
  crawl: "🕸️",
  windows: "🪟",
  comments: "💬",
  lexicon: "📖",
  analyze: "🧮",
  db: "🗄️",
  agents: "🐝",
};

interface ArchSceneProps {
  steps: ArchStepEvent[];
}

/**
 * Scene 1 — the deterministic pipeline the whole project stands on
 * (crawl → windows → lexicon → analyze → DB), then the agent layer above it.
 * Driven by arch_step events from the backend.
 */
export function ArchScene({ steps }: ArchSceneProps) {
  const byStep = new Map(steps.map((s) => [s.step, s] as const));
  const active = steps.find((s) => s.status === "active") ?? null;
  const agents = byStep.get("agents");

  return (
    <section className="dk-card flex h-full flex-col items-center justify-center gap-10 p-8">
      {/* agent layer band — appears on top when its step fires */}
      <div
        className={`flex w-[82%] items-center justify-center gap-3 rounded-2xl border px-8 py-5 transition-all duration-700 ${
          agents
            ? "border-[var(--dk-accent)]/50 bg-[var(--dk-accent-dim)] opacity-100"
            : "border-dashed border-[var(--dk-border)] opacity-30"
        } ${agents?.status === "active" ? "dk-arch-active" : ""}`}
      >
        <span className="text-4xl">🐝</span>
        <div>
          <div className="text-2xl font-bold">
            {agents?.label_he ?? "שכבת הסוכנים"}
          </div>
          {agents && (
            <div className="text-base text-[var(--dk-ink-2)]">
              {agents.detail_he}
            </div>
          )}
        </div>
      </div>

      <div className="text-3xl text-[var(--dk-ink-3)]" aria-hidden>
        {agents ? "⬆" : " "}
      </div>

      {/* the deterministic pipeline, right-to-left */}
      <div className="flex w-full items-stretch justify-center gap-0">
        {PIPELINE_ORDER.map((id, i) => {
          const step = byStep.get(id);
          const isActive = step?.status === "active";
          const isDone = step?.status === "done";
          return (
            <div key={id} className="flex items-center">
              {i > 0 && (
                <span
                  className={`px-2 text-3xl transition-colors duration-500 ${
                    isDone || isActive
                      ? "text-[var(--dk-accent)]"
                      : "text-[var(--dk-ink-3)] opacity-40"
                  }`}
                  aria-hidden
                >
                  ←
                </span>
              )}
              <div
                className={`flex w-[148px] flex-col items-center gap-1.5 rounded-2xl border px-3 py-5 text-center transition-all duration-500 ${
                  isActive
                    ? "dk-arch-active border-[var(--dk-accent)] bg-[var(--dk-accent-dim)]"
                    : isDone
                      ? "border-[var(--dk-good)]/40 bg-[var(--dk-surface-2)]"
                      : "border-[var(--dk-border)] opacity-35"
                }`}
              >
                <span className="text-3xl">{STEP_ICONS[id]}</span>
                <span className="text-xl font-bold" dir="ltr">
                  {step?.label_he ?? id}
                </span>
                {isDone && (
                  <span className="text-lg font-bold text-[var(--dk-good)]">
                    ✓
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* one explanation line at a time — the current step's detail */}
      <div className="flex min-h-[64px] w-[75%] items-center justify-center text-center">
        {active ? (
          <p
            key={active.step}
            className="dk-fade-up text-2xl font-medium leading-snug text-[var(--dk-ink)]"
          >
            {active.detail_he}
          </p>
        ) : steps.length === 0 ? (
          <p className="dk-breathe text-xl text-[var(--dk-ink-3)]">
            הפייפליין הדטרמיניסטי — הבסיס של הכל…
          </p>
        ) : (
          <p className="text-xl text-[var(--dk-ink-2)]">
            בדיוק הסדר הזה רץ ב־GitHub Actions כל 6 שעות. הדמו שלפניכם הוא
            השכבה שמעל.
          </p>
        )}
      </div>
    </section>
  );
}
