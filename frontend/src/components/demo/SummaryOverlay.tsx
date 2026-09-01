"use client";

import type { Facts } from "./explain/facts";
import type { RunSummaryEvent } from "./types";

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
  facts: Facts | null;
}

/**
 * Stays on screen until the presenter advances (reset clears it).
 *
 * The retrieval tile reports the snapshot, not the story just shown. The
 * closing screen is the one the audience writes down, and the story the loop
 * picked is a story picked to be striking — on it, keyword search finds 0 of 2
 * versions, against 17 of 77 across the corpus. Every other tile here is
 * already a snapshot number; this one was the outlier.
 */
export function SummaryOverlay({ summary, facts }: SummaryOverlayProps) {
  const significant = (summary.outlets ?? []).filter((o) => o.significant);
  const keyword = facts?.retrieval?.keyword;

  return (
    <div className="dk-dim-in absolute inset-0 z-40 flex flex-col items-center justify-center gap-7 bg-[#05080f]/88 px-10">
      <div className="dk-scale-in text-center">
        <div className="mb-3 text-lg font-semibold text-[var(--dk-accent)]">
          סיכום הריצה
        </div>
        <h2 className="max-w-[900px] text-5xl font-black leading-tight">
          {summary.headline_he}
        </h2>
        <p className="mt-3 max-w-[820px] text-lg text-[var(--dk-ink-2)]">
          {summary.event_headline}
        </p>
      </div>

      <div className="dk-fade-up flex flex-wrap items-stretch justify-center gap-4">
        <StatTile
          label={
            keyword
              ? "גרסאות שחיפוש מילולי מוצא בסנאפשוט"
              : "אחזור סמנטי מול חיפוש מילים — בסיפור הזה"
          }
          value={
            keyword
              ? `${keyword.found}/${keyword.total}`
              : `${summary.keyword_total - summary.keyword_found}:${summary.keyword_found}`
          }
          dir="ltr"
        />
        <StatTile
          label="אירועים משותפים בסנאפשוט"
          value={String(summary.events_total ?? 0)}
        />
        <StatTile
          label="ביטויים שהמאמת פסל"
          value={`${summary.terms_rejected}/${summary.terms_total}`}
          dir="ltr"
        />
        <StatTile
          label="ציטוטים שהמאמת פסל"
          value={`${summary.quotes_rejected}/${summary.quotes_total}`}
          dir="ltr"
        />
        <StatTile
          label="עלות שכבת ה־AI"
          value={`$${(summary.total_cost_usd ?? 0).toFixed(4)}`}
          dir="ltr"
        />
      </div>

      {significant.length > 0 && (
        <div className="dk-fade-up flex flex-wrap justify-center gap-3 text-[15px] text-[var(--dk-ink-2)]">
          <span className="text-[var(--dk-ink-3)]">
            סטייה מובהקת מחציון האירוע:
          </span>
          {significant.map((o) => (
            <span key={o.source_he} className="font-semibold">
              {o.source_he}{" "}
              <span dir="ltr">
                {(o.mean ?? 0) >= 0 ? "+" : ""}
                {(o.mean ?? 0).toFixed(4)}
              </span>{" "}
              <span className="text-[var(--dk-ink-3)]">(n={o.n})</span>
            </span>
          ))}
        </div>
      )}

      <div className="dk-breathe text-[var(--dk-ink-3)]">
        רווח / ⏎ — ריצה חדשה, סיפור אחר
      </div>
    </div>
  );
}
