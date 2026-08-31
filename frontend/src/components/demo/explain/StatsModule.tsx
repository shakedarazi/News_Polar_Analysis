"use client";

import { useState } from "react";
import type { ChangeScan, Facts, OutletRow, TopicCellRow } from "./facts";
import {
  Caveat,
  Chip,
  CodeRef,
  Panel,
  Stage,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "why", label_he: "סטייה מהחציון" },
  { id: "ci", label_he: "רווח סמך" },
  { id: "change", label_he: "נקודת שינוי" },
  { id: "claim", label_he: "מה שורד" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the statistics layer — the only place in the demo whose job is to
 * take findings away.
 *
 * Four decisions, one per tab: compare every version against its own event's median
 * instead of averaging an outlet's whole output; get the interval from a
 * bootstrap rather than a closed formula, and return nothing at all below three
 * observations; report "no change point" only next to the power to have found
 * one; and refuse a beat cell under the event floor even when its interval
 * clears zero. Nineteen significance tests ran across this wall, three came in
 * under 0.05, and exactly one clears the Bonferroni threshold.
 */
export function StatsModule({ facts }: Props) {
  const [tab, setTab] = useState("why");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "why" && <WhyNotRaw facts={facts} />}
      {tab === "ci" && <Interval facts={facts} />}
      {tab === "change" && <Change facts={facts} />}
      {tab === "claim" && <Claim facts={facts} />}
    </div>
  );
}

/* ── formatting ─────────────────────────────────────────────────── */

function num(x: number): string {
  return x.toLocaleString("en-US");
}

function signed(x: number, digits = 4): string {
  return `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(digits)}`;
}

function pct(x: number): string {
  return `${(x * 100).toFixed(0)}%`;
}

/**
 * p-values are the module's currency — render them one way everywhere.
 *
 * A bootstrap p can come back as an exact 0, which only ever means "smaller
 * than this many resamples can resolve". `res` is that resolution, passed in
 * from the iteration count rather than typed as a constant.
 */
function P({
  value,
  alpha,
  res,
}: {
  value: number | null;
  alpha: number;
  res: number;
}) {
  if (value === null) {
    return <span className="font-mono text-[var(--dk-ink-3)]">—</span>;
  }
  const tone =
    value < alpha ? "text-[var(--dk-bad)]" : "text-[var(--dk-ink-2)]";
  return (
    <span className={`font-mono ${tone}`} dir="ltr">
      {value === 0 ? `<${res.toFixed(4)}` : value.toFixed(4)}
    </span>
  );
}

function Big({
  value,
  label,
  tone = "accent",
}: {
  value: string;
  label: string;
  tone?: "accent" | "bad" | "good" | "warn";
}) {
  const colors = {
    accent: "text-[var(--dk-accent)]",
    bad: "text-[var(--dk-bad)]",
    good: "text-[var(--dk-good)]",
    warn: "text-[var(--dk-warn)]",
  };
  return (
    <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-2.5 text-center">
      <div className={`text-3xl font-black ${colors[tone]}`} dir="ltr">
        {value}
      </div>
      <div className="mt-0.5 text-[13.5px] leading-snug text-[var(--dk-ink-2)]">
        {label}
      </div>
    </div>
  );
}

/** A 95% interval drawn on a shared axis, with zero marked. */
function IntervalBar({
  lo,
  hi,
  mean,
  span,
  muted = false,
}: {
  lo: number;
  hi: number;
  mean: number;
  span: number;
  muted?: boolean;
}) {
  const toPct = (v: number) => ((v + span) / (2 * span)) * 100;
  const clear = lo > 0 || hi < 0;
  const color = muted
    ? "bg-[var(--dk-ink-3)]"
    : clear
      ? "bg-[var(--dk-bad)]"
      : "bg-[var(--dk-accent)]";
  return (
    <div className="relative h-4 flex-1 overflow-hidden rounded-md bg-[var(--dk-surface-2)]">
      <div
        className="absolute inset-y-0 w-px bg-[var(--dk-ink-3)]"
        style={{ left: `${toPct(0)}%` }}
      />
      <div
        className={`absolute inset-y-[5px] rounded-full ${color} ${muted ? "opacity-50" : ""}`}
        style={{
          left: `${toPct(Math.max(lo, -span))}%`,
          width: `${Math.max(toPct(Math.min(hi, span)) - toPct(Math.max(lo, -span)), 1)}%`,
        }}
      />
      <div
        className="absolute inset-y-[2px] w-[2px] bg-[var(--dk-ink)]"
        style={{ left: `${toPct(mean)}%` }}
      />
    </div>
  );
}

