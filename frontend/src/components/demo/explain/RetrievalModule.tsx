"use client";

import { useState } from "react";
import type { Facts, RetrievalNeighbour } from "./facts";
import {
  BarRow,
  Caveat,
  Chip,
  CodeRef,
  Panel,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "why", label_he: "למה לא מילים" },
  { id: "index", label_he: "האינדקס" },
  { id: "cut", label_he: "הסף והחלון" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the retrieval layer — the first place in the system where a learned
 * model earns its keep.
 *
 * Three decisions, one per tab: pay for embeddings because the free keyword
 * baseline was measured and lost; hold the index as a numpy matrix because at
 * this size an approximate index buys nothing and adds a process that can fall
 * over mid-exhibition; and set both boundaries — how close is the same story,
 * how old is too old — from a sweep that is recomputed on every build by
 * demo/snapshot/build_explainer_facts.py.
 */
export function RetrievalModule({ facts }: Props) {
  const [tab, setTab] = useState("why");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "why" && <WhyWords facts={facts} />}
      {tab === "index" && <IndexPanel facts={facts} />}
      {tab === "cut" && <Cut facts={facts} />}
    </div>
  );
}

function num(x: number): string {
  return x.toLocaleString("en-US");
}

function pct(x: number): string {
  return `${(x * 100).toFixed(0)}%`;
}

