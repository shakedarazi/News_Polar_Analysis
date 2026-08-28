"use client";

import { STRATEGY_LABELS_HE, STRATEGY_ORDER } from "./roster";
import type { ScrapeStatus, ScrapeUrlTrack } from "./types";

function StatusIcon({ status }: { status: ScrapeStatus | null }) {
  switch (status) {
    case "trying":
      return <span className="dk-spinner inline-block" aria-label="מנסה" />;
    case "success":
      return (
        <span className="font-bold text-[var(--dk-good)]" aria-label="הצליח">
          ✓
        </span>
      );
    case "failed":
      return (
        <span className="font-bold text-[var(--dk-bad)]" aria-label="נכשל">
          ✗
        </span>
      );
    case "skipped":
      return (
        <span className="text-[var(--dk-ink-3)]" aria-label="דולג">
          ⏭
        </span>
      );
    default:
      return (
        <span className="text-[var(--dk-ink-3)] opacity-40" aria-hidden>
          ·
        </span>
      );
  }
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

interface ScrapeTrackerProps {
  tracks: ScrapeUrlTrack[];
  /** stage=true — the intake scene's main visual (large, static) instead of
      a small overlay floating over the agent map */
  stage?: boolean;
}

/** Per-URL scraping decision tree. */
export function ScrapeTracker({ tracks, stage = false }: ScrapeTrackerProps) {
  if (tracks.length === 0) {
    return stage ? (
      <p className="dk-breathe text-xl text-[var(--dk-ink-3)]">
        סקאוט יוצא לאסוף את הכתבות…
      </p>
    ) : null;
  }
  if (stage) {
    return (
      <div className="dk-scale-in flex w-full max-w-[760px] flex-col gap-3">
        <h3 className="flex items-center gap-2 text-xl font-bold text-[var(--dk-ink-2)]">
          🛰️ עץ ההחלטות של סקאוט — קישור אחר קישור
        </h3>
        <div className="flex flex-col gap-3 text-lg">
          {tracks.slice(-3).map((track) => (
            <TrackCard key={track.url} track={track} large />
          ))}
        </div>
      </div>
    );
  }
  return (
    <aside className="dk-card dk-scale-in absolute top-3 left-3 z-10 w-[300px] p-3.5">
      <h3 className="mb-2 flex items-center gap-2 text-base font-bold text-[var(--dk-ink-2)]">
        🛰️ שחזור קישורים
      </h3>
      <div className="flex flex-col gap-2.5">
        {tracks.map((track) => (
          <TrackCard key={track.url} track={track} />
        ))}
      </div>
    </aside>
  );
}

function TrackCard({
  track,
  large = false,
}: {
  track: ScrapeUrlTrack;
  large?: boolean;
}) {
  const byStrategy = new Map(track.steps.map((s) => [s.strategy, s] as const));
  const done = track.steps.some(
    (s) => s.status === "success" || s.status === "skipped",
  );
  return (
    <div
      className={`rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/70 ${
        large ? "p-4" : "p-2.5"
      } ${done ? "opacity-70" : ""}`}
    >
      <div
        className={`dk-truncate font-semibold ${
          large ? "mb-2 text-[18px]" : "mb-1.5 text-[14px]"
        }`}
      >
        {truncate(track.article_title || track.url, large ? 60 : 34)}
      </div>
      <ol className="flex flex-col">
        {STRATEGY_ORDER.map((strategy, i) => {
          const step = byStrategy.get(strategy);
          // hide untouched tail strategies once the URL is resolved
          if (!step && done) return null;
          return (
            <li
              key={strategy}
              className={`flex items-center gap-2 py-0.5 ${
                large ? "text-[16px]" : "text-[13px]"
              }`}
            >
              <span className="flex w-4 justify-center">
                <StatusIcon status={step?.status ?? null} />
              </span>
              {i < STRATEGY_ORDER.length - 1 && (
                <span className="sr-only">←</span>
              )}
              <span
                className={
                  step
                    ? "text-[var(--dk-ink)]"
                    : "text-[var(--dk-ink-3)] opacity-60"
                }
              >
                {STRATEGY_LABELS_HE[strategy]}
              </span>
              {step?.note_he && (
                <span
                  className={`dk-truncate mr-auto text-[var(--dk-ink-3)] ${
                    large ? "max-w-[280px] text-[14px]" : "max-w-[120px] text-[11px]"
                  }`}
                >
                  {step.note_he}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
