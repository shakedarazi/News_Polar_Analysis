import { CheckCircle2, Clock } from "lucide-react";

const DAY_MS = 24 * 60 * 60 * 1000;

// Comments need ~24h to accumulate before audience analysis runs (see
// pipeline/fetch_comments.py); article-text analysis has no such
// dependency and completes immediately on crawl (see
// maybe_analyze_windows_after_save). Two independent statuses, not one.
function audienceEtaLabel(firstSeenAt: string): string {
  const etaMs = new Date(firstSeenAt).getTime() + DAY_MS;
  const hoursLeft = Math.ceil((etaMs - Date.now()) / (60 * 60 * 1000));
  return hoursLeft > 0 ? `ייאספו בעוד כ-${hoursLeft} שעות` : "ממתין לאיסוף תגובות";
}

function StatusCard({
  done,
  label,
  doneHint,
  pendingHint,
}: {
  done: boolean;
  label: string;
  doneHint: string;
  pendingHint: string;
}) {
  return (
    <div className="card flex items-start gap-3 p-4">
      {done ? (
        <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-[var(--positive)]" aria-hidden />
      ) : (
        <Clock className="mt-0.5 h-5 w-5 shrink-0 text-slate-400 dark:text-slate-500" aria-hidden />
      )}
      <div className="min-w-0">
        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{label}</p>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{done ? doneHint : pendingHint}</p>
      </div>
    </div>
  );
}

export function AnalysisStatusBar({
  hasWindows,
  hasAudienceAnalysis,
  firstSeenAt,
}: {
  hasWindows: boolean;
  hasAudienceAnalysis: boolean;
  firstSeenAt: string;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <StatusCard
        done={hasWindows}
        label="ניתוח תוכן הכתבה"
        doneHint="בוצע ניתוח דומיננטיות לפי משפטים"
        pendingHint="יבוצע אוטומטית עם איסוף הכתבה"
      />
      <StatusCard
        done={hasAudienceAnalysis}
        label="ניתוח תגובות קהל"
        doneHint="בוצע ניתוח קיטוב על תגובות הקהל"
        pendingHint={`תגובות ${audienceEtaLabel(firstSeenAt)}`}
      />
    </div>
  );
}
