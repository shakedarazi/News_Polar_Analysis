"use client";

import { useState } from "react";
import type { Facts, OutletRow, TopicCellRow } from "./facts";
import { Chip, CodeRef, Panel, Stage, SubNav, type TabDef } from "./kit";

const TABS: TabDef[] = [
  { id: "within", label_he: "למה משווים רק בתוך אותו סיפור" },
  { id: "survives", label_he: "מה שורד מ־19 הבדיקות" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the statistics layer — the only place in the demo whose job is to
 * take findings away.
 *
 * Two tabs, four panels. First the decision that makes any comparison legal:
 * measure every version against its own event's median, because most of the
 * variation between outlets is which stories they picked. Then what is left
 * after the interval, the floor and the correction: nineteen tests ran, three
 * came in under 0.05, and exactly one clears Bonferroni.
 *
 * Dropped on purpose (see demo/README.md items 8, 31, 60): the change-point
 * scan and its power table. The time axis is `first_seen_at` — crawl time, not
 * publication — so a change point there is as much evidence about our schedule
 * as about the paper, and the one scan that cleared 0.05 dies at the correction
 * anyway. It stays in the count of 19 and in the list of what fell.
 */
export function StatsModule({ facts }: Props) {
  const [tab, setTab] = useState("within");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "within" && <WithinEvent facts={facts} />}
      {tab === "survives" && <Survives facts={facts} />}
    </div>
  );
}

/* ── shared ─────────────────────────────────────────────────────── */

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

/* ── 1. the comparison that is allowed, and how sharp it is ─────── */

