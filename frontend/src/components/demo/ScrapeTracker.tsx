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
}

/** Per-URL scraping decision tree — floats over the map during intake. */
export function ScrapeTracker({ tracks }: ScrapeTrackerProps) {
  if (tracks.length === 0) return null;
  return (
    <aside className="dk-card dk-scale-in absolute top-3 left-3 z-10 w-[300px] p-3.5">
      <h3 className="mb-2 flex items-center gap-2 text-base font-bold text-[var(--dk-ink-2)]">
        🛰️ שחזור קישורים
      </h3>
      <div className="flex flex-col gap-2.5">
        {tracks.map((track) => {
          const byStrategy = new Map(
            track.steps.map((s) => [s.strategy, s] as const),
          );
          const done = track.steps.some(
            (s) => s.status === "success" || s.status === "skipped",
          );
          return (
            <div
              key={track.url}
              className={`rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/70 p-2.5 ${
                done ? "opacity-70" : ""
              }`}
            >
              <div className="dk-truncate mb-1.5 text-[14px] font-semibold">
                {truncate(track.article_title || track.url, 34)}
              </div>
              <ol className="flex flex-col">
                {STRATEGY_ORDER.map((strategy, i) => {
                  const step = byStrategy.get(strategy);
                  // hide untouched tail strategies once the URL is resolved
                  if (!step && done) return null;
                  return (
                    <li
                      key={strategy}
                      className="flex items-center gap-2 py-0.5 text-[13px]"
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
                        <span className="dk-truncate mr-auto max-w-[120px] text-[11px] text-[var(--dk-ink-3)]">
                          {step.note_he}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ol>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
