"use client";

import type { GateEvent } from "./types";

interface GateBarProps {
  gate: GateEvent | null;
  /** the run is on a scene — mid-scene presses skip the current pause */
  running: boolean;
  onAdvance: () => void;
}

/**
 * HITL control strip. Space/Enter/arrows (handled in DemoDashboard) or a click
 * send the same POST /control/advance in both of its states:
 *
 * - at a gate, the loud pill — the scene is over and the demo is waiting;
 * - mid-scene, the quiet pill — the step on screen ends when the presenter is
 *   done talking about it, not when its timer runs out.
 *
 * One key, two meanings, and the strip says which one is live right now. The
 * alternative — showing the control only at gates — left the presenter with
 * ~50s of unskippable pauses inside the architecture scene and no sign that
 * the key was doing anything.
 */
export function GateBar({ gate, running, onAdvance }: GateBarProps) {
  if (!gate) {
    if (!running) return null;
    return (
      <div className="pointer-events-none absolute inset-x-0 bottom-5 z-30 flex justify-center">
        <button
          type="button"
          onClick={onAdvance}
          className="pointer-events-auto flex items-center gap-2.5 rounded-full border border-[var(--dk-border)] bg-[var(--dk-surface)]/70 px-5 py-2 text-[15px] font-semibold text-[var(--dk-ink-3)] backdrop-blur transition hover:border-[var(--dk-accent)]/50 hover:text-[var(--dk-ink-2)]"
        >
          לצעד הבא
          <span className="rounded-md border border-[var(--dk-border)] px-2 py-0.5 text-[12px] font-semibold">
            רווח
          </span>
        </button>
      </div>
    );
  }
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