function WithinEvent({ facts }: Props) {
  const s = facts?.stats;
  const c = s?.constants;
  const dom = s?.metrics.find((m) => m.key === "dominance");
  const between = dom?.variance.between_share ?? null;
  const within = dom?.variance.within_share ?? null;
  const ranked = dom ? rankRows(dom.outlets) : [];
  const lowRaw = ranked.find((r) => r.rawRank === 1);
  const lowDev = ranked.find((r) => r.devRank === 1);

  const curve = s?.curve;
  const full = curve?.points[curve.points.length - 1];
  const doubled = (curve?.points ?? [])
    .map((p, i) => ({ p, prev: curve?.points[i - 1] }))
    .filter((x) => x.prev && x.p.n === x.prev.n * 2)
    .pop();

  const span = 0.08;
  const withCi = s
    ? s.metrics.flatMap((m) => m.outlets).filter((r) => r.mean !== null)
    : [];
  const sig = withCi.filter((r) => r.significant);
  const pairing = s?.pairing;
  const pair = pairing?.pairs[0];

  return (
    <Stage cols="grid-cols-[48%_1fr]">
      <Panel
        title={
          between !== null
            ? `‏${pct(between)} מההבדל בין הערוצים הוא איזה סיפור, לא איך`
            : "פירוק השונות"
        }
        hint={dom && s ? `${dom.n} גרסאות · ${s.events} אירועים` : undefined}
      >
        {dom && between !== null && within !== null && lowRaw && lowDev ? (
          <div className="flex flex-col gap-3.5">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              הרצון הטבעי הוא לחשב ממוצע לכל ערוץ ולדרג. הבעיה שהמספר הזה מערבב
              שתי שאלות שונות: אילו סיפורים הערוץ בחר לסקר, ואיך כתב אותם. ‏
              {pct(between)} מהפער הוא הראשונה.
            </p>
            <div className="flex h-11 overflow-hidden rounded-lg border border-[var(--dk-border)]">
              <div
                className="flex flex-col items-center justify-center bg-[var(--dk-bad)]/70 text-[14px] font-bold leading-tight"
                style={{ width: `${between * 100}%` }}
              >
                <span>{pct(between)}</span>
                <span className="font-semibold">איזה סיפור</span>
              </div>
              <div
                className="flex flex-col items-center justify-center bg-[var(--dk-good)]/70 text-[14px] font-bold leading-tight"
                style={{ width: `${within * 100}%` }}
              >
                <span>{pct(within)}</span>
                <span className="font-semibold">איך סיפרו</span>
              </div>
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              פירוק השונות על {dom.n} גרסאות: כמה מהפער בדומיננטיות — החלק של
              יחידת המדידה ששייך לקטגוריה החזקה בה — מוסבר בהבדל בין אירועים,
              וכמה בתוך אותו אירוע.
            </p>
            <div
              dir="ltr"
              className="rounded-lg border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)]/40 px-3 py-2 text-center font-mono text-[15.5px] text-[var(--dk-accent)]"
            >
              deviation = value − median(versions of the same event)
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              לכן כל גרסה נמדדת מול חציון האירוע שלה בלבד — חציון ולא ממוצע, כדי
              שגרסה חריגה אחת לא תזיז את נקודת הייחוס.
            </p>
            <table className="w-full text-[15.5px]">
              <thead>
                <tr className="text-[13.5px] text-[var(--dk-ink-3)]">
                  <th className="pb-1 text-right font-medium">ערוץ</th>
                  <th className="pb-1 text-right font-medium">גרסאות</th>
                  <th className="pb-1 text-right font-medium">ממוצע גולמי</th>
                  <th className="pb-1 text-right font-medium">מקום</th>
                  <th className="pb-1 text-right font-medium">סטייה מהחציון</th>
                  <th className="pb-1 text-right font-medium">מקום</th>
                </tr>
              </thead>
              <tbody>
                {ranked.map((r) => (
                  <tr key={r.source} className="border-t border-[var(--dk-border)]/60">
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
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              ממוצע גולמי: הממוצע של כל כתבות הערוץ, ‏0 עד 1. סטייה: אותה כתבה
              מול חציון האירוע שלה — מינוס פירושו פחות טעון מהערוצים שסיקרו את
              אותו סיפור. ‏&ldquo;מקום 1&rdquo; הוא הנמוך ביותר בכל עמודה.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              מה זה קונה: הדירוג מתהפך. הממוצע הגולמי הנמוך ביותר הוא של{" "}
              {lowRaw.source_he}, והסטייה הנמוכה ביותר של {lowDev.source_he}.
              אותן כתבות, שתי שיטות, שתי תשובות — ורק אחת מהן משווה סיפור
              לסיפור.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          c
            ? `${sig.length} מ־${withCi.length} הרווחים אינם נוגעים באפס`
            : "רווחי הסמך"
        }
        hint={c ? `${num(c.bootstrap_iterations)} דגימות · זרע ${c.bootstrap_seed}` : undefined}
      >
        {s && c && curve && full ? (
          <div className="flex flex-col gap-3.5">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              לכל סטייה צריך לדעת כמה היא בטוחה. נוסחה סגורה הייתה דורשת להניח
              איך התוצאות מתפלגות — הנחה שמדגם בגודל הזה לא מצדיק. במקום זה
              בוטסטראפ: {num(c.bootstrap_iterations)} דגימות חוזרות מהמדידה
              עצמה, בזרע קבוע, כך שאותה ריצה מחזירה בדיוק את אותו רווח.
            </p>
            {s.metrics.map((m) => (
              <div key={m.key}>
                <div className="mb-1.5 text-[15.5px] font-bold">{m.label_he}</div>
                <div className="flex flex-col gap-1.5">
                  {m.outlets.map((r) => (
                    <div key={r.source} className="flex items-center gap-2.5">
                      <span className="w-[74px] shrink-0 text-[14.5px] font-semibold">
                        {r.source_he}
                      </span>
                      <span
                        dir="ltr"
                        className="w-[30px] shrink-0 text-left font-mono text-[13px] text-[var(--dk-ink-3)]"
                      >
                        {r.n}
                      </span>
                      {r.lo !== null && r.hi !== null && r.mean !== null ? (
                        <IntervalBar lo={r.lo} hi={r.hi} mean={r.mean} span={span} />
                      ) : (
                        <span className="flex-1 text-[13.5px] text-[var(--dk-ink-3)]">
                          פחות מ־{c.bootstrap_min_n} אירועים — לא מוחזר רווח
                        </span>
                      )}
                      <span dir="ltr" className="w-[58px] shrink-0 text-left text-[13px]">
                        <P value={r.p} alpha={c.alpha} res={2 / c.bootstrap_iterations} />
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              הקו האנכי הוא אפס. רווח שחוצה אותו — הערוץ לא נבדל מהחציון של
              הסיפורים שסיקר. ‏p הוא הסיכוי לראות פער כזה גם כשאין הבדל אמיתי;
              קטן = פחות סביר שזה מקרה. המספר משמאל לשם הוא כמה אירועים נכנסו.
            </p>
            {doubled?.prev && (
              <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
                כמה עוד נתונים היו קונים: הכפלת המדגם מ־{doubled.prev.n} ל־
                {doubled.p.n} אירועים צימצמה את רוחב הרווח פי{" "}
                {(doubled.prev.width / doubled.p.width).toFixed(2)}. באותו קצב,
                חצי מהרוחב הנוכחי דורש בערך {num(full.n * 4)} אירועים — כלומר
                כמה חודשי איסוף, לא עוד יום.
              </p>
            )}
            {pairing && pair && (
              <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
                ‏{pairing.two_version} מ־{pairing.events} האירועים סוקרו בשני
                ערוצים בלבד, ובזוג החציון הוא נקודת האמצע: שתי הסטיות הן בהכרח
                תמונת ראי זו של זו. ‏{pairing.top_pair_two_version} מהזוגות הם{" "}
                {pair.a_he} מול {pair.b_he}, ולכן שתי השורות שאינן נוגעות באפס
                הן ברובן אותו ממצא שנרשם פעמיים.
              </p>
            )}
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

/* ── 2. what is left after the floor and the correction ─────────── */

function CellRow({ cell, span }: { cell: TopicCellRow; span: number }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="w-[62px] shrink-0 text-[14.5px] font-semibold">
        {cell.source_he}
      </span>
      <span className="w-[62px] shrink-0 text-[14.5px] text-[var(--dk-ink-2)]">
        {cell.topic_he}
      </span>
      <span
        dir="ltr"
        className="w-[26px] shrink-0 text-left font-mono text-[13px] text-[var(--dk-bad)]"
      >
        {cell.n}
      </span>
      {cell.lo !== null && cell.hi !== null && cell.mean !== null ? (
        <IntervalBar lo={cell.lo} hi={cell.hi} mean={cell.mean} span={span} muted />
      ) : (
        <span className="flex-1" />
      )}
      <span className="w-[52px] shrink-0 text-start text-[12.5px]">
        <Chip tone="bad">נדחה</Chip>
      </span>
    </div>
  );
}

function Survives({ facts }: Props) {
  const s = facts?.stats;
  const m = s?.multiplicity;
  const meta = s?.cells_meta.find((x) => x.key === "dominance");
  const tempting = (s?.cells["dominance"] ?? []).filter((r) => r.tempting);

  return (
    <Stage cols="grid-cols-[50%_1fr]">
      <Panel
        title={
          m
            ? `${m.tests} בדיקות רצו כאן, ${m.hits.length} ירדו מתחת ל־${m.alpha}, אחת שורדת`
            : "ריבוי בדיקות"
        }
        hint={m ? `${m.ci_tests} רווחים · ${m.cell_tests} תאים · ${m.scan_tests} סריקות` : undefined}
      >
        {m && s ? (
          <div className="flex flex-col gap-3.5">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              ככל שבודקים יותר דברים, גדל הסיכוי שמשהו ייראה מובהק במקרה. ברמת{" "}
              <span dir="ltr" className="font-mono">
                {m.alpha}
              </span>{" "}
              ועל {m.tests} בדיקות, רעש לבדו היה מייצר{" "}
              <span dir="ltr" className="font-mono text-[var(--dk-bad)]">
                {m.expected_false}
              </span>{" "}
              תוצאות מובהקות. קיבלנו {m.hits.length} — כלומר בלי תיקון, אי אפשר
              להבדיל בין ממצא לבין מזל.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              תיקון Bonferroni מחלק את הסף במספר הבדיקות:{" "}
              <span dir="ltr" className="font-mono">
                {m.alpha} / {m.tests} = {m.bonferroni.toFixed(5)}
              </span>
              . זו החומרה שקונה את הזכות לומר משפט אחד ברצינות.
            </p>
            <div className="flex flex-col gap-1.5">
              {m.hits.map((h) => {
                const lives = h.p < m.bonferroni;
                return (
                  <div
                    key={h.what}
                    className={`flex items-center gap-2.5 rounded-lg border px-3 py-2 ${
                      lives
                        ? "border-[var(--dk-good)]/45 bg-[var(--dk-good)]/8"
                        : "border-[var(--dk-border)] opacity-60"
                    }`}
                  >
                    <span className="text-[15.5px] font-semibold">{h.what}</span>
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
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              שלוש התוצאות שירדו מתחת ל־{m.alpha}, מול הסף המתוקן{" "}
              {m.bonferroni.toFixed(5)}. ‏&ldquo;נקודת שינוי&rdquo; היא רגע שבו סדרת הערוץ
              מתחלפת ברמה — היא עברה את {m.alpha} ולא את התיקון.
            </p>
            {m.survivors.length > 0 && (
              <p className="rounded-xl border border-[var(--dk-good)]/45 bg-[var(--dk-good)]/8 px-3.5 py-2.5 text-[17px] leading-snug">
                כשמשווים גרסאות של <b>אותו סיפור</b>,{" "}
                <b>{m.survivors[0].source_he}</b> יוצא{" "}
                {m.survivors[0].direction === "below" ? "נמוך" : "גבוה"} מחציון
                האירוע ב{m.survivors[0].metric_he} באופן עקבי. כל השאר על הקיר
                הזה תואם רעש.
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <Chip tone="bad">לא &quot;הערוץ מוטה&quot;</Chip>
              <Chip tone="bad">לא כיוון פוליטי</Chip>
              <Chip tone="bad">לא סיבתיות</Chip>
              <Chip tone="neutral">רק: פחות מילות מילון ביחידה</Chip>
            </div>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          meta && s
            ? `${meta.total - meta.usable} מ־${meta.total} התאים נפסלים לפני שמסתכלים על התוצאה`
            : "מטריצת נושא×ערוץ"
        }
        hint={meta ? `רצפה: ${facts?.stats.constants.min_cell_events} אירועים לתא` : undefined}
      >
        {meta && s ? (
          <div className="flex flex-col gap-3.5">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              פיצול לפי נושא הוא הפיתוי הגדול: הוא חושף מסגור שמתקזז במספר
              המצרפי. המחיר הוא שכל תא מקבל רק חלק מהאירועים, ומדגם קטן מספיק
              מייצר כמעט כל ממצא שרוצים.
            </p>
            <div className="grid grid-cols-3 gap-2.5">
              {[
                { v: meta.total, l: "תאים של ערוץ × נושא", t: "accent" },
                { v: meta.usable, l: `עוברים את רצפת ${s.constants.min_cell_events} האירועים`, t: "warn" },
                { v: meta.significant, l: "מובהקים ומדווחים", t: "good" },
              ].map((b) => (
                <div
                  key={b.l}
                  className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-2.5 py-3 text-center"
                >
                  <div
                    dir="ltr"
                    className={`text-[38px] font-black leading-[1.1] ${
                      b.t === "warn"
                        ? "text-[var(--dk-warn)]"
                        : b.t === "good"
                          ? "text-[var(--dk-good)]"
                          : "text-[var(--dk-accent)]"
                    }`}
                  >
                    {b.v}
                  </div>
                  <div className="mt-1.5 text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
                    {b.l}
                  </div>
                </div>
              ))}
            </div>
            {tempting.length > 0 && (
              <>
                <div className="flex flex-col gap-1.5">
                  {tempting.map((cell) => (
                    <CellRow
                      key={`${cell.source}-${cell.topic_he}`}
                      cell={cell}
                      span={0.14}
                    />
                  ))}
                </div>
                <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
                  שני תאים שנראים כמו ממצא: הרווח כולו מתחת לאפס. המספר האדום
                  הוא כמה אירועים יש בתא, והוא הסיבה שהם נדחים.
                </p>
                <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
                  הכלל נקבע לפני שראינו את התוצאה, ולכן הוא גם חל עליה: תא על{" "}
                  {tempting[0].n} אירועים הוא עדות על {tempting[0].n} אירועים.
                  הם על המסך דווקא כדי להראות איך נראית תוצאה שאסור לדווח.
                </p>
              </>
            )}
            <CodeRef path="demo/core/framing.py · outlet_deviation, bootstrap_ci" />
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}
