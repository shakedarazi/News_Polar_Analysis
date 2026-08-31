"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import { Caveat, Chip, CodeRef, Panel, SubNav, type TabDef } from "./kit";

const TABS: TabDef[] = [
  { id: "loss", label_he: "מה המאמת מוחק" },
  { id: "gain", label_he: "מה הלולאה מחזירה" },
  { id: "guards", label_he: "מה מונע ממנה לרמות" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the repair loop — the only place in this system where a model gets
 * a second try.
 *
 * The argument is not "we added a loop". It is that a deterministic verifier
 * which only deletes is also a loss function: 33 of 144 evidence quotes were
 * thrown out, and each one is a claim on screen with nothing under it. The
 * loop is the recovery path, and every rule in it exists because the obvious
 * version of that rule was wrong — including the guard that was added after
 * the first run silently destroyed 13 good citations.
 */
export function RepairModule({ facts }: Props) {
  const [tab, setTab] = useState("loss");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "loss" && <Loss facts={facts} />}
      {tab === "gain" && <Gain facts={facts} />}
      {tab === "guards" && <Guards facts={facts} />}
    </div>
  );
}

/* ── formatting ─────────────────────────────────────────────────── */

function num(x: number): string {
  return x.toLocaleString("en-US");
}

function pct(x: number, digits = 0): string {
  return `${(x * 100).toFixed(digits)}%`;
}

function usd(x: number): string {
  if (x === 0) return "$0";
  if (x >= 1) return `$${x.toFixed(2)}`;
  const digits = x >= 0.001 ? 4 : 6;
  return `$${x.toFixed(digits).replace(/0+$/, "").replace(/\.$/, "")}`;
}

