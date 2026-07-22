import Link from "next/link";
import { ExternalLink } from "lucide-react";
import type { EventTimelineItem } from "@/lib/types";
import { formatDate, sourceLabel } from "@/lib/format";
import { SourceLogo } from "./SourceLogo";
import { CompactBiasBadge } from "./PoliticalBiasMeter";

const SENTIMENT_CLASS: Record<string, string> = {
  חיובי: "score-low",
  שלילי: "score-high",
  מעורב: "score-mid",
  ניטרלי: "score-none",
};

function SentimentBadge({ sentiment }: { sentiment: string | null }) {
  if (!sentiment) return null;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${SENTIMENT_CLASS[sentiment] ?? "score-none"}`}
    >
      {sentiment}
    </span>
  );
}

export function EventTimeline({ items }: { items: EventTimelineItem[] }) {
  if (items.length === 0) {
    return (
      <div className="card p-6 text-center text-sm text-slate-500 dark:text-slate-400">
        לא נמצאו כתבות מקושרות לאירוע זה.
      </div>
    );
  }

  return (
    <ol className="relative space-y-6 border-r-2 border-[var(--border)] pr-6">
      {items.map((item) => (
        <li key={item.article_id} className="relative">
          <span
            className="absolute top-1.5 right-[-31px] h-3 w-3 rounded-full border-2 border-[var(--card)] bg-[var(--purple)]"
            aria-hidden
          />
          <div className="card p-4">
            <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <span className="font-semibold text-[var(--purple)]">{item.status_label}</span>
              <span aria-hidden>·</span>
              <span>{formatDate(item.first_seen_at)}</span>
              <span className="inline-flex items-center gap-1">
                <SourceLogo source={item.source} size={14} />
                {sourceLabel(item.source)}
              </span>
              <SentimentBadge sentiment={item.summary_sentiment} />
              {item.bias_label && (
                <CompactBiasBadge
                  label={item.bias_label}
                  score={item.bias_score}
                  confidence={item.bias_confidence}
                />
              )}
            </div>

            <Link
              href={`/articles/${item.article_id}`}
              className="block text-sm font-bold text-slate-900 hover:text-[var(--primary-light)] dark:text-slate-100"
            >
              {item.title || "ללא כותרת"}
            </Link>

            {item.snippet && (
              <p className="mt-1.5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                {item.snippet}…
              </p>
            )}

            <div className="mt-2 flex items-center gap-3 text-xs">
              <Link
                href={`/articles/${item.article_id}`}
                className="font-medium text-[var(--indigo)] hover:underline"
              >
                לפרטי הכתבה
              </Link>
              <a
                href={item.canonical_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-medium text-[var(--indigo)] hover:underline"
              >
                לכתבה המקורית
                <ExternalLink className="h-3 w-3" aria-hidden />
              </a>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
