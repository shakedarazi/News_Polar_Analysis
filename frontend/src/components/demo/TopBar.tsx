"use client";

import type { PhaseEvent, StreamMode } from "./types";

interface TopBarProps {
  phase: PhaseEvent | null;
  mode: StreamMode;
}

export function TopBar({ phase, mode }: TopBarProps) {
  return (
    <header className="flex h-full items-center gap-6 px-8">
      {/* product mark */}
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--dk-accent-dim)] text-2xl">
          🐝
        </div>
        <div>
          <div className="text-2xl font-bold leading-tight">
            Trust{" "}
            <span className="text-[var(--dk-accent)]">· נחיל סוכנים חי</span>
          </div>
          <div className="text-xs text-[var(--dk-ink-3)]">
            לקסיקון הקיטוב מבוסס על מחקרו של אלמוג בן שמחון
          </div>
        </div>
      </div>

      {/* phase chip */}
      <div className="flex flex-1 items-center justify-center">
        {phase ? (
          <div
            key={`${phase.phase}-${phase.round}`}
            className="dk-chip-in flex items-center gap-3 rounded-full border border-[var(--dk-accent)]/40 bg-[var(--dk-accent-dim)] px-8 py-2.5"
          >
            <span className="h-3 w-3 animate-pulse rounded-full bg-[var(--dk-accent)]" />
            <span className="text-2xl font-bold tracking-tight text-[var(--dk-accent)]">
              {phase.label_he}
            </span>
          </div>
        ) : (
          <div className="dk-breathe rounded-full border border-[var(--dk-border)] px-8 py-2.5 text-xl font-medium text-[var(--dk-ink-2)]">
            ממתין לריצה הבאה…
          </div>
        )}
      </div>

      {/* round progress + mode */}
      <div className="flex items-center gap-4">
        {mode === "mock" && (
          <span className="rounded-full border border-[var(--dk-warn)]/40 bg-[var(--dk-warn)]/10 px-3 py-1 text-sm font-medium text-[var(--dk-warn)]">
            מצב הדגמה
          </span>
        )}
        {phase && (
          <div className="text-left">
            <div className="text-xl font-bold leading-tight">
              סבב {phase.round}/{phase.total_rounds}
            </div>
            <div className="text-sm text-[var(--dk-ink-2)]">
              {phase.round_label_he}
            </div>
          </div>
        )}
        <div className="flex gap-1.5" aria-hidden>
          {Array.from({ length: phase?.total_rounds ?? 3 }, (_, i) => (
            <span
              key={i}
              className={`h-2.5 w-8 rounded-full transition-colors duration-500 ${
                phase && i < phase.round
                  ? "bg-[var(--dk-accent)]"
                  : "bg-[var(--dk-border)]"
              }`}
            />
          ))}
        </div>
      </div>
    </header>
  );
}