function Big({
  value,
  label,
  tone = "accent",
}: {
  value: string;
  label: string;
  tone?: "accent" | "bad" | "good" | "warn" | "muted";
}) {
  const colors = {
    accent: "text-[var(--dk-accent)]",
    bad: "text-[var(--dk-bad)]",
    good: "text-[var(--dk-good)]",
    warn: "text-[var(--dk-warn)]",
    muted: "text-[var(--dk-ink-2)]",
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

function Missing() {
  return (
    <p className="text-[15px] text-[var(--dk-ink-3)]">
      אין קובץ מדידות — הדיאגרמות מוצגות בלי המספרים.
    </p>
  );
}

/* ── 1. the loss the verifier creates ───────────────────────────── */

function Loss({ facts }: Props) {
  const r = facts?.repair;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[42%_1fr] gap-3">
      <Panel title="מאמת שרק מוחק הוא גם פונקציית הפסד">
        {r ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              {r.verifier.quotes_rejected} מתוך {r.verifier.quotes_total}{" "}
              הציטוטים לא נמצאו בטקסט ונמחקו. כל מחיקה כזאת היא משפט על המסך
              בלי ראיה מתחתיו.
            </p>
            <div className="grid grid-cols-2 gap-2">
              <Big
                value={pct(
                  r.verifier.quotes_rejected / r.verifier.quotes_total,
                )}
                label="מהציטוטים נמחקו"
                tone="bad"
              />
              <Big
                value={`${r.verifier.terms_rejected}/${r.verifier.terms_total}`}
                label="מילים טעונות שנמחקו"
                tone="muted"
              />
            </div>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              המחיקה נכונה — ציטוט שהקהל לא ימצא בטקסט הוא הדבר היחיד שיפיל את
              כל ההצגה. אבל היא לא הסוף האפשרי היחיד.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="שתי דרכים לכתוב ציטוט שנפסל"
        hint="דוגמה אמיתית מהקורפוס"
      >
        {r?.example ? (
          <div className="flex flex-col gap-2.5">
            <div className="text-[13.5px] text-[var(--dk-ink-3)]">
              {r.example.headline}
            </div>
            <div className="rounded-xl border border-[var(--dk-bad)]/45 bg-[var(--dk-bad)]/8 p-3">
              <div className="mb-1 flex items-center gap-2">
                <Chip tone="bad">נפסל</Chip>
                <span className="text-[13px] text-[var(--dk-ink-3)]">
                  {r.example.source}
                </span>
              </div>
              <p className="text-[15px] leading-snug">״{r.example.before}״</p>
            </div>
            <div className="rounded-xl border border-[var(--dk-good)]/45 bg-[var(--dk-good)]/8 p-3">
              <div className="mb-1 flex items-center gap-2">
                <Chip tone="good">עבר</Chip>
                <span className="text-[13px] text-[var(--dk-ink-3)]">
                  אחרי סבב אחד
                </span>
              </div>
              <p className="text-[15px] leading-snug">״{r.example.after}״</p>
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              המודל קיצר את המשפט וסגר אותו בנקודה. הנקודה לא הייתה בטקסט, ולכן
              ההשוואה מילה במילה נכשלה. הציטוט המלא היה שם כל הזמן.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

/* ── 2. what the loop won back ──────────────────────────────────── */

function Gain({ facts }: Props) {
  const r = facts?.repair;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <Panel title="14 ציטוטים חזרו, 15 קיבלו null בכנות">
        {r ? (
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-3 gap-2">
              <Big value={num(r.loop.regrounded)} label="ציטוטים שהוחזרו" tone="good" />
              <Big value={num(r.loop.nulled)} label="הודה שאין ציטוט" tone="muted" />
              <Big value={num(r.loop.destroyed)} label="ציטוטים תקינים שנהרסו" tone="good" />
            </div>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              שתי התוצאות האלה נראות זהות בספירת הפרות, והן לא אותו דבר. רק
              הראשונה היא החזרה. השנייה היא מודל שמסרב להמציא.
            </p>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              {r.loop.violations_before} הפרות נכנסו,{" "}
              {r.loop.violations_after} נשארו. על שלושת הסיפורים שעל הקיר זה{" "}
              {r.stage.recovered} ציטוטים שחזרו למסך.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <div className="flex min-h-0 flex-col gap-3">
        <Panel
          title="ניסיון שני תיקן אפס, ולכן התקרה היא אחד"
          hint="נמדד ב־2, נקבע ל־1"
        >
          {r ? (
            <div className="flex flex-col gap-2">
              {r.attempts.map((a) => (
                <div
                  key={a.n}
                  className="flex items-center gap-3 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-3 py-2"
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[var(--dk-border)] font-mono text-[13px]">
                    {a.n}
                  </span>
                  <span
                    dir="ltr"
                    className="w-[92px] shrink-0 text-left font-mono text-[14px] text-[var(--dk-ink-2)]"
                  >
                    {a.calls} calls
                  </span>
                  <span className="flex-1 text-[14.5px] text-[var(--dk-ink-2)]">
                    {a.detail_he}
                  </span>
                  <Chip tone={a.accepted ? "good" : "bad"}>
                    {a.accepted ? `+${a.accepted}` : "0"}
                  </Chip>
                </div>
              ))}
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                התקרה לא נוחשה. הלולאה רצה על{" "}
                {r.constants.max_attempts_measured} כדי לבדוק אם הניסיון השני
                שווה משהו. הוא לא, ולכן הקוד רץ על{" "}
                {r.constants.max_attempts}.
              </p>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="התיקון עלה שביעית משכבת המודל">
          {r ? (
            <div className="flex flex-col gap-2.5">
              <div className="grid grid-cols-3 gap-2">
                <Big value={usd(r.bill.layer_usd)} label="שכבת המודל" tone="muted" />
                <Big value={usd(r.bill.usd)} label="הלולאה" tone="warn" />
                <Big value={pct(r.bill.share_of_layer, 1)} label="תוספת" tone="accent" />
              </div>
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                {r.loop.calls} קריאות על {r.loop.entered} פריטים,{" "}
                {usd(r.bill.per_item_usd)} לפריט. סך הכל{" "}
                {usd(r.bill.total_usd)}.
              </p>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>
    </div>
  );
}

/* ── 3. the rules that keep it honest ───────────────────────────── */

function Guards({ facts }: Props) {
  const r = facts?.repair;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[52%_1fr] gap-3">
      <Panel title="ארבעה כללים, כל אחד בגלל כשל">
        {r ? (
          <ol className="flex flex-col gap-2">
            {r.guards.map((g, i) => (
              <li
                key={g.key}
                className="flex items-start gap-3 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/40 px-3 py-2"
              >
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--dk-border)] font-mono text-[13px] text-[var(--dk-ink-3)]">
                  {i + 1}
                </span>
                <div className="flex-1">
                  <div className="text-[15.5px] font-bold">{g.title_he}</div>
                  <p className="mt-0.5 text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
                    {g.detail_he}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <Missing />
        )}
      </Panel>

      <div className="flex min-h-0 flex-col gap-3">
        <Panel title="הכלל השלישי נוסף אחרי שהלולאה הרסה 13 ציטוטים">
          {r ? (
            <div className="flex flex-col gap-2.5">
              <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
                הגרסה הראשונה קיבלה כל תיקון שהוריד הפרות. המודל החזיר null גם
                לציטוטים שכבר עברו, ומחיקה של ציטוט תקין לא סופרת כהפרה.
              </p>
              <div className="grid grid-cols-2 gap-2">
                <Big
                  value={num(r.regression.destroyed_before_guard)}
                  label="ציטוטים תקינים שנמחקו, לפני הכלל"
                  tone="bad"
                />
                <Big
                  value={num(r.regression.destroyed_now)}
                  label="אחרי הכלל"
                  tone="good"
                />
              </div>
              <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
                מאז התיקון נוגע רק במקורות שהמאמת פסל, והוא מתקבל רק אם מספר
                הציטוטים המאומתים לא ירד.
              </p>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="בזמן התצוגה הלולאה לא קוראת למודל">
          {r ? (
            <div className="flex flex-col gap-2.5">
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                כל תיקון נשמר בקובץ, יחד עם כל ניסיון שנדחה. המסך מנגן את
                הקובץ.
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <CodeRef path="demo/data/repair_cache.json" />
                <CodeRef path="demo/data/repair_log.json" />
              </div>
              <Caveat>
                חסר קובץ או שאין רשת — הפריט חוזר למצב שלפני התיקון: ציטוט ריק,
                בדיוק כמו שהמאמת השאיר אותו. אף פעם לא ציטוט שגוי.
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
