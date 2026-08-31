"use client";

import { useState } from "react";
import type { ChangeScan, Facts, OutletRow, TopicCellRow } from "./facts";
import {
  Caveat,
  Chip,
  CodeRef,
  MetricCard,
  Node,
  Panel,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "why", label_he: "למה לא ממוצע לערוץ" },
  { id: "within", label_he: "ההשוואה התוך־אירועית" },
  { id: "ci", label_he: "רווח סמך" },
  { id: "cells", label_he: "מטריצת נושא×ערוץ" },
  { id: "change", label_he: "נקודת שינוי ועוצמה" },
  { id: "claim", label_he: "מה מותר להגיד" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the statistics layer — the only place in the demo whose job is to
 * take findings away.
 *
 * Everything upstream produces numbers. This module asks which of them survive
 * being asked twice: 19 significance tests were run across the wall, three came
 * in under 0.05, and exactly one clears a Bonferroni threshold. The module is
 * built so the audience can watch that subtraction happen rather than be told
 * about it.
 */
export function StatsModule({ facts }: Props) {
  const [tab, setTab] = useState("why");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "why" && <WhyNotRaw facts={facts} />}
      {tab === "within" && <Within facts={facts} />}
      {tab === "ci" && <Interval facts={facts} />}
      {tab === "cells" && <Cells facts={facts} />}
      {tab === "change" && <Change facts={facts} />}
      {tab === "claim" && <Claim facts={facts} />}
    </div>
  );
}

function signed(x: number, digits = 4): string {
  return `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(digits)}`;
}

function pct(x: number): string {
  return `${(x * 100).toFixed(0)}%`;
}

