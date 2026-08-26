import { formatNumber, POLAR_MEAN_METRIC, sourceLabel } from "@/lib/format";
import { PolarScore } from "./PolarScore";
import { EmptyState } from "./EmptyState";
import { SourceLogo } from "./SourceLogo";

type Row = {
  source: string;
  article_count: number;
  analyzed_count?: number;
  avg_audience_mean: number | null;
};

export function SourcesGrid({ sources }: { sources: Row[] }) {
  if (sources.length === 0) {
    return <EmptyState message="לא נמצאו מקורות חדשות התואמים לסינון שנבחר." />;
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {sources.map((s) => {
        const analyzed = s.analyzed_count ?? 0;
        const countLine =
          analyzed > 0 && analyzed < s.article_count
            ? `${formatNumber(s.article_count)} כתבות · ${formatNumber(analyzed)} עם ניתוח תגובות`
            : analyzed === 0
              ? `${formatNumber(s.article_count)} כתבות · אין ניתוח תגובות`
              : `${formatNumber(s.article_count)} כתבות`;
        return (
          <div key={s.source} className="card flex items-center justify-between gap-3 p-4">
            <div className="flex min-w-0 items-center gap-2.5">
              <SourceLogo source={s.source} size={32} />
              <div className="min-w-0">
                <p className="truncate font-bold text-slate-900 dark:text-slate-100">{sourceLabel(s.source)}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{countLine}</p>
              </div>
            </div>
            <div className="shrink-0">
              <PolarScore value={s.avg_audience_mean} label={POLAR_MEAN_METRIC} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
