"use client";

import type { LlmModeEvent, PhaseEvent, SceneEvent, StreamMode } from "./types";

interface TopBarProps {
  scene: SceneEvent | null;
  phase: PhaseEvent | null;
  mode: StreamMode;
  llmMode: LlmModeEvent | null;
}

/**
 * Always-on header: product mark · big scene title + one explanation line ·
 * scene progress dots · model-provenance badge.
 */
export function TopBar({ scene, phase, mode, llmMode }: TopBarProps) {
  return (
    <header className="flex h-full items-center gap-6 px-8">
      {/* product mark */}
      <div className="flex shrink-0 items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--dk-accent-dim)] text-2xl">
          🐝
        </div>
        <div>
          <div className="text-xl font-bold leading-tight">
            Trust <span className="text-[var(--dk-accent)]">· נחיל סוכנים</span>
          </div>
          <div className="text-[11px] text-[var(--dk-ink-3)]">
            לקסיקון הקיטוב — מחקר אלמוג בן שמחון
          </div>
        </div>
      </div>

      {/* scene title — the single focus point of the screen */}
      <div className="flex min-w-0 flex-1 flex-col items-center justify-center">
        {scene ? (
          <div key={scene.scene} className="dk-chip-in min-w-0 text-center">
            <div className="text-[26px] font-black leading-tight tracking-tight text-[var(--dk-accent)]">
              {scene.title_he}
              {phase && (
                <span className="text-[var(--dk-ink)]"> · {phase.label_he}</span>
              )}
            </div>
            {scene.subtitle_he && (
              <div className="dk-truncate text-[14px] text-[var(--dk-ink-2)]">
                {scene.subtitle_he}
              </div>
            )}
          </div>
        ) : (
          <div className="dk-breathe rounded-full border border-[var(--dk-border)] px-8 py-2.5 text-xl font-medium text-[var(--dk-ink-2)]">
            ממתין לריצה הבאה…
          </div>
        )}
      </div>

      {/* progress + mode */}
      <div className="flex shrink-0 items-center gap-4">
        {mode === "mock" ? (
          <span className="rounded-full border border-[var(--dk-warn)]/40 bg-[var(--dk-warn)]/10 px-3 py-1 text-sm font-medium text-[var(--dk-warn)]">
            מצב הדגמה
          </span>
        ) : llmMode ? (
          <span className="flex items-center gap-1.5 rounded-full border border-[var(--dk-border)] bg-[var(--dk-surface-2)] px-3 py-1 text-sm font-medium text-[var(--dk-ink-2)]">
            <span className="h-2 w-2 rounded-full bg-[var(--dk-ink-3)]" />
            {llmMode.label_he}
          </span>
        ) : null}

        {/* scene progress dots */}
        {scene && (
          <div className="flex items-center gap-1.5" aria-label="התקדמות סצנות">
            {Array.from({ length: scene.total }, (_, i) => (
              <span
                key={i}
                className={`rounded-full transition-all duration-500 ${
                  i + 1 === scene.idx
                    ? "h-3 w-3 bg-[var(--dk-accent)]"
                    : i + 1 < scene.idx
                      ? "h-2 w-2 bg-[var(--dk-accent)]/50"
                      : "h-2 w-2 bg-[var(--dk-border)]"
                }`}
              />
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
