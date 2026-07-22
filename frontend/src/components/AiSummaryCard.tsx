"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, Sparkles } from "lucide-react";
import { generateArticleSummaryClient, getArticleSummaryClient } from "@/lib/api";
import type { AiSummary } from "@/lib/types";

type State =
  | { kind: "loading" }
  | { kind: "processing" }
  | { kind: "no-content" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: AiSummary };

export function AiSummaryCard({
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
      const data = await generateArticleSummaryClient(articleId);
      if (data.status === "ready") {
        setState({ kind: "ready", data });
      } else {
        setState({ kind: "error", message: "השירות לא החזיר סיכום." });
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
      setState({ kind: "no-content" });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await getArticleSummaryClient(articleId);
        if (cancelled) return;
        if (data.status === "ready") {
          setState({ kind: "ready", data });
        } else {
          // No summary stored yet — generate once and cache server-side.
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
        <Sparkles className="h-5 w-5 text-[var(--purple)]" aria-hidden />
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">סיכום AI</h2>
      </div>
      <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
        הנקודות המרכזיות מהכתבה כפי שזוהו על ידי המערכת
      </p>

      {state.kind === "loading" && (
        <div className="animate-pulse space-y-2" role="status" aria-label="טוען סיכום">
          <div className="h-3 w-full rounded bg-slate-100 dark:bg-slate-800" />
          <div className="h-3 w-5/6 rounded bg-slate-100 dark:bg-slate-800" />
          <div className="h-3 w-2/3 rounded bg-slate-100 dark:bg-slate-800" />
        </div>
      )}

      {state.kind === "processing" && (
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <RefreshCw className="h-4 w-4 animate-spin" aria-hidden />
          מייצר סיכום AI לכתבה...
        </div>
      )}

      {state.kind === "no-content" && (
        <p className="text-sm text-slate-500 dark:text-slate-400">אין מספיק תוכן בכתבה כדי לייצר סיכום.</p>
      )}

      {state.kind === "error" && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-red-700 dark:text-red-300">
            <AlertTriangle className="h-4 w-4" aria-hidden />
            לא ניתן היה לייצר סיכום AI כרגע.
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

      {state.kind === "ready" && (
        <div className="space-y-4 text-sm text-slate-700 dark:text-slate-300">
          <p className="leading-relaxed">{state.data.summary}</p>

          {!!state.data.key_points?.length && (
            <div>
              <h3 className="mb-1 text-xs font-semibold text-slate-500 dark:text-slate-400">נקודות מרכזיות</h3>
              <ul className="list-inside list-disc space-y-1">
                {state.data.key_points.map((point, i) => (
                  <li key={i}>{point}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
            {state.data.topic && (
              <span>
                <strong className="text-slate-700 dark:text-slate-300">נושא מרכזי:</strong> {state.data.topic}
              </span>
            )}
            {state.data.sentiment && (
              <span>
                <strong className="text-slate-700 dark:text-slate-300">טון הכתבה:</strong> {state.data.sentiment}
              </span>
            )}
          </div>

          {!!state.data.entities?.length && (
            <div className="flex flex-wrap gap-1.5">
              {state.data.entities.map((entity, i) => (
                <span
                  key={i}
                  className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs text-slate-600 dark:text-slate-300"
                >
                  {entity}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