/** A big number with a caption — the module's only "headline" element. */
function Big({
  value,
  label,
  tone = "accent",
}: {
  value: string;
  label: string;
  tone?: "accent" | "bad" | "good";
}) {
  const colors = {
    accent: "text-[var(--dk-accent)]",
    bad: "text-[var(--dk-bad)]",
    good: "text-[var(--dk-good)]",
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

/* ── 1. the keyword baseline was measured, and it lost ──────────── */

function WhyWords({ facts }: Props) {
  const r = facts?.retrieval;
  const k = r?.keyword;
  const ex = r?.example;
  const maxJ = Math.max(1, ...(k?.histogram.map((b) => b.n) ?? [1]));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[42%_1fr] gap-3">
      <Panel
        title={
          k
            ? `חיפוש מילולי מוצא ${k.found} מתוך ${k.total} הגרסאות`
            : "חיפוש מילולי מול אחזור סמנטי"
        }
        hint={k ? `J = חפיפת מילים בכותרת · חציון ${k.median}` : undefined}
      >
        {k && r ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              {k.zero_overlap} מהזוגות לא חולקים אף מילה. לכל מערכת יש בחירת
              מילים משלה, ולכן שתי כותרות על אותו אירוע יכולות לא להיפגש.
            </p>
            <div className="grid grid-cols-3 gap-2">
              <Big
                value={`${k.found}/${k.total}`}
                label="זוגות שהמילים מצאו"
                tone="bad"
              />
              <Big value={pct(k.recall)} label="שיעור אחזור מילולי" tone="bad" />
              <Big
                value={`${k.blind_events}/${r.events.total}`}
                label="אירועים שנעלמים לגמרי"
              />
            </div>
            <div className="flex flex-col gap-2">
              {k.histogram.map((b, i) => {
                // The top bucket starts at the keyword threshold, so it is the
                // only one a keyword search would have called a match.
                const found = i === k.histogram.length - 1;
                return (
                  <BarRow
                    key={b.label}
                    label={b.label}
                    n={b.n}
                    max={maxJ}
                    tone={found ? "good" : "bad"}
                    note={found ? `נמצא מ־${r.keyword_jaccard} ומעלה` : undefined}
                  />
                );
              })}
            </div>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              האחזור הסמנטי בנה {r.events.total} אירועים מ־{r.events.versions}{" "}
              גרסאות. בסיס מילולי היה משאיר {r.events.total - k.blind_events}.
            </p>
            <Caveat>
              {k.total} זוגות הגרסאות הוגדרו על ידי האחזור הסמנטי עצמו, ולכן הוא
              מוצא אותם בהגדרה. הטענה היחידה כאן: מבין הזוגות שהוא מצא, מילים
              היו משחזרות {pct(k.recall)}. אין ground truth ידני.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="אותו סיפור, אפס מילים משותפות"
        hint="cos — קרבה סמנטית · J — חפיפת מילים"
      >
        {ex && r ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3 rounded-xl border border-[var(--dk-accent)]/30 bg-[var(--dk-accent-dim)]/30 px-3 py-2">
              <Chip tone="accent">נקודת המוצא</Chip>
              <span className="text-[13.5px] text-[var(--dk-ink-3)]">
                {ex.seed.source_he}
              </span>
              <span className="min-w-0 flex-1 text-[16px] font-bold leading-snug">
                {ex.seed.title}
              </span>
            </div>

            {ex.neighbours.map((n, i) => (
              <NeighbourRow key={n.title} n={n} rank={i + 1} />
            ))}

            {ex.rejected && (
              <div className="flex items-stretch gap-2.5 rounded-xl border border-dashed border-[var(--dk-border)] px-3 py-2 opacity-60">
                <div
                  dir="ltr"
                  className="flex w-[76px] shrink-0 flex-col items-center justify-center"
                >
                  <span className="font-mono text-[17px] font-bold text-[var(--dk-ink-3)]">
                    {ex.rejected.cos}
                  </span>
                  <span className="text-[11.5px] text-[var(--dk-ink-3)]">cos</span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Chip tone="bad">
                      מתחת ל־{r.cluster_sim.toFixed(2)} — נעצר כאן
                    </Chip>
                    <span className="text-[13.5px] text-[var(--dk-ink-3)]">
                      {ex.rejected.source_he}
                    </span>
                  </div>
                  <div className="mt-0.5 truncate text-[14.5px] text-[var(--dk-ink-2)]">
                    {ex.rejected.title}
                  </div>
                </div>
              </div>
            )}

            <p className="mt-1 text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
              שתי שורות עברו את הסף וירדו: הערוץ שלהן כבר תרם גרסה. ההשוואה
              בהמשך רצה מול חציון האירוע, וערוץ שתורם שלוש גרסאות מתוך חמש נמדד
              מול עצמו.
            </p>
            <Caveat>
              השורה הרביעית עברה את הסף ואינה אותו סיפור. כלל גרסה־אחת־לערוץ
              הסיר אותה כאן במקרה, לא בגלל שהמערכת זיהתה טעות.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

function NeighbourRow({ n, rank }: { n: RetrievalNeighbour; rank: number }) {
  return (
    <div
      className={`flex items-stretch gap-2.5 rounded-xl border px-3 py-2 ${
        n.kept
          ? "border-[var(--dk-good)]/40 bg-[var(--dk-good)]/6"
          : "border-[var(--dk-border)] bg-[var(--dk-surface-2)]/40"
      }`}
    >
      <div className="flex w-[76px] shrink-0 flex-col items-center justify-center">
        <span
          dir="ltr"
          className="font-mono text-[17px] font-bold text-[var(--dk-accent)]"
        >
          {n.cos}
        </span>
        <span className="text-[11.5px] text-[var(--dk-ink-3)]">cos</span>
      </div>
      <div
        className={`flex w-[64px] shrink-0 flex-col items-center justify-center rounded-lg ${
          n.jaccard === 0 ? "bg-[var(--dk-bad)]/12" : ""
        }`}
      >
        <span
          dir="ltr"
          className={`font-mono text-[16px] font-bold ${
            n.jaccard === 0 ? "text-[var(--dk-bad)]" : "text-[var(--dk-ink-2)]"
          }`}
        >
          {n.jaccard.toFixed(3)}
        </span>
        <span className="text-[11.5px] text-[var(--dk-ink-3)]">J</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[12.5px] text-[var(--dk-ink-3)]" dir="ltr">
            #{rank}
          </span>
          <Chip tone={n.kept ? "good" : "warn"}>
            {n.kept ? `${n.source_he} · נכנס לאירוע` : `${n.source_he} · ירד`}
          </Chip>
          {!n.kept && (
            <span className="text-[13px] text-[var(--dk-ink-3)]">
              הערוץ כבר תרם גרסה
            </span>
          )}
        </div>
        <div className="mt-0.5 text-[15px] leading-snug">{n.title}</div>
        <div className="mt-0.5 text-[13px] text-[var(--dk-ink-3)]">
          מילים משותפות:{" "}
          {n.shared.length ? (
            n.shared.join(" · ")
          ) : (
            <b className="text-[var(--dk-bad)]">אין</b>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── 2. what the index costs, and what it exposed ───────────────── */

function IndexPanel({ facts }: Props) {
  const r = facts?.retrieval;
  const dup = r?.duplicates;
  const haaretz = r?.corpus.per_source.find((s) => s.source === "haaretz");

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[44%_1fr] gap-3">
      <Panel
        title="מטריצה בזיכרון, לא בסיס נתונים וקטורי"
        hint={r ? `${r.corpus.indexed} מתוך ${r.corpus.total} כתבות` : undefined}
      >
        {r ? (
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-2">
              <Big value={num(r.vectors)} label="ווקטורים" />
              <Big value={String(r.dims)} label="ממדים לווקטור" />
              <Big
                value={`${(r.bytes / 1024 / 1024).toFixed(2)} MB`}
                label="גודל האינדקס בזיכרון"
              />
              <Big
                value={`${r.query_ms.toFixed(3)} ms`}
                label="שאילתה מלאה"
                tone="good"
              />
              <div className="col-span-2 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-3 py-2 text-center">
                <code dir="ltr" className="font-mono text-[15px] text-[var(--dk-ink)]">
                  {r.model}
                </code>
                <div className="text-[13px] text-[var(--dk-ink-3)]">
                  רץ אופליין פעם אחת בזמן ההכנה — הקיוסק לא טוען מודל
                </div>
              </div>
            </div>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              שאילתה היא מכפלת מטריצה אחת, והתוצאה מדויקת. אינדקס משוער היה
              מחליף אותה בקירוב, ומוסיף תהליך שיכול ליפול מול קהל.
            </p>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              לכל וקטור נכנסים כותרת ו־{r.passage_lead_chars} תווים ראשונים.{" "}
              {r.corpus.too_short} כתבות מתחת ל־{r.min_text_chars} תווים לא נכנסו,
              כי אין להן פתיח לעגן עליו.
              {haaretz
                ? ` בהארץ זה ${haaretz.indexed} מתוך ${haaretz.articles}.`
                : ""}
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="הזהות היא של הכתובת, לא של התוכן"
        hint={dup ? `${dup.pairs} זוגות בקוסינוס ${dup.threshold}+` : undefined}
      >
        {dup && dup.examples.length ? (
          <div className="flex flex-col gap-2.5">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              <CodeRef path="article_id = sha256(canonical_url)" /> — אותה כתבה
              שמוגשת בשני נתיבים באתר היא שתי שורות במסד. האמבדינגים לא מאחדים
              אותן; הם הופכים אותן לגלויות. כלל גרסה אחת לכל ערוץ מונע מהן
              להכפיל אירוע.
            </p>
            {dup.examples.map((d) => (
              <div
                key={d.id_a}
                className="rounded-xl border border-[var(--dk-warn)]/35 bg-[var(--dk-warn)]/6 px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <Chip tone="warn">
                    <span dir="ltr" className="font-mono">
                      cos {d.cos}
                    </span>
                  </Chip>
                  <span className="truncate text-[14px] text-[var(--dk-ink-2)]">
                    {d.title}
                  </span>
                </div>
                <UrlDiff a={d.url_a} b={d.url_b} />
              </div>
            ))}
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

/* ── 3. two boundaries, both measured ───────────────────────────── */

function Cut({ facts }: Props) {
  const r = facts?.retrieval;
  const sim = r?.similarity;
  const slots = r?.slots;

  const chosen = r?.sweep.find((s) => s.chosen);
  const loose = r?.sweep.reduce((a, b) => (b.events > a.events ? b : a));
  const tight = r?.sweep.find((s) => chosen && s.threshold > chosen.threshold);
  const atCut = sim?.above.find((a) => a.threshold === r?.cluster_sim);
  const win = (h: number) => slots?.freshness.windows.find((w) => w.hours === h);

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <Panel
        title={
          chosen && loose
            ? `הסף ${chosen.threshold.toFixed(2)} ויתר על ${loose.events - chosen.events} אירועים`
            : "הסף שנבחר"
        }
        hint={sim ? `חציון קוסינוס בין שתי כתבות: ${sim.median}` : undefined}
      >
        {r && sim && chosen && loose && tight ? (
          <div className="flex flex-col gap-3">
            <table className="w-full text-[15px]">
              <thead>
                <tr className="text-[13.5px] text-[var(--dk-ink-3)]">
                  <th className="pb-1.5 text-right font-normal">סף</th>
                  <th className="pb-1.5 text-right font-normal">אירועים</th>
                  <th className="pb-1.5 text-right font-normal">גרסאות</th>
                  <th className="pb-1.5 text-right font-normal">עם 3+ ערוצים</th>
                </tr>
              </thead>
              <tbody>
                {r.sweep.map((row) => (
                  <tr
                    key={row.threshold}
                    className={
                      row.chosen
                        ? "bg-[var(--dk-accent-dim)]/50 text-[var(--dk-accent)]"
                        : "text-[var(--dk-ink-2)]"
                    }
                  >
                    <td dir="ltr" className="py-1 text-right font-mono font-bold">
                      {row.threshold.toFixed(2)}
                      {row.chosen ? " ←" : ""}
                    </td>
                    <td dir="ltr" className="py-1 text-right font-mono">
                      {row.events}
                    </td>
                    <td dir="ltr" className="py-1 text-right font-mono">
                      {row.versions}
                    </td>
                    <td
                      dir="ltr"
                      className={`py-1 text-right font-mono ${
                        row.three_plus === 0 && !row.chosen
                          ? "text-[var(--dk-bad)]"
                          : ""
                      }`}
                    >
                      {row.three_plus}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              {atCut?.pct}% מ־{num(sim.pairs)} הזוגות עוברים את הסף. ציון קוסינוס
              נמדד מול ההתפלגות, לא לבדו.
            </p>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              {loose.threshold} מוסיף {loose.events - chosen.events} אירועים,
              והאשכולות שם כבר סיפור מתגלגל שלם. {tight.threshold} מאפס את
              ההשוואה: {tight.three_plus} אירועים עם שלושה ערוצים.
            </p>
            <Caveat>
              הגבול בין אירוע לסיפור מתגלגל נקבע בעין, לא במדד. האשכול גם חמדני
              ותלוי סדר — דטרמיניסטי, אבל סדר אחר היה נותן חלוקה אחרת.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="פינוי לפי גיל, לא לפי שימוש"
        hint={
          slots
            ? `חציון אירוע ${slots.freshness.p50_hours}ש׳ · p75 ${slots.freshness.p75_hours} · p90 ${slots.freshness.p90_hours}`
            : undefined
        }
      >
        {slots ? (
          <div className="flex flex-col gap-3">
            <table className="w-full text-[15px]">
              <thead>
                <tr className="text-[13px] text-[var(--dk-ink-3)]">
                  <th className="pb-1.5 text-right font-normal">
                    מדיניות פינוי
                  </th>
                  {slots.rows.map((row) => (
                    <th
                      key={row.k}
                      dir="ltr"
                      className="pb-1.5 text-right font-mono font-normal"
                    >
                      {row.k}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {slots.policies.map((p) => (
                  <tr key={p.key} className="text-[var(--dk-ink-2)]">
                    <td className="py-1 pl-2">
                      <span dir="ltr" className="font-mono text-[13px]">
                        {p.key.toUpperCase()}
                      </span>
                      <span className="mr-2 text-[13.5px]">{p.label_he}</span>
                      <div className="text-[12px] text-[var(--dk-ink-3)]">
                        {p.note_he}
                      </div>
                    </td>
                    {slots.rows.map((row) => (
                      <td
                        key={row.k}
                        dir="ltr"
                        className={`py-1 text-right font-mono ${
                          row[p.key] === row.total
                            ? "text-[var(--dk-good)]"
                            : ""
                        }`}
                      >
                        {row[p.key]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[14px] text-[var(--dk-ink-3)]">
              זוגות גרסאות שהאינדקס עדיין מוצא, מתוך {slots.rows[0]?.total}, לפי
              מספר הסלוטים שהוא מחזיק.
            </p>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              FIFO ו־LRU יצאו זהים בכל K: בזרם חדשות פריט נשאל פעם אחת ולא
              נוגעים בו שוב. LFU גרוע יותר, כי הוא מקבע כתבות ישנות ומרעיב
              טריות.
            </p>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              בקצב {slots.freshness.per_day} כתבות ליום, חלון של 24 שעות הוא{" "}
              {win(24)?.slots} סלוטים ומכסה {pct(win(24)?.covered ?? 0)}{" "}
              מהאירועים. 48 שעות מכסות {pct(win(48)?.covered ?? 0)}.
            </p>
            <Caveat>
              האינדקס כאן לא מפנה כלום: {slots.current.resident} וקטורים על{" "}
              {slots.freshness.corpus_days} ימי קורפוס. הטבלה מודדת מה היה קורה
              בחלון, ושום דבר בקוד לא מונע אשכול של שתי כתבות בהפרש שבועיים.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

/**
 * Two URLs with only the part that differs highlighted.
 *
 * These paths are long and nearly identical, and a truncated pair proves
 * nothing — the whole claim is *which* segment differs, so that segment is
 * the one thing that must survive on a wall screen.
 */
function UrlDiff({ a, b }: { a: string; b: string }) {
  let head = 0;
  while (head < a.length && head < b.length && a[head] === b[head]) head += 1;
  let tail = 0;
  while (
    tail < a.length - head &&
    tail < b.length - head &&
    a[a.length - 1 - tail] === b[b.length - 1 - tail]
  )
    tail += 1;

  const render = (url: string) => (
    <span className="break-all">
      <span className="opacity-55">{url.slice(0, head)}</span>
      <mark className="rounded bg-[var(--dk-warn)]/25 px-0.5 text-[var(--dk-warn)]">
        {url.slice(head, url.length - tail) || "∅"}
      </mark>
      <span className="opacity-55">{url.slice(url.length - tail)}</span>
    </span>
  );

  return (
    <div
      dir="ltr"
      className="mt-1 flex flex-col gap-0.5 font-mono text-[12px] text-[var(--dk-ink-3)]"
    >
      {render(a)}
      {render(b)}
    </div>
  );
}

/* ── shared ────────────────────────────────────────────── */

function Missing() {
  return (
    <p className="text-[15px] text-[var(--dk-ink-3)]">
      אין קובץ מדידות — הדיאגרמות מוצגות בלי המספרים.
    </p>
  );
}