function Missing() {
  return (
    <p className="text-[15px] text-[var(--dk-ink-3)]">
      אין קובץ מדידות — הדיאגרמות מוצגות בלי המספרים.
    </p>
  );
}

/* ── 1. deviation from the event median, not a per-outlet mean ──── */

function WhyNotRaw({ facts }: Props) {
  const s = facts?.stats;
  const dom = s?.metrics.find((m) => m.key === "dominance");
  const between = dom?.variance.between_share ?? null;
  const within = dom?.variance.within_share ?? null;
  const ranked = dom ? rankRows(dom.outlets) : [];
  const lowRaw = ranked.find((r) => r.rawRank === 1);
  const lowDev = ranked.find((r) => r.devRank === 1);

  return (
    <Stage cols="grid-cols-[42%_1fr]">
      <Panel
        title={
          between !== null
            ? `‏${pct(between)} מהשונות היא איזה סיפור, לא איך`
            : "פירוק השונות"
        }
        hint={dom && s ? `${dom.n} גרסאות · ${s.events} אירועים` : undefined}
      >
        {dom && between !== null && within !== null ? (
          <div className="flex flex-col gap-3">
            <div className="flex h-10 overflow-hidden rounded-lg border border-[var(--dk-border)]">
              <div
                className="flex flex-col items-center justify-center bg-[var(--dk-bad)]/70 text-[13px] font-bold leading-tight"
                style={{ width: `${between * 100}%` }}
              >
                <span>{pct(between)}</span>
                <span className="font-semibold">איזה סיפור</span>
              </div>
              <div
                className="flex flex-col items-center justify-center bg-[var(--dk-good)]/70 text-[13px] font-bold leading-tight"
                style={{ width: `${within * 100}%` }}
              >
                <span>{pct(within)}</span>
                <span className="font-semibold">איך סיפרו</span>
              </div>
            </div>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              ממוצע דומיננטיות לערוץ מערבב שתי שאלות: אילו סיפורים הוא בחר לסקר,
              ואיך כתב אותם. הרוב הוא הראשונה, ואי אפשר להפריד אותן בדיעבד.
            </p>
            <div
              dir="ltr"
              className="rounded-lg border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)]/40 px-3 py-2 text-center font-mono text-[15px] text-[var(--dk-accent)]"
            >
              deviation = value − median(versions of the same event)
            </div>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              הסטייה התוך־אירועית מודדת רק את השנייה: כל גרסה מול חציון האירוע
              שלה. חציון ולא ממוצע, כדי שגרסה חריגה לא תזיז את נקודת הייחוס.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="הנמוך בממוצע הגולמי אינו הנמוך בהשוואה"
        hint="אותן כתבות בדיוק, שתי שיטות"
      >
        {dom && lowRaw && lowDev ? (
          <div className="flex flex-col gap-3">
            <table className="w-full text-[15px]">
              <thead>
                <tr className="text-[13.5px] text-[var(--dk-ink-3)]">
                  <th className="pb-1 text-right font-medium">ערוץ</th>
                  <th className="pb-1 text-right font-medium">n</th>
                  <th className="pb-1 text-right font-medium">ממוצע גולמי</th>
                  <th className="pb-1 text-right font-medium">דירוג</th>
                  <th className="pb-1 text-right font-medium">סטייה תוך־אירוע</th>
                  <th className="pb-1 text-right font-medium">דירוג</th>
                </tr>
              </thead>
              <tbody>
                {ranked.map((r) => (
                  <tr
                    key={r.source}
                    className="border-t border-[var(--dk-border)]/60"
                  >
                    <td className="py-1 font-semibold">{r.source_he}</td>
                    <td className="py-1 font-mono text-[14px]" dir="ltr">
                      {r.n}
                    </td>
                    <td className="py-1 font-mono text-[14px]" dir="ltr">
                      {r.raw_mean?.toFixed(4) ?? "—"}
                    </td>
                    <td className="py-1 font-mono text-[14px] text-[var(--dk-ink-3)]">
                      {r.rawRank ?? "—"}
                    </td>
                    <td className="py-1 font-mono text-[14px]" dir="ltr">
                      {r.mean === null ? "—" : signed(r.mean, 4)}
                    </td>
                    <td
                      className={`py-1 font-mono text-[14px] ${r.flipped ? "font-bold text-[var(--dk-bad)]" : "text-[var(--dk-ink-3)]"}`}
                    >
                      {r.devRank ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              הממוצע הגולמי הנמוך ביותר שייך ל־{lowRaw.source_he}, והסטייה
              הנמוכה ביותר ל־{lowDev.source_he}. שתי העמודות רצות על אותן
              הכתבות ולא מסכימות על הדירוג.
            </p>
            <Caveat>
              גם הסטייה אינה חפה: היא נמדדת מול חציון האירוע, כלומר מול הערוצים
              האחרים שסיקרו אותו. אין כאן אמת אובייקטיבית — יש נקודת ייחוס
              משותפת.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

/** Rank both columns so the disagreement between them is visible, not claimed. */
function rankRows(rows: OutletRow[]) {
  const withRaw = rows.filter((r) => r.raw_mean !== null && r.mean !== null);
  const rawOrder = [...withRaw].sort(
    (a, b) => (a.raw_mean as number) - (b.raw_mean as number),
  );
  const devOrder = [...withRaw].sort(
    (a, b) => (a.mean as number) - (b.mean as number),
  );
  return rows.map((r) => {
    const rawRank = rawOrder.indexOf(r) + 1 || null;
    const devRank = devOrder.indexOf(r) + 1 || null;
    return { ...r, rawRank, devRank, flipped: !!rawRank && rawRank !== devRank };
  });
}

/* ── 2. the bootstrap, and what it refuses to answer ────────────── */

function Interval({ facts }: Props) {
  const s = facts?.stats;
  const c = s?.constants;
  const curve = s?.curve;
  const maxWidth = Math.max(...(curve?.points.map((p) => p.width) ?? [1]));
  const full = curve?.points[curve.points.length - 1];
  const span = 0.08;
  const pairing = s?.pairing;
  const pair = pairing?.pairs[0];

  // The last checkpoint that doubles its predecessor — the measured version of
  // "how much does another n buy", which is what licenses the estimate below.
  const doubled = (curve?.points ?? [])
    .map((p, i) => ({ p, prev: curve?.points[i - 1] }))
    .filter((x) => x.prev && x.p.n === x.prev.n * 2)
    .pop();

  const withCi = s
    ? s.metrics.flatMap((m) => m.outlets).filter((r) => r.mean !== null)
    : [];
  const sig = withCi.filter((r) => r.significant);
  const noCi = s
    ? s.metrics[0]?.outlets.filter((r) => r.mean === null) ?? []
    : [];
  // The widest interval on the wall, named from the data rather than from
  // whichever outlet happened to be widest when this was written.
  const widest = withCi.reduce<OutletRow | null>(
    (a, b) =>
      a && (a.hi as number) - (a.lo as number) >
      (b.hi as number) - (b.lo as number)
        ? a
        : b,
    null,
  );

  return (
    <Stage cols="grid-cols-[44%_1fr]">
      <Panel
        title={c ? `‏${num(c.bootstrap_iterations)} דגימות מחדש במקום הנחת התפלגות` : "הבוטסטראפ"}
        hint={c ? `זרע ${c.bootstrap_seed} · אותם מספרים בכל לולאה` : undefined}
      >
        {c && curve && full ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              בוטסטראפ — דגימה חוזרת מהמדידה עצמה. נוסחה סגורה הייתה דורשת הנחת
              התפלגות שמדגם בגודל הזה לא מצדיק, ולכן הרווח נבנה מ־
              {num(c.bootstrap_iterations)} דגימות עם החזרה.
            </p>
            <div>
              <div className="mb-1 text-[15px] font-bold">
                רוחב הרווח לפי מספר האירועים · {curve.source_he}
              </div>
              <div className="flex flex-col gap-1">
                {curve.points.map((pt) => (
                  <div key={pt.n} className="flex items-center gap-2.5">
                    <span
                      dir="ltr"
                      className="w-[34px] shrink-0 text-left font-mono text-[13.5px] text-[var(--dk-ink-2)]"
                    >
                      n={pt.n}
                    </span>
                    <div className="h-3.5 flex-1 overflow-hidden rounded-md bg-[var(--dk-surface-2)]">
                      <div
                        className="h-full rounded-md bg-[var(--dk-accent)]"
                        style={{ width: `${(pt.width / maxWidth) * 100}%` }}
                      />
                    </div>
                    <span
                      dir="ltr"
                      className="w-[54px] shrink-0 text-left font-mono text-[13.5px] text-[var(--dk-ink-2)]"
                    >
                      {pt.width.toFixed(4)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            {doubled?.prev && (
              <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
                הכפלת המדגם מ־{doubled.prev.n} ל־{doubled.p.n} אירועים צמצמה את
                הרוחב פי {(doubled.prev.width / doubled.p.width).toFixed(2)}.
                אומדן באותו קצב: רווח של {(full.width / 2).toFixed(4)} דורש
                בערך {num(full.n * 4)} אירועים.
              </p>
            )}
            <Caveat>
              מתחת ל־{c.bootstrap_min_n} תצפיות הפונקציה מחזירה{" "}
              <span dir="ltr" className="font-mono">
                None
              </span>{" "}
              ולא מספר.{" "}
              {noCi.length > 0
                ? `${noCi[0].source_he} מופיעה ב־${noCi[0].n} אירוע בלבד, ולכן היא מקבלת קו במקום רווח — ולא רווח רחב שנראה כמו מדידה.`
                : "ערוץ מתחת לרצפה מופיע עם קו במקום רווח."}
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={`‏${sig.length} מתוך ${withCi.length} הרווחים אינם נוגעים באפס`}
        hint="סטייה תוך־אירועית · רווח 95%"
      >
        {s && c && widest ? (
          <div className="flex flex-col gap-3">
            {s.metrics.map((m) => (
              <div key={m.key}>
                <div className="mb-1 text-[15px] font-bold">{m.label_he}</div>
                <div className="flex flex-col gap-1.5">
                  {m.outlets.map((r) => (
                    <div key={r.source} className="flex items-center gap-2.5">
                      <span className="w-[74px] shrink-0 text-[14.5px] font-semibold">
                        {r.source_he}
                      </span>
                      <span
                        dir="ltr"
                        className="w-[34px] shrink-0 text-left font-mono text-[13px] text-[var(--dk-ink-3)]"
                      >
                        {r.n}
                      </span>
                      {r.lo !== null && r.hi !== null && r.mean !== null ? (
                        <IntervalBar
                          lo={r.lo}
                          hi={r.hi}
                          mean={r.mean}
                          span={span}
                        />
                      ) : (
                        <span className="flex-1 text-[13.5px] text-[var(--dk-ink-3)]">
                          מתחת לרצפת התצפיות — אין רווח סמך
                        </span>
                      )}
                      <span
                        dir="ltr"
                        className="w-[58px] shrink-0 text-left text-[13px]"
                      >
                        <P
                          value={r.p}
                          alpha={c.alpha}
                          res={2 / c.bootstrap_iterations}
                        />
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              הקו האנכי הוא אפס, ורווח שחוצה אותו אומר שהערוץ לא נבדל מחציון
              הסיפורים שסיקר. הרחב ביותר הוא של {widest.source_he} (
              {((widest.hi as number) - (widest.lo as number)).toFixed(4)})
              {widest.source === "haaretz"
                ? " — מהכתבות שלו נשמרת פסקה אחת בלבד, כי הגוף מאחורי תשלום."
                : "."}
            </p>
            {pairing && pair && (
              <Caveat>
                {pairing.two_version} מתוך {pairing.events} האירועים הם זוגות,
                ובזוג שתי הסטיות הן בהכרח{" "}
                <span dir="ltr" className="font-mono">
                  +d/2
                </span>{" "}
                ו־
                <span dir="ltr" className="font-mono">
                  −d/2
                </span>{" "}
                — השוואה אחת שנרשמה פעמיים. {pairing.top_pair_two_version} מהם{" "}
                {pair.a_he} מול {pair.b_he}, ולכן שתי השורות שאינן נוגעות באפס
                הן ברובן אותו ממצא.
              </Caveat>
            )}
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

/* ── 3. change point, said only next to the power ───────────────── */

function ScanRow({
  scan,
  alpha,
  res,
}: {
  scan: ChangeScan;
  alpha: number;
  res: number;
}) {
  return (
    <tr className="border-t border-[var(--dk-border)]/60">
      <td className="py-1 font-semibold">{scan.source_he}</td>
      <td className="py-1 font-mono text-[13.5px] text-[var(--dk-ink-3)]" dir="ltr">
        {scan.n}
      </td>
      <td className="py-1 text-[13.5px] text-[var(--dk-ink-2)]" dir="ltr">
        {scan.at ?? "—"}
      </td>
      <td className="py-1 font-mono text-[13.5px]" dir="ltr">
        {scan.shift === null ? "—" : signed(scan.shift)}
      </td>
      <td className="py-1 text-[13.5px]">
        <P value={scan.p} alpha={alpha} res={res} />
      </td>
      <td className="py-1 text-[13px]">
        {scan.too_short ? (
          <span className="text-[var(--dk-ink-3)]">קצר מדי לפיצול</span>
        ) : scan.detected ? (
          <Chip tone="bad">חצה {alpha}</Chip>
        ) : (
          <span className="text-[var(--dk-ink-3)]">אין שינוי</span>
        )}
      </td>
    </tr>
  );
}

function Change({ facts }: Props) {
  const s = facts?.stats;
  const c = s?.constants;
  const scans = s?.scans.filter((x) => x.metric === "dominance") ?? [];
  const hit = scans.find((x) => x.detected);
  const half = s?.power.rows.map((r) => r.power_half_sd) ?? [];

  return (
    <Stage cols="grid-cols-[52%_1fr]">
      <Panel
        title={
          c
            ? `‏${num(c.permutation_iterations)} ערבובים של הזמן, לא טבלת התפלגות`
            : "הסריקה"
        }
        hint={c ? `לפחות ${c.min_segment} תצפיות בכל צד` : undefined}
      >
        {scans.length > 0 && c ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              הגלאי לוקח את הפיצול החזק ביותר בסדרה, והמובהקות מגיעה ממבחן
              תמורות: {num(c.permutation_iterations)} ערבובים של סדר הזמן.
              טבלת התפלגות לא הייתה מוצדקת כאן — הסדרה קצרה ורחוקה מנורמלית.
            </p>
            <table className="w-full text-[15px]">
              <thead>
                <tr className="text-[13.5px] text-[var(--dk-ink-3)]">
                  <th className="pb-1 text-right font-medium">ערוץ</th>
                  <th className="pb-1 text-right font-medium">n</th>
                  <th className="pb-1 text-right font-medium">נקודת הפיצול</th>
                  <th className="pb-1 text-right font-medium">הפרש</th>
                  <th className="pb-1 text-right font-medium">p</th>
                  <th className="pb-1 text-right font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {scans.map((scan) => (
                  <ScanRow
                    key={scan.source}
                    scan={scan}
                    alpha={c.alpha}
                    res={1 / (c.permutation_iterations + 1)}
                  />
                ))}
              </tbody>
            </table>
            {hit && hit.p !== null && (
              <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
                תוצאה אחת ירדה מתחת ל־{c.alpha}, ובקושי:{" "}
                <span dir="ltr" className="font-mono text-[var(--dk-bad)]">
                  {hit.p.toFixed(4)}
                </span>{" "}
                על סדרה של {hit.n} תצפיות.
              </p>
            )}
            <Caveat>
              ציר הזמן הוא{" "}
              <span dir="ltr" className="font-mono">
                first_seen_at
              </span>{" "}
              — מועד סריקה, לא פרסום. נקודת שינוי בסדרה כזו יכולה להיות עדות על
              לוח הזמנים של הקרולר לפחות באותה מידה שהיא עדות על העיתון.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={`"לא נמצא שינוי" נאמר רק יחד עם העוצמה`}
        hint={s ? `${s.power.iterations} הזרקות לכל שורה` : undefined}
      >
        {s?.power.rows.length ? (
          <div className="flex flex-col gap-3">
            <table className="w-full text-[15px]" dir="ltr">
              <thead>
                <tr className="text-[13.5px] text-[var(--dk-ink-3)]">
                  <th className="pb-1 text-left font-medium">n</th>
                  <th className="pb-1 text-left font-medium">shift 1.0 sd</th>
                  <th className="pb-1 text-left font-medium">shift 0.5 sd</th>
                </tr>
              </thead>
              <tbody>
                {s.power.rows.map((r) => (
                  <tr key={r.n} className="border-t border-[var(--dk-border)]/60">
                    <td className="py-1 font-mono">{r.n}</td>
                    <td className="py-1 font-mono text-[var(--dk-accent)]">
                      {pct(r.power_1sd)}
                    </td>
                    <td className="py-1 font-mono text-[var(--dk-bad)]">
                      {pct(r.power_half_sd)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              בסדרות בגודל הזה שינוי של חצי סטיית תקן נתפס ב־
              {pct(Math.min(...half))}–{pct(Math.max(...half))} מהמקרים בלבד.
              לכן &quot;לא נמצאה נקודת שינוי&quot; נקרא כאן{" "}
              <b>&quot;לא נמצא שינוי בגודל שהיינו יכולים לראות&quot;</b>.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <CodeRef path={s.power.source} />
              <span className="text-[13px] text-[var(--dk-ink-3)]">
                נקראת מהקובץ שהריצה מציגה, לא מחושבת מחדש
              </span>
            </div>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

/* ── 4. the floor, the correction, and the one sentence left ────── */

function CellRow({ cell, span }: { cell: TopicCellRow; span: number }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="w-[62px] shrink-0 text-[14px] font-semibold">
        {cell.source_he}
      </span>
      <span className="w-[62px] shrink-0 text-[14px] text-[var(--dk-ink-2)]">
        {cell.topic_he}
      </span>
      <span
        dir="ltr"
        className={`w-[26px] shrink-0 text-left font-mono text-[13px] ${cell.usable ? "text-[var(--dk-ink-2)]" : "text-[var(--dk-bad)]"}`}
      >
        {cell.n}
      </span>
      {cell.lo !== null && cell.hi !== null && cell.mean !== null ? (
        <IntervalBar
          lo={cell.lo}
          hi={cell.hi}
          mean={cell.mean}
          span={span}
          muted={!cell.usable}
        />
      ) : (
        <span className="flex-1" />
      )}
      <span className="w-[74px] shrink-0 text-start text-[12.5px]">
        {cell.tempting ? (
          <Chip tone="bad">נדחה</Chip>
        ) : cell.usable ? (
          <span className="text-[var(--dk-ink-3)]">שמיש</span>
        ) : (
          <span className="text-[var(--dk-ink-3)]">n נמוך</span>
        )}
      </span>
    </div>
  );
}

function Claim({ facts }: Props) {
  const s = facts?.stats;
  const m = s?.multiplicity;
  const meta = s?.cells_meta.find((x) => x.key === "dominance");
  const tempting = (s?.cells["dominance"] ?? []).filter((r) => r.tempting);

  return (
    <Stage cols="grid-cols-[44%_1fr]">
      <Panel
        title={
          meta && s
            ? `רצפת ${s.constants.min_cell_events} האירועים פוסלת ${meta.total - meta.usable} מ־${meta.total} התאים`
            : "מטריצת נושא×ערוץ"
        }
        hint={meta ? meta.label_he : undefined}
      >
        {meta && s ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              פיצול לפי נושא חושף מסגור של ביט אחד שמתקזז במספר המצרפי. המחיר
              שלו הוא שכל תא מקבל רק חלק מהאירועים.
            </p>
            <div className="grid grid-cols-3 gap-2.5">
              <Big value={`${meta.total}`} label="תאים במטריצה" tone="accent" />
              <Big
                value={`${meta.usable}`}
                label={`עוברים את הרצפה (n ≥ ${s.constants.min_cell_events})`}
                tone="warn"
              />
              <Big
                value={`${meta.significant}`}
                label="מובהקים ומדווחים"
                tone="good"
              />
            </div>
            {tempting.length > 0 && (
              <>
                <div className="flex flex-col gap-1">
                  {tempting.map((cell) => (
                    <CellRow
                      key={`${cell.source}-${cell.topic_he}`}
                      cell={cell}
                      span={0.14}
                    />
                  ))}
                </div>
                <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
                  {meta.tempting} התאים האלה נראים כמו ממצא — הרווח שלהם אינו
                  נוגע באפס — וכולם נפסלים על n. תא על {tempting[0].n} אירועים
                  הוא עדות על {tempting[0].n} אירועים.
                </p>
              </>
            )}
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          m
            ? `‏${m.tests} בדיקות רצו כאן, ${m.survivors.length === 1 ? "ממצא אחד שורד" : `${m.survivors.length} ממצאים שורדים`}`
            : "ריבוי בדיקות"
        }
        hint={
          m
            ? `${m.ci_tests} רווחים · ${m.cell_tests} תאים · ${m.scan_tests} סריקות`
            : undefined
        }
      >
        {m && s ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              ברמת מובהקות{" "}
              <span dir="ltr" className="font-mono">
                {m.alpha}
              </span>{" "}
              רעש לבדו היה נותן{" "}
              <span dir="ltr" className="font-mono text-[var(--dk-bad)]">
                {m.expected_false}
              </span>{" "}
              תוצאות מובהקות. קיבלנו {m.hits.length}, והסף אחרי תיקון Bonferroni
              הוא{" "}
              <span dir="ltr" className="font-mono">
                {m.bonferroni.toFixed(5)}
              </span>
              .
            </p>
            <div className="flex flex-col gap-1.5">
              {m.hits.map((h) => {
                const lives = h.p < m.bonferroni;
                return (
                  <div
                    key={h.what}
                    className={`flex items-center gap-2.5 rounded-lg border px-3 py-1.5 ${
                      lives
                        ? "border-[var(--dk-good)]/45 bg-[var(--dk-good)]/8"
                        : "border-[var(--dk-border)] opacity-60"
                    }`}
                  >
                    <span className="text-[15px] font-semibold">{h.what}</span>
                    <span dir="ltr" className="ms-auto font-mono text-[14px]">
                      <P
                        value={h.p}
                        alpha={m.alpha}
                        res={2 / s.constants.bootstrap_iterations}
                      />
                    </span>
                    <span className="w-[62px] text-left text-[13px]">
                      {lives ? (
                        <Chip tone="good">שורד</Chip>
                      ) : (
                        <span className="text-[var(--dk-ink-3)]">נופל</span>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
            {m.survivors.length > 0 ? (
              <p className="rounded-xl border border-[var(--dk-good)]/45 bg-[var(--dk-good)]/8 px-3.5 py-2.5 text-[16px] leading-snug">
                כשמשווים גרסאות של <b>אותו סיפור</b>,{" "}
                <b>{m.survivors[0].source_he}</b> יוצא{" "}
                {m.survivors[0].direction === "below" ? "נמוך" : "גבוה"} מחציון
                האירוע ב{m.survivors[0].metric_he} באופן עקבי. כל השאר על הקיר
                הזה תואם רעש.
              </p>
            ) : (
              <p className="text-[15px] text-[var(--dk-ink-2)]">
                אף ממצא לא שרד את התיקון.
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <Chip tone="bad">לא &quot;הערוץ מוטה&quot;</Chip>
              <Chip tone="bad">לא כיוון פוליטי</Chip>
              <Chip tone="bad">לא סיבתיות</Chip>
              <Chip tone="neutral">רק: פחות מילות לקסיקון בחלון</Chip>
            </div>
            <CodeRef path="demo/core/framing.py · outlet_deviation, bootstrap_ci" />
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}
