import type { EventDeviation } from "@/lib/types";
import { sourceLabel } from "@/lib/format";
import { LOGO_COLOR, LOGO_TEXT } from "./SourceLogo";

/**
 * One event's arithmetic, shown in full.
 *
 * The dashboard aggregates thousands of these into per-outlet intervals; this
 * is the unit those are built from, so a reader who distrusts the aggregate can
 * open a single story and check the subtraction by hand. Same rule as the
 * aggregate: one version per outlet, the most-commented one, so a channel that
 * ran five follow-ups does not become the median it is measured against.
 */
export function EventVersionComparison({ data }: { data: EventDeviation }) {
  if (!data.comparable || data.median === null || data.versions.length < 2) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">
        באירוע הזה יש נתוני קהל למקור אחד בלבד, ולכן אין מול מה להשוות.
      </p>
    );
  }

  const extent = Math.max(...data.versions.map((v) => Math.abs(v.deviation))) || 0.01;
  const domain = extent * 1.3;

  return (
    <div>
      <div className="space-y-1">
        {data.versions.map((v) => {
          const left = ((v.deviation / domain + 1) / 2) * 100;
          const center = 50;
          const color = LOGO_COLOR[v.source] ?? "#64748B";
          return (
            <div
              key={v.article_id}
              className="grid grid-cols-[7rem_1fr_4.5rem] items-center gap-2 sm:grid-cols-[9rem_1fr_6rem]"
            >
              <div className="flex items-center gap-2">
                <span
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-bold text-white"
                  style={{ background: color }}
                  aria-hidden
                >
                  {LOGO_TEXT[v.source] ?? v.source.slice(0, 2).toUpperCase()}
                </span>
                <span className="truncate text-xs text-slate-600 dark:text-slate-300">
                  {sourceLabel(v.source)}
                </span>
              </div>

              <div dir="ltr" className="relative h-7">
                <div
                  className="absolute top-0 bottom-0 w-px bg-[var(--border)]"
                  style={{ left: "50%" }}
                  aria-hidden
                />
                <div
                  className="absolute top-1/2 h-2 -translate-y-1/2 rounded-full"
                  style={{
                    background: color,
                    left: `${Math.min(left, center)}%`,
                    width: `${Math.abs(left - center)}%`,
                  }}
                  aria-hidden
                />
                <span className="sr-only">
                  {sourceLabel(v.source)}: {(v.value * 100).toFixed(2)} אחוז,{" "}
                  {(v.deviation * 100).toFixed(2)} נקודות אחוז מהחציון
                </span>
              </div>

              <div className="text-left tabular-nums" dir="ltr">
                <span className="block text-xs font-semibold text-slate-900 dark:text-slate-100">
                  {v.deviation >= 0 ? "+" : "−"}
                  {Math.abs(v.deviation * 100).toFixed(2)}
                </span>
                <span className="block text-[10px] text-slate-400 dark:text-slate-500">
                  {(v.value * 100).toFixed(2)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-3 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        חציון האירוע: {(data.median * 100).toFixed(2)}% — הקו האנכי. הסטייה היא המרחק ממנו,
        בנקודות אחוז. מקור שאין לו תגובות שנותחו בכתבה הזו אינו משתתף בחציון ואינו מוצג;
        הוא לא נספר כאפס.
        {data.versions.length === 2 && (
          <>
            {" "}
            בשני מקורות החציון הוא נקודת האמצע, ולכן שתי הסטיות הן בהכרח אותו מרחק לשני
            הכיוונים — זו השוואה אחת, לא שתי תצפיות.
          </>
        )}
      </p>
    </div>
  );
}
