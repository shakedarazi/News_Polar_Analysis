"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Compass, RefreshCw } from "lucide-react";
import { generateArticleBiasClient, getArticleBiasClient } from "@/lib/api";
import type { ArticleBias, BiasLabel } from "@/lib/types";

const DISCLAIMER =
  "המדד הוא הערכה אלגוריתמית המבוססת על ניתוח השפה והמסגור בכתבה, ואינו קביעה עובדתית לגבי עמדת הכותב או מקור החדשות.";

const NOT_ENOUGH_DATA = "אין מספיק נתונים להצגת נטייה פוליטית.";

function scoreToPercent(score: number): number {
  return ((Math.max(-1, Math.min(1, score)) + 1) / 2) * 100;
}

/** Neutral hue (brand purple) at every position — position alone conveys
 * lean, so no side is colored in a way that could read as partisan coding. */
function BiasScale({
  score,
  label,
  confidence,
}: {
  score: number;
  label: BiasLabel;
  confidence: number | null | undefined;
}) {
  const pct = scoreToPercent(score);
  const confidencePct = confidence !== null && confidence !== undefined ? Math.round(confidence * 100) : null;

  return (
    <div
      role="img"
      aria-label={`נטייה פוליטית: ${label}${confidencePct !== null ? `, רמת ביטחון ${confidencePct} אחוז` : ""}`}
    >
      <div dir="ltr" className="relative h-2 w-full rounded-full bg-[var(--border)]">
        <div
          className="absolute top-1/2 h-3.5 w-3.5 -translate-y-1/2 -translate-x-1/2 rounded-full border-2 border-[var(--card)] bg-[var(--purple)] shadow"
          style={{ left: `${pct}%` }}
          aria-hidden
        />
      </div>
      <div dir="ltr" className="mt-1.5 flex justify-between text-xs font-medium text-slate-500 dark:text-slate-400">
        <span>שמאל</span>
        <span>מרכז</span>
        <span>ימין</span>
      </div>
    </div>
  );
}

/**
 * Read-only compact chip for article/source cards and lists. Renders nothing
 * when no bias estimate has been generated yet for that article — lists must
 * never trigger on-demand AI generation per-row (only the full meter does,
 * on the article detail page), and a meter must not be shown without real data.
 */
export function CompactBiasBadge({
  label,
  score,
  confidence,
}: {
  label: BiasLabel | null | undefined;
  score: number | null | undefined;
  confidence: number | null | undefined;
}) {
  if (!label || score === null || score === undefined) return null;

  const confidencePct = confidence !== null && confidence !== undefined ? Math.round(confidence * 100) : null;
  const pct = scoreToPercent(score);
  const title =
    `נטייה פוליטית: ${label}` +
    (confidencePct !== null ? ` (רמת ביטחון ${confidencePct}%)` : "") +
    ` — ${DISCLAIMER}`;

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300"
      title={title}
      aria-label={title}
    >
      <span dir="ltr" className="relative h-1.5 w-6 rounded-full bg-[var(--border)]" aria-hidden>
        <span
          className="absolute top-1/2 h-2 w-2 -translate-y-1/2 -translate-x-1/2 rounded-full bg-[var(--purple)]"
          style={{ left: `${pct}%` }}
        />
      </span>
      {label}
    </span>
  );
}

type State =
  | { kind: "loading" }
  | { kind: "processing" }
  | { kind: "insufficient"; message?: string }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: ArticleBias };

export function PoliticalBiasMeter({
  articleId,
  hasContent,
}: {
  articleId: string;
  hasContent: boolean;
}) {
  const [state, setState] = useState<State>({ kind: "loading" });

  const generate = useCallback(async () => {
    setState({ kind: "processing" });
    try {
      const data = await generateArticleBiasClient(articleId);
      if (data.status === "ready") {
        setState({ kind: "ready", data });
      } else if (data.status === "not_applicable") {
        setState({ kind: "insufficient", message: data.rationale ?? undefined });
      } else {
        setState({ kind: "error", message: "השירות לא החזיר תוצאה." });
      }
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "שגיאה לא ידועה",
      });
    }
  }, [articleId]);

  useEffect(() => {
    if (!hasContent) {
      setState({ kind: "insufficient" });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await getArticleBiasClient(articleId);
        if (cancelled) return;
        if (data.status === "ready") {
          setState({ kind: "ready", data });
        } else if (data.status === "not_applicable") {
          setState({ kind: "insufficient", message: data.rationale ?? undefined });
        } else {
          await generate();
        }
      } catch (err) {
        if (!cancelled) {
          setState({
            kind: "error",
            message: err instanceof Error ? err.message : "שגיאה לא ידועה",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [articleId, hasContent]);

  return (
    <section className="card p-6">
      <div className="mb-1 flex items-center gap-2">
        <Compass className="h-5 w-5 text-[var(--purple)]" aria-hidden />
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">נטייה פוליטית</h2>
      </div>

      {state.kind === "loading" && (
        <div className="animate-pulse space-y-2" role="status" aria-label="טוען נטייה פוליטית">
          <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800" />
          <div className="h-3 w-1/2 rounded bg-slate-100 dark:bg-slate-800" />
        </div>
      )}

      {state.kind === "processing" && (
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <RefreshCw className="h-4 w-4 animate-spin" aria-hidden />
          מנתח נטייה פוליטית...
        </div>
      )}

      {state.kind === "insufficient" && (
        <p className="text-sm text-slate-500 dark:text-slate-400">{NOT_ENOUGH_DATA}</p>
      )}

      {state.kind === "error" && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-red-700 dark:text-red-300">
            <AlertTriangle className="h-4 w-4" aria-hidden />
            לא ניתן היה לנתח נטייה פוליטית כרגע.
          </div>
          <p className="text-xs text-red-600 dark:text-red-400">{state.message}</p>
          <button
            type="button"
            onClick={generate}
            className="btn-primary rounded-lg px-3 py-1.5 text-xs font-medium"
          >
            נסה שוב
          </button>
        </div>
      )}

      {state.kind === "ready" && state.data.label && (
        <div className="space-y-4">
          <BiasScale
            score={state.data.score ?? 0}
            label={state.data.label}
            confidence={state.data.confidence}
          />

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            <span className="font-semibold text-slate-900 dark:text-slate-100">{state.data.label}</span>
            {state.data.confidence !== null && state.data.confidence !== undefined && (
              <span className="text-xs text-slate-500 dark:text-slate-400">
                רמת ביטחון: {Math.round(state.data.confidence * 100)}%
              </span>
            )}
            {state.data.score !== null && state.data.score !== undefined && (
              <span className="text-xs text-slate-400 dark:text-slate-500">
                ציון: {state.data.score.toFixed(2)}
              </span>
            )}
          </div>

          {state.data.rationale && (
            <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              {state.data.rationale}
            </p>
          )}

          <p className="border-t border-[var(--border)] pt-3 text-[11px] leading-relaxed text-slate-400 dark:text-slate-500">
            {DISCLAIMER}
          </p>
        </div>
      )}
    </section>
  );
}
