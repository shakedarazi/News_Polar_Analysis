"use client";

import { useEffect } from "react";
import type { RunSummaryEvent } from "./types";

const SHOW_MS = 10_000;

function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

interface StatTileProps {
  label: string;
  value: string;
  dir?: "rtl" | "ltr";
}

function StatTile({ label, value, dir = "rtl" }: StatTileProps) {
  return (
    <div className="dk-card flex min-w-[150px] flex-col items-center gap-1 px-6 py-4">
      <div className="text-4xl font-bold tracking-tight" dir={dir}>
        {value}
      </div>
      <div className="text-sm text-[var(--dk-ink-2)]">{label}</div>
    </div>
  );
}

interface SummaryOverlayProps {
  summary: RunSummaryEvent;
  onDone: () => void;
}

export function SummaryOverlay({ summary, onDone }: SummaryOverlayProps) {
  useEffect(() => {
    const t = setTimeout(onDone, SHOW_MS);
    return () => clearTimeout(t);
  }, [onDone]);

  const rounds = Array.isArray(summary.rounds) ? summary.rounds : [];
  const trajectory = rounds.map((r) => pct(r.accuracy ?? 0)).join(" ← ");

  return (
    <div className="dk-dim-in absolute inset-0 z-40 flex flex-col items-center justify-center gap-8 bg-[#05080f]/88 px-10">
      <div className="dk-scale-in text-center">
        <div className="mb-3 text-lg font-semibold text-[var(--dk-accent)]">
          סיכום הריצה
        </div>
        <h2 className="max-w-[900px] text-5xl font-black leading-tight">
          {summary.headline_he}
        </h2>
      </div>

      <div className="dk-fade-up flex flex-wrap items-stretch justify-center gap-4">
        <StatTile
          label="כתבות נותחו"
          value={String(summary.total_articles ?? 0)}
        />
        <StatTile label="עימותים" value={String(summary.debates ?? 0)} />
        <StatTile
          label="קישורים שוחזרו"
          value={String(summary.links_recovered ?? 0)}
        />
        <StatTile
          label="עלות כוללת"
          value={`$${(summary.total_cost_usd ?? 0).toFixed(4)}`}
          dir="ltr"
        />
        {rounds.length > 0 && (
          <StatTile label="מסלול הדיוק" value={trajectory} />
        )}
      </div>

      <div className="dk-breathe text-[var(--dk-ink-3)]">
        הריצה הבאה תתחיל מיד…
      </div>
    </div>
  );
}
