"use client";

import type { GateEvent } from "./types";

interface GateBarProps {
  gate: GateEvent | null;
  onAdvance: () => void;
}

/**
 * HITL control strip: appears when the backend is paused at a gate.
 * Space/Enter/arrows (handled in DemoDashboard) or a click advance the demo.
 */
export function GateBar({ gate, onAdvance }: GateBarProps) {
  if (!gate) return null;
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-5 z-30 flex justify-center">
      <button
        type="button"
        onClick={onAdvance}
        className="dk-gate-pulse pointer-events-auto flex items-center gap-3 rounded-full border border-[var(--dk-accent)]/60 bg-[var(--dk-surface)]/95 px-7 py-3 text-lg font-bold text-[var(--dk-ink)] shadow-[0_0_30px_rgba(34,211,238,0.25)] backdrop-blur"
      >
        <span className="text-[var(--dk-accent)]" aria-hidden>
          ⏎
        </span>
        {gate.hint_he || "המשך"}
        <span className="rounded-md border border-[var(--dk-border)] px-2 py-0.5 text-[12px] font-semibold text-[var(--dk-ink-2)]">
          רווח
        </span>
        {gate.autoplay_ms !== null && (
          <span className="text-[12px] font-normal text-[var(--dk-ink-3)]">
            ממשיך לבד…
          </span>
        )}
      </button>
    </div>
  );
}
