"use client";

import { useEffect } from "react";
import type { InsightEvent } from "./types";

const SHOW_MS = 10_000;

interface InsightToastProps {
  insight: { id: number; ev: InsightEvent };
  onDone: (id: number) => void;
}

export function InsightToast({ insight, onDone }: InsightToastProps) {
  const { id, ev } = insight;
  useEffect(() => {
    const t = setTimeout(() => onDone(id), SHOW_MS);
    return () => clearTimeout(t);
  }, [id, onDone]);

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-[26%] z-30 flex justify-center">
      <figure
        key={id}
        className="dk-toast dk-card w-[56%] max-w-[720px] border-[var(--dk-accent)]/30 px-8 py-5 text-center"
      >
        <div className="mb-1.5 text-sm font-semibold text-[var(--dk-accent)]">
          💡 {ev.question_he}
        </div>
        <blockquote className="text-2xl font-bold leading-snug">
          ״{ev.text_he}״
        </blockquote>
        <figcaption className="mt-2 text-xs text-[var(--dk-ink-3)]">
          {ev.source_he}
        </figcaption>
      </figure>
    </div>
  );
}
