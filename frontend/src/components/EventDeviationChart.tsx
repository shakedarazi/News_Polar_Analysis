import type { EventDeviationProfile } from "@/lib/types";
import { sourceLabel } from "@/lib/format";
import { EmptyState } from "./EmptyState";
import { LOGO_COLOR, LOGO_TEXT } from "./SourceLogo";

const METRIC_LABEL: Record<string, string> = {
  audience_mean: "פולריות התגובות",
  dominance: "ריכוז נושאי בטקסט הכתבה",
  audience_issue_mean: "שפת נושא בתגובות",
  audience_affective_mean: "שפת עוינות בתגובות",
};

/** Confidence, not direction, drives the colour. Which side of zero an outlet
 * falls on is already carried by position; colouring it as well would turn a
 * measurement into a verdict. */
const STRONG = "var(--purple)";
const WEAK = "#94A3B8";

function pct(value: number, domain: number): number {
  return ((value / domain + 1) / 2) * 100;
}

/**
 * A forest plot of each outlet's distance from the median of the same event.
 *
 * The dashboard's other source comparison averages everything an outlet
 * published, which mostly measures *which stories it chose to cover*. Here the
 * story is held fixed: every outlet is scored against the median version of the
 * same event, so what is left is the editorial difference.
 *
 * Two intervals are drawn per row. The pale one is Bonferroni-corrected for the
 * number of outlets tested at once — testing several and reporting whichever
 * crossed zero is how noise becomes a finding — and it is the one the
 * "מובהק" label is gated on.
 */
export function EventDeviationChart({ profile }: { profile: EventDeviationProfile }) {
  const rows = profile.sources.filter((s) => typeof s.mean_deviation === "number");

  if (rows.length === 0 || profile.events_used === 0) {
    return (
      <EmptyState message="עדיין אין מספיק אירועים שסוקרו ביותר ממקור אחד כדי להשוות." />
    );
  }

  // Symmetric around zero: the eye reads distance from the centre line, and an
  // asymmetric domain would make a small negative look like a large one.
  const extent = Math.max(
    ...rows.flatMap((s) =>
      [s.mean_deviation, s.ci_low_adjusted, s.ci_high_adjusted, s.ci_low, s.ci_high]
        .filter((v): v is number => typeof v === "number")
        .map(Math.abs),
    ),
  );
  const domain = (extent || 0.01) * 1.25;
  const pairPercent =
    profile.pair_share !== null ? Math.round(profile.pair_share * 100) : null;

  return (
    <div>
      <div className="space-y-1">
        {rows.map((s) => {
          const hasCi = s.ci_low !== null && s.ci_high !== null;
          const color = s.significant_adjusted ? STRONG : WEAK;
          const logo = LOGO_COLOR[s.source] ?? "#64748B";

          return (
            <div
              key={s.source}
              className="grid grid-cols-[7.5rem_1fr_5.5rem] items-center gap-2 sm:grid-cols-[9rem_1fr_7rem]"
            >
              <div className="flex items-center gap-2">
                <span
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-bold text-white"
                  style={{ background: logo }}
                  aria-hidden
                >
                  {LOGO_TEXT[s.source] ?? s.source.slice(0, 2).toUpperCase()}
                </span>
                <span className="truncate text-xs text-slate-600 dark:text-slate-300">
                  {sourceLabel(s.source)}
                </span>
              </div>

              <div dir="ltr" className="relative h-8">
                <div
                  className="absolute top-0 bottom-0 w-px bg-[var(--border)]"
                  style={{ left: "50%" }}
                  aria-hidden
                />
                {hasCi && s.ci_low_adjusted !== null && s.ci_high_adjusted !== null && (
                  <div
                    className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full opacity-25"
                    style={{
                      background: color,
                      left: `${pct(s.ci_low_adjusted, domain)}%`,
                      width: `${pct(s.ci_high_adjusted, domain) - pct(s.ci_low_adjusted, domain)}%`,
                    }}
                    aria-hidden
                  />
                )}
                {hasCi && (
                  <div
                    className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full opacity-70"
                    style={{
                      background: color,
                      left: `${pct(s.ci_low!, domain)}%`,
                      width: `${pct(s.ci_high!, domain) - pct(s.ci_low!, domain)}%`,
                    }}
                    aria-hidden
                  />
                )}
                <div
                  className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--card)]"
                  style={{ background: color, left: `${pct(s.mean_deviation, domain)}%` }}
                  aria-hidden
                />
                <span className="sr-only">
                  {sourceLabel(s.source)}: סטייה של{" "}
                  {(s.mean_deviation * 100).toFixed(2)} נקודות אחוז מחציון האירוע, על{" "}
                  {s.events} אירועים
                  {s.significant_adjusted ? ", מובהק" : ", לא מובהק"}
                </span>
              </div>

              <div className="text-left" dir="ltr">
                <span
                  className={`block text-xs font-semibold tabular-nums ${
                    s.significant_adjusted
                      ? "text-slate-900 dark:text-slate-100"
                      : "text-slate-400 dark:text-slate-500"
                  }`}
                >
                  {s.mean_deviation >= 0 ? "+" : "−"}
                  {Math.abs(s.mean_deviation * 100).toFixed(2)}
                </span>
                <span className="block text-[10px] text-slate-400 dark:text-slate-500">
                  {hasCi ? `n=${s.events}` : `n=${s.events} · אין רווח`}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div
        dir="ltr"
        className="mt-1 grid grid-cols-[7.5rem_1fr_5.5rem] gap-2 sm:grid-cols-[9rem_1fr_7rem]"
      >
        <span />
        <div className="flex justify-between text-[10px] text-slate-400 dark:text-slate-500">
          <span>−{(domain * 100).toFixed(2)}</span>
          <span>0 = חציון האירוע</span>
          <span>+{(domain * 100).toFixed(2)}</span>
        </div>
        <span />
      </div>

      <p className="mt-3 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        {METRIC_LABEL[profile.metric] ?? profile.metric}, נמדד <strong>בתוך</strong> אירועים
        שסוקרו על ידי יותר ממקור אחד: כל מקור מושווה לחציון של אותו אירוע, כך שמה שנשאר
        אינו בחירת הסיפורים אלא ההבדל בסיקור. הבסיס: {profile.events_used} אירועים מתוך{" "}
        {profile.events_considered} שנבחנו. כל מקור נספר פעם אחת לאירוע — הכתבה עם הכי הרבה
        תגובות — כדי שמקור שפרסם חמישה המשכים לא יהפוך בעצמו לחציון.
      </p>
      <p className="mt-1.5 text-xs leading-relaxed text-slate-400 dark:text-slate-500">
        הקו הבהיר הוא רווח סמך מתוקן לריבוי השוואות (Bonferroni על {profile.tests_run}{" "}
        מקורות), והוא זה שקובע אם נכתב ״מובהק״. הקו הכהה הוא 95% ללא תיקון.
        {pairPercent !== null && (
          <>
            {" "}
            {pairPercent}% מהאירועים הם זוג מקורות בלבד, ובזוג החציון הוא נקודת האמצע — שתי
            הסטיות הן בהכרח אותה השוואה שנרשמה פעמיים.
          </>
        )}{" "}
        מקור עם פחות מ־{profile.min_observations} אירועים מוצג בלי רווח סמך.
      </p>
    </div>
  );
}
