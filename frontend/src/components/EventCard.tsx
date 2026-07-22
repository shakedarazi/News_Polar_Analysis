import Link from "next/link";
import { Newspaper, Radio } from "lucide-react";
import type { EventSummary } from "@/lib/types";
import { formatDate, sourceLabel } from "@/lib/format";
import { SourceLogo } from "./SourceLogo";

const STILL_DEVELOPING_HOURS = 24;

export function EventCard({ event }: { event: EventSummary }) {
  const stillDeveloping =
    Date.now() - new Date(event.last_seen_at).getTime() < STILL_DEVELOPING_HOURS * 60 * 60 * 1000;

  return (
    <Link href={`/events/${event.event_id}`} className="card card-hover block p-5">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {event.primary_category && (
          <span className="rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300">
            {event.primary_category}
          </span>
        )}
        {stillDeveloping && (
          <span className="inline-flex items-center gap-1 rounded-md bg-[var(--negative)]/10 px-2 py-0.5 text-xs font-semibold text-[var(--negative)]">
            <Radio className="h-3 w-3 animate-pulse" aria-hidden />
            האירוע עדיין מתפתח
          </span>
        )}
      </div>

      <h3 className="mb-2 text-base font-bold text-slate-900 dark:text-slate-100">
        {event.title || "ללא כותרת"}
      </h3>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
        <span className="inline-flex items-center gap-1">
          <Newspaper className="h-3.5 w-3.5" aria-hidden />
          {event.article_count} כתבות · {event.source_count} מקורות
        </span>
        <span>
          {formatDate(event.first_seen_at)} — {formatDate(event.last_seen_at)}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {event.sources.map((source) => (
          <span
            key={source}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
          >
            <SourceLogo source={source} size={14} />
            {sourceLabel(source)}
          </span>
        ))}
      </div>
    </Link>
  );
}
