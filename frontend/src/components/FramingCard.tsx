"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, ScanText, ShieldCheck } from "lucide-react";
import { generateArticleFramingClient, getArticleFramingClient } from "@/lib/api";
import type { ArticleFraming } from "@/lib/types";

const VOICE_LABEL: Record<string, string> = {
  active: "פעיל",
  passive: "סביל",
};

const VOICE_NOTE: Record<string, string> = {
  active: "המשפט מציין מי ביצע את הפעולה.",
  passive: "המשפט מתאר את הפעולה בלי לציין מי ביצע אותה.",
};

function Field({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | null | undefined;
  hint?: string;
}) {
  return (
    <div>
      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
      {value ? (
        <p className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-slate-100">{value}</p>
      ) : (
        // An absent value is a finding, not a hole: "no actor named" is exactly
        // what passive framing looks like. Saying "—" alone would read as a bug.
        <p className="mt-0.5 text-sm text-slate-400 dark:text-slate-500">לא צוין בכתבה</p>
      )}
      {hint && <p className="mt-0.5 text-[11px] leading-relaxed text-slate-400 dark:text-slate-500">{hint}</p>}
    </div>
  );
}

type State =
  | { kind: "loading" }
  | { kind: "processing" }
  | { kind: "insufficient" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: ArticleFraming };

/**
 * Structural framing: who is named as acting, who is held responsible, active
 * or passive voice, whose point of view opens the piece. Distinct from the
 * bias meter (which camp the language leans to) and from the lexicon score
 * (how charged the audience is) — two outlets can match on both of those and
 * still differ here.
 *
 * Everything rendered has already passed string grounding against the same 500
 * characters the model read. The rejected items are shown too, because a
 * verifier whose work is invisible is indistinguishable from no verifier.
 */
export function FramingCard({
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
      const data = await generateArticleFramingClient(articleId);
      if (data.status === "ready") {
        setState({ kind: "ready", data });
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
        const data = await getArticleFramingClient(articleId);
        if (cancelled) return;
        if (data.status === "ready") {
          setState({ kind: "ready", data });
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

  const data = state.kind === "ready" ? state.data : null;
  const kept = data?.loaded_terms ?? [];
  const dropped = data?.dropped_terms ?? [];
  const rejectedActor = data?.rejected_actor ?? null;

  return (
    <section className="card p-6">
      <div className="mb-1 flex items-center gap-2">
        <ScanText className="h-5 w-5 text-[var(--purple)]" aria-hidden />
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">מסגור הכתבה</h2>
      </div>
      <p className="mb-4 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        מי מוצג כמבצע הפעולה, למי מיוחסת אחריות ובאיזה קול נכתבה הכותרת. זהו ניתוח מבני של
        הניסוח — לא הערכה של נכונות הכתבה ולא של עמדתה הפוליטית.
      </p>

      {state.kind === "loading" && (
        <div className="animate-pulse space-y-2" role="status" aria-label="טוען ניתוח מסגור">
          <div className="h-3 w-1/3 rounded bg-slate-100 dark:bg-slate-800" />
          <div className="h-3 w-2/3 rounded bg-slate-100 dark:bg-slate-800" />
        </div>
      )}

      {state.kind === "processing" && (
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <RefreshCw className="h-4 w-4 animate-spin" aria-hidden />
          מנתח מסגור...
        </div>
      )}

      {state.kind === "insufficient" && (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          אין מספיק טקסט בכתבה לניתוח מסגור.
        </p>
      )}

      {state.kind === "error" && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-red-700 dark:text-red-300">
            <AlertTriangle className="h-4 w-4" aria-hidden />
            לא ניתן היה לנתח מסגור כרגע.
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

      {data && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="מי מוצג כמבצע" value={data.actor} />
            <Field label="למי מיוחסת אחריות" value={data.responsibility} />
            <Field
              label="קול הכותרת"
              value={data.voice ? VOICE_LABEL[data.voice] : null}
              hint={data.voice ? VOICE_NOTE[data.voice] : undefined}
            />
            <Field label="נקודת המבט הפותחת" value={data.lead_perspective} />
          </div>

          <div>
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
              מילים טעונות בכותרת
            </p>
            {kept.length > 0 ? (
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {kept.map((term) => (
                  <span
                    key={term}
                    className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                  >
                    {term}
                  </span>
                ))}
              </div>
            ) : (
              <p className="mt-0.5 text-sm text-slate-400 dark:text-slate-500">
                הכותרת ניטרלית — לא נמצאו מילות הערכה.
              </p>
            )}
          </div>

          <div className="border-t border-[var(--border)] pt-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
              אימות מול הטקסט
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
              כל ביטוי שמוצג כאן נבדק והוא מופיע כלשונו ב־500 התווים הראשונים שהמודל קרא. ביטוי
              שלא נמצא — יורד, ולא מוצג.
            </p>
            {dropped.length === 0 && !rejectedActor ? (
              <p className="mt-1.5 text-[11px] text-slate-400 dark:text-slate-500">
                בכתבה זו לא נפסל אף ביטוי.
              </p>
            ) : (
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] text-slate-400 dark:text-slate-500">נפסלו:</span>
                {rejectedActor && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500 line-through dark:bg-slate-800 dark:text-slate-400">
                    {rejectedActor}
                  </span>
                )}
                {dropped.map((term) => (
                  <span
                    key={term}
                    className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500 line-through dark:bg-slate-800 dark:text-slate-400"
                  >
                    {term}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
