"use client";

import { useEffect } from "react";
import { METHOD_LABELS_HE } from "./roster";
import type { ClassificationEvent } from "./types";

const SHOW_MS = 6_500;

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

interface ClassificationFlashProps {
  item: { id: number; ev: ClassificationEvent };
  onDone: (id: number) => void;
}

/** compact flash card near the map for each classification event */
export function ClassificationFlash({ item, onDone }: ClassificationFlashProps) {
  const { id, ev } = item;
  useEffect(() => {
    const t = setTimeout(() => onDone(id), SHOW_MS);
    return () => clearTimeout(t);
  }, [id, onDone]);

  const wrong = ev.correct === false;
  const confidence = Math.max(0, Math.min(1, ev.confidence ?? 0));
  const neighbors = Array.isArray(ev.neighbors)
    ? ev.neighbors.slice(0, 3)
    : [];

  return (
    <div
      key={id}
      className={`dk-card dk-scale-in absolute bottom-3 left-3 z-10 w-[310px] p-3.5 ${
        wrong ? "dk-shake border-[var(--dk-bad)]/40" : ""
      }`}
    >
      <div className="dk-truncate mb-2 text-[15px] font-bold">
        {truncate(ev.title ?? "", 38)}
      </div>

      <div className="mb-2 flex items-center gap-2">
        <span className="rounded-full bg-[var(--dk-accent-dim)] px-3 py-0.5 text-[15px] font-bold text-[var(--dk-accent)]">
          {ev.predicted}
        </span>
        {ev.correct !== null && (
          <span
            className={`text-xl font-black ${
              ev.correct ? "text-[var(--dk-good)]" : "text-[var(--dk-bad)]"
            }`}
            title={ev.reference ?? undefined}
          >
            {ev.correct ? "✓" : `✗ (${ev.reference ?? "?"})`}
          </span>
        )}
        <span className="mr-auto rounded-md border border-[var(--dk-border)] px-2 py-0.5 text-[12px] font-semibold text-[var(--dk-ink-2)]">
          {METHOD_LABELS_HE[ev.method] ?? ev.method}
        </span>
      </div>

      {/* confidence meter — accent fill on a lighter same-hue track */}
      <div className="mb-1 flex items-center gap-2">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--dk-accent-dim)]">
          <div
            className="dk-bar-fill h-full rounded-full bg-[var(--dk-accent)]"
            style={{ width: `${confidence * 100}%` }}
          />
        </div>
        <span className="text-[13px] font-bold text-[var(--dk-ink-2)]">
          {Math.round(confidence * 100)}%
        </span>
      </div>

      {neighbors.length > 0 && (
        <div className="mt-2 border-t border-[var(--dk-border)] pt-1.5">
          <div className="mb-1 text-[11px] font-semibold text-[var(--dk-ink-3)]">
            שכנים שאוחזרו (RAG)
          </div>
          {neighbors.map((n, i) => (
            <div
              key={i}
              className="flex items-center gap-2 py-0.5 text-[12px] text-[var(--dk-ink-2)]"
            >
              <span className="dk-truncate flex-1">
                {truncate(n.title ?? "", 30)}
              </span>
              <span className="shrink-0 font-semibold">{n.category}</span>
              <span className="shrink-0 text-[var(--dk-ink-3)]" dir="ltr">
                {(n.score ?? 0).toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