/** p-values are the module's currency — render them one way everywhere. */
function P({ value, alpha }: { value: number | null; alpha: number }) {
  if (value === null) {
    return <span className="font-mono text-[var(--dk-ink-3)]">—</span>;
  }
  const tone =
    value < alpha ? "text-[var(--dk-bad)]" : "text-[var(--dk-ink-2)]";
  return (
    <span className={`font-mono ${tone}`} dir="ltr">
      {value === 0 ? "<0.0003" : value.toFixed(4)}
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

/* ── 1. why a raw per-outlet mean answers the wrong question ────── */

function WhyNotRaw({ facts }: Props) {
  const s = facts?.stats;
  const dom = s?.metrics.find((m) => m.key === "dominance");

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[48%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="השאלה שממוצע גולמי עונה עליה">
          <div className="flex flex-col gap-2">
            <div className="flex items-stretch gap-2">
              <Node
                title="איזה סיפורים סיקרו"
                sub="בחירה מערכתית — מה בכלל נכנס לעיתון"
                tone="bad"
                wide
              />
              <Node
                title="איך סיפרו אותם"
                sub="מסגור — מה שאנחנו רוצים למדוד"
                tone="good"
                wide
              />
            </div>
            <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
              ממוצע דומיננטיות לערוץ מערבב את השניים ואי אפשר להפריד אותם
              בדיעבד. ערוץ שמסקר יותר פיגועים יקבל ציון גבוה גם אם הוא כותב
              בדיוק כמו כולם. זו לא ביקורת תיאורטית — אפשר למדוד כמה מהשונות
              נובעת מכל צד.
            </p>
          </div>
        </Panel>

        <Panel
          title="פירוק השונות"
          hint={dom ? `${dom.n} גרסאות · ${s?.events} אירועים` : undefined}
        >
          {dom && dom.variance.between_share !== null ? (
            <div className="flex flex-col gap-2.5">
              <div className="flex h-10 overflow-hidden rounded-lg border border-[var(--dk-border)]">
                <div
                  className="flex flex-col items-center justify-center bg-[var(--dk-bad)]/70 text-[13px] font-bold leading-tight"
                  style={{ width: `${dom.variance.between_share * 100}%` }}
                >
                  <span>{pct(dom.variance.between_share)}</span>
                  <span className="font-semibold">איזה סיפור</span>
                </div>
                <div
                  className="flex flex-col items-center justify-center bg-[var(--dk-good)]/70 text-[13px] font-bold leading-tight"
                  style={{ width: `${(dom.variance.within_share ?? 0) * 100}%` }}
                >
                  <span>{pct(dom.variance.within_share ?? 0)}</span>
                  <span className="font-semibold">איך סיפרו</span>
                </div>
              </div>
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                {pct(dom.variance.between_share)} מכל השונות בדומיננטיות היא
                ההבדל בין סיפורים, לא בין ערוצים שמספרים את אותו סיפור. מי
                שמדווח ממוצע גולמי מדווח בעיקר את הרוב הזה.
              </p>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="שתי השיטות על אותן כתבות בדיוק"
          hint="דומיננטיות · גרסאות האירועים"
        >
          {dom ? (
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
                {rankRows(dom.outlets).map((r) => (
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
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="מה זה משנה בפועל">
          {dom ? (
            <div className="flex flex-col gap-2.5">
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                שתי העמודות מחושבות על אותן הכתבות. הן לא מסכימות: הערוץ בעל
                הממוצע הגולמי הנמוך ביותר אינו הערוץ שכותב את הגרסה הכי פחות
                טעונה של אותו סיפור. הפער בין השיטות הוא בדיוק ההבדל בין
                &quot;מה סיקרת&quot; ל&quot;איך סיקרת&quot;.
              </p>
              <Caveat>
                גם הסטייה התוך־אירועית אינה חפה: היא מודדת מול חציון האירוע,
                כלומר מול הערוצים האחרים שסיקרו אותו. אין כאן &quot;אמת&quot;
                אובייקטיבית — יש נקודת ייחוס משותפת.
              </Caveat>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>
    </div>
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

/* ── 2. the within-event comparison itself ──────────────────────── */

function Within({ facts }: Props) {
  const s = facts?.stats;
  const p = s?.pairing;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="ההגדרה" hint="demo/core/framing.py · outlet_deviation">
          <MetricCard
            name="סטייה תוך־אירועית"
            field="deviation"
            formula="value − median(all versions of that event)"
            range="(−1, 1)"
            reads={[
              {
                value: "+0.02",
                means: "הגרסה של הערוץ טעונה ב־0.02 מהגרסה החציונית של אותו סיפור",
              },
              { value: "0.00", means: "הערוץ כתב בדיוק את הגרסה החציונית" },
              {
                value: "−0.02",
                means: "פחות טעון מהחציון — פחות מילות לקסיקון בחלון",
              },
            ]}
            measured="החציון ולא הממוצע: גרסה חריגה אחת לא מזיזה את נקודת הייחוס"
          />
        </Panel>

        <Panel title="למה חציון, ולמה גרסה אחת לכל ערוץ">
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            אם ערוץ תורם חמש גרסאות לאותו אשכול, החציון <b>הופך להיות הוא</b> —
            הוא ימדוד סטייה אפס בהגדרה, וכל השאר יימדדו מולו. לכן שלב האשכולות
            שומר גרסה אחת בלבד לכל ערוץ (המדוברת ביותר), עוד לפני שהסטטיסטיקה
            מתחילה. זו החלטה בשכבת האחזור שקיימת <b>בשביל</b> השכבה הזו.
          </p>
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="הצורה של האירועים — וזו המגבלה האמיתית"
          hint={p ? `${p.events} אירועים` : undefined}
        >
          {p ? (
            <div className="flex flex-col gap-2.5">
              <div className="grid grid-cols-2 gap-2.5">
                <Big
                  value={`${p.two_version}/${p.events}`}
                  label="אירועים עם שתי גרסאות בלבד"
                  tone="warn"
                />
                <Big
                  value={`${p.top_pair_two_version}`}
                  label={
                    p.pairs[0]
                      ? `מהם ${p.pairs[0].a_he} מול ${p.pairs[0].b_he}`
                      : "מהם אותו זוג ערוצים"
                  }
                  tone="bad"
                />
              </div>
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                באירוע עם שתי גרסאות החציון <b>הוא</b> נקודת האמצע, ולכן שתי
                הסטיות הן בהכרח{" "}
                <span dir="ltr" className="font-mono">
                  +d/2
                </span>{" "}
                ו־
                <span dir="ltr" className="font-mono">
                  −d/2
                </span>
                . אלה לא שתי תצפיות עצמאיות אלא השוואה אחת שנרשמה פעמיים — ולכן
                &quot;ynet כותב טעון יותר&quot; ו&quot;mako כותב טעון פחות&quot;
                הם ברובם <b>אותו ממצא</b>, לא שניים.
              </p>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="מי נפגש עם מי">
          {p ? (
            <table className="w-full text-[15px]">
              <tbody>
                {p.pairs.map((pair) => (
                  <tr
                    key={`${pair.a}-${pair.b}`}
                    className="border-t border-[var(--dk-border)]/60"
                  >
                    <td className="py-1 font-semibold">
                      {pair.a_he} · {pair.b_he}
                    </td>
                    <td className="py-1 font-mono text-[14px]" dir="ltr">
                      {pair.events}
                    </td>
                    <td className="py-1 text-[13.5px] text-[var(--dk-ink-3)]">
                      {pair.events < 5
                        ? "מדגם קטן מדי לדיווח"
                        : `${pct(pair.events / p.events)} מהאירועים`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>
    </div>
  );
}

/* ── 3. the bootstrap and how the interval narrows ──────────────── */

function Interval({ facts }: Props) {
  const s = facts?.stats;
  const c = s?.constants;
  const dom = s?.metrics.find((m) => m.key === "dominance");
  const curve = s?.curve;
  const maxWidth = Math.max(...(curve?.points.map((p) => p.width) ?? [1]));
  const span = 0.08;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="הבוטסטראפ" hint="demo/core/framing.py · bootstrap_ci">
          <div className="flex flex-col gap-2">
            <div className="flex items-stretch gap-1.5">
              <Node title="הסטיות שנמדדו" sub={dom ? `n=${dom.outlets[0]?.n}` : ""} wide />
              <Node
                title="דגימה מחדש עם החזרה"
                sub={c ? `${c.bootstrap_iterations.toLocaleString("en-US")} פעמים` : ""}
                tone="accent"
                wide
              />
              <Node title="אחוזונים 2.5 ו־97.5" sub="רווח 95%" tone="good" wide />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              אין כאן הנחת התפלגות. במקום נוסחה סגורה, המדידה נדגמת מחדש
              מעצמה — מה שמתאים במיוחד לגדלי מדגם קטנים ולסטיות שאינן נורמליות.
              הזרע{" "}
              <span dir="ltr" className="font-mono">
                {c?.bootstrap_seed}
              </span>{" "}
              קבוע, כדי שהקיוסק יציג את אותם מספרים בכל לולאה.
            </p>
            {c && (
              <Caveat>
                מתחת ל־{c.bootstrap_min_n} תצפיות הפונקציה מחזירה{" "}
                <span dir="ltr" className="font-mono">
                  None
                </span>{" "}
                ולא מספר. זו הסיבה שחדשות 12 מופיעה בטבלאות עם קו במקום רווח סמך
                — ולא עם רווח רחב שנראה כמו מדידה.
              </Caveat>
            )}
          </div>
        </Panel>

        <Panel
          title="הרווח מצטמצם כשהראיות מצטברות"
          hint={curve ? `${curve.source_he} · דומיננטיות` : undefined}
        >
          {curve ? (
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
          ) : (
            <Missing />
          )}
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        {s?.metrics.map((m) => (
          <Panel key={m.key} title={m.label_he} hint="סטייה תוך־אירועית · רווח 95%">
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
                    <IntervalBar lo={r.lo} hi={r.hi} mean={r.mean} span={span} />
                  ) : (
                    <span className="flex-1 text-[13.5px] text-[var(--dk-ink-3)]">
                      מתחת לרצפת התצפיות — אין רווח סמך
                    </span>
                  )}
                  <span
                    dir="ltr"
                    className="w-[58px] shrink-0 text-left text-[13px]"
                  >
                    <P value={r.p} alpha={s.constants.alpha} />
                  </span>
                </div>
              ))}
            </div>
          </Panel>
        )) ?? <Missing />}
        {s && (
          <p className="shrink-0 px-1 text-[14px] leading-snug text-[var(--dk-ink-3)]">
            הקו האנכי הוא אפס. רווח שחוצה אותו — הערוץ לא נבדל מהחציון של
            הסיפורים שסיקר. אדום = הרווח לא נוגע באפס. הצבע הזה עוד לא אומר
            שהממצא שורד; זה נבדק בלשונית האחרונה.
          </p>
        )}
      </div>
    </div>
  );
}

/* ── 4. the beat-level matrix, and the cells we refuse ───────────── */

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

function Cells({ facts }: Props) {
  const s = facts?.stats;
  const meta = s?.cells_meta.find((m) => m.key === "dominance");
  const rows = s?.cells["dominance"] ?? [];
  const tempting = rows.filter((r) => r.tempting);

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[44%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="למה בכלל לפצל לפי נושא">
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            ערוץ יכול לשבת בדיוק על החציון בסך הכל ועדיין למסגר מחדש
            <b> ביט אחד</b> באופן שיטתי, פשוט כי ביטים עם סימן הפוך מתקזזים
            במספר המצרפי. הפיצול לפי נושא האירוע הוא הדרך לראות את זה — והמחיר
            שלו הוא שכל תא מקבל רק חלק מהאירועים.
          </p>
        </Panel>

        <Panel title="מה יצא" hint={meta ? `${meta.label_he}` : undefined}>
          {meta && s ? (
            <div className="flex flex-col gap-2.5">
              <div className="grid grid-cols-3 gap-2.5">
                <Big value={`${meta.total}`} label="תאים במטריצה" tone="accent" />
                <Big
                  value={`${meta.usable}`}
                  label={`שמישים (n ≥ ${s.constants.min_cell_events})`}
                  tone="warn"
                />
                <Big
                  value={`${meta.significant}`}
                  label="מובהקים ומדווחים"
                  tone="good"
                />
              </div>
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                אפס. אחרי הפיצול לנושאים לא נשאר אף תא שגם עומד ברצפת{" "}
                {s.constants.min_cell_events} האירועים וגם הרווח שלו לא נוגע
                באפס. זה מה שיש — לא מה שהיינו רוצים שיהיה.
              </p>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="כל התאים, כולל אלה שנפסלו"
          hint="קו אנכי = אפס · אפור = מתחת לרצפה"
        >
          {rows.length > 0 ? (
            <div className="flex flex-col gap-1">
              {rows.slice(0, 10).map((cell) => (
                <CellRow
                  key={`${cell.source}-${cell.topic_he}`}
                  cell={cell}
                  span={0.14}
                />
              ))}
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="המלכודת">
          {tempting.length > 0 && s ? (
            <div className="flex flex-col gap-2">
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                {tempting.length} תאים במטריצה הזו הם בדיוק מה שנראה כמו ממצא:
                הרווח שלהם <b>לא נוגע באפס</b>. כולם נפסלים, כי n שלהם מתחת
                ל־{s.constants.min_cell_events}. תא על 6 אירועים אינו עדות על
                ערוץ — הוא עדות על שישה אירועים.
              </p>
              <div className="flex flex-col gap-1">
                {tempting.map((cell) => (
                  <div
                    key={`${cell.source}-${cell.topic_he}`}
                    className="flex items-center gap-2 rounded-lg border border-[var(--dk-bad)]/40 bg-[var(--dk-bad)]/8 px-2.5 py-1 text-[14.5px]"
                  >
                    <span className="font-semibold">{cell.source_he}</span>
                    <span className="text-[var(--dk-ink-2)]">{cell.topic_he}</span>
                    <span dir="ltr" className="font-mono text-[13.5px]">
                      n={cell.n}
                    </span>
                    <span
                      dir="ltr"
                      className="font-mono text-[13.5px] text-[var(--dk-bad)]"
                    >
                      [{cell.lo?.toFixed(4)}, {cell.hi?.toFixed(4)}]
                    </span>
                    <span className="ms-auto text-[13px] text-[var(--dk-ink-3)]">
                      לא דווח
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>
    </div>
  );
}

/* ── 5. change point + power ─────────────────────────────────────── */

function ScanRow({ scan, alpha }: { scan: ChangeScan; alpha: number }) {
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
        <P value={scan.p} alpha={alpha} />
      </td>
      <td className="py-1 text-[13px]">
        {scan.too_short ? (
          <span className="text-[var(--dk-ink-3)]">קצר מדי לפיצול</span>
        ) : scan.detected ? (
          <Chip tone="bad">חצה 0.05</Chip>
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

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[47%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="הגלאי" hint="demo/core/framing.py · detect_change_point">
          <div className="flex flex-col gap-2">
            <div
              dir="ltr"
              className="rounded-lg border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)]/40 px-3 py-2 text-center font-mono text-[15px] text-[var(--dk-accent)]"
            >
              max over t of √(t(n−t)/n) · |mean(before) − mean(after)| / sd
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              עוברים על כל נקודות הפיצול האפשריות ולוקחים את החזקה ביותר. משקל{" "}
              <span dir="ltr" className="font-mono">
                √(t(n−t)/n)
              </span>{" "}
              מונע מפיצול בקצה לנצח על רעש בלבד, ולפחות{" "}
              {c?.min_segment ?? 8} תצפיות חייבות להישאר בכל צד.
            </p>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              המובהקות לא מגיעה מטבלה אלא ממבחן תמורות:{" "}
              {c?.permutation_iterations.toLocaleString("en-US")} ערבובים של סדר
              הזמן, וסופרים כמה מהם הגיעו לסטטיסטיקה כזו. הסדרה כאן קצרה ורחוקה
              מנורמלית, ולכן זו ההשוואה היחידה שאפשר להצדיק.
            </p>
          </div>
        </Panel>

        <Panel title="עוצמה — מה בכלל היינו רואים">
          {s?.power.rows.length ? (
            <div className="flex flex-col gap-2">
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
                    <tr
                      key={r.n}
                      className="border-t border-[var(--dk-border)]/60"
                    >
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
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                בגודל הסדרות שיש לנו, שינוי של חצי סטיית תקן נתפס בפחות מחצי
                מהמקרים. לכן &quot;לא נמצאה נקודת שינוי&quot; נקרא כאן{" "}
                <b>&quot;לא נמצא שינוי בגודל שהיינו יכולים לראות&quot;</b>, ולא
                &quot;לא היה שינוי&quot;.
              </p>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="הסריקה" hint="דומיננטיות · סדרה מאוחדת לכל ערוץ">
          {scans.length > 0 && c ? (
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
                  <ScanRow key={scan.source} scan={scan} alpha={c.alpha} />
                ))}
              </tbody>
            </table>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="ההסתייגות על התוצאה היחידה שחצתה">
          {s ? (
            <div className="flex flex-col gap-2.5">
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                תוצאה אחת ירדה מתחת ל־0.05, ובקושי. ה־p שלה הוא{" "}
                <span dir="ltr" className="font-mono text-[var(--dk-bad)]">
                  {scans.find((x) => x.detected)?.p?.toFixed(4) ?? "—"}
                </span>
                , וזה לפני שמביאים בחשבון שהיא אחת מתוך {s.multiplicity.tests}{" "}
                בדיקות שרצו על הקיר הזה. בלשונית הבאה רואים מה קורה לה אחרי
                תיקון.
              </p>
              <Caveat>
                גם אילו הייתה שורדת, ציר הזמן כאן הוא{" "}
                <span dir="ltr" className="font-mono">
                  first_seen_at
                </span>{" "}
                — מועד <b>סריקה</b>, לא פרסום. &quot;נקודת שינוי&quot; בסדרה
                כזו יכולה להיות עדות על לוח הזמנים של הקרולר לפחות באותה מידה
                שהיא עדות על העיתון.
              </Caveat>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>
    </div>
  );
}

/* ── 6. what survives ───────────────────────────────────────────── */

function Claim({ facts }: Props) {
  const s = facts?.stats;
  const m = s?.multiplicity;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[47%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="כמה בדיקות רצו כאן בפועל">
          {m ? (
            <div className="flex flex-col gap-2.5">
              <div className="flex items-stretch gap-2">
                <Node
                  title={`${m.ci_tests}`}
                  sub="רווחי סמך ברמת ערוץ"
                  tone="neutral"
                  mono
                  wide
                />
                <Node
                  title={`${m.cell_tests}`}
                  sub="תאי נושא×ערוץ שמישים"
                  tone="neutral"
                  mono
                  wide
                />
                <Node
                  title={`${m.scan_tests}`}
                  sub="סריקות נקודת שינוי"
                  tone="neutral"
                  mono
                  wide
                />
              </div>
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                סך הכל <b>{m.tests}</b> בדיקות מובהקות. ברמת מובהקות{" "}
                <span dir="ltr" className="font-mono">
                  {m.alpha}
                </span>
                , מספר התוצאות ה&quot;מובהקות&quot; שצפוי מרעש בלבד הוא{" "}
                <span dir="ltr" className="font-mono text-[var(--dk-bad)]">
                  {m.expected_false}
                </span>
                . קיבלנו {m.hits.length}.
              </p>
              <Caveat>
                אם מציגים {m.tests} מספרים ומספרים על אלה שחצו את הרף, מובטח
                שיהיו כאלה. זו הסיבה שהלשונית הזו קיימת ולא נסגרה בשקט.
              </Caveat>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="הסף אחרי תיקון" hint="Bonferroni">
          {m ? (
            <div className="grid grid-cols-2 gap-2.5">
              <Big
                value={m.bonferroni.toFixed(5)}
                label={`0.05 / ${m.tests} — הרף שממצא צריך לעבור`}
                tone="warn"
              />
              <Big
                value={`${m.survivors.length}/${m.hits.length}`}
                label="מהתוצאות שחצו את 0.05 שורדות אותו"
                tone="good"
              />
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="מה עבר ומה נפל">
          {m ? (
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
                      <P value={h.p} alpha={m.alpha} />
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
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="המשפט היחיד שמותר לומר מהמסך הזה">
          {m && s ? (
            <div className="flex flex-col gap-2.5">
              {m.survivors.length > 0 ? (
                <p className="rounded-xl border border-[var(--dk-good)]/45 bg-[var(--dk-good)]/8 px-3.5 py-2.5 text-[16px] leading-snug">
                  כשמשווים גרסאות של <b>אותו סיפור</b>,{" "}
                  <b>{m.survivors[0].source_he}</b> יוצא{" "}
                  {m.survivors[0].direction === "below" ? "נמוך" : "גבוה"}{" "}
                  מחציון האירוע ב־{m.survivors[0].metric_he} באופן עקבי —
                  והממצא שורד גם אחרי תיקון ל־{m.tests} בדיקות. כל השאר על הקיר
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
              <div className="flex items-center gap-2">
                <CodeRef path="demo/core/framing.py · outlet_deviation, bootstrap_ci" />
              </div>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>
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
