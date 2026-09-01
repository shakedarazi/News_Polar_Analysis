"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import { BarRow, Chip, Ladder, Panel, Stage, SubNav, type TabDef } from "./kit";

const TABS: TabDef[] = [
  { id: "why", label_he: "למה יש ניסיון שני" },
  { id: "rules", label_he: "מה היא מחזירה, ומה עוצר אותה" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the repair loop — the only place in this system where a model gets
 * a second try.
 *
 * Rewritten to demo/WRITING.md, from three tabs to two. Each of the four
 * panels now carries one decision, the alternative by name, and what it buys:
 * retry instead of accepting the deletion; cap at one attempt because the
 * second fixed nothing; accept a patch only when the verified count holds.
 *
 * The argument survives the cut. A deterministic verifier that only deletes is
 * also a loss function — 33 of 144 evidence quotes went, and each one is a
 * claim on screen with nothing under it. What changed is that the acceptance
 * rule is now stated as the choice it is, measured against the obvious
 * alternative (accept anything that lowers the violation count, which deletes
 * 13 good citations), rather than narrated as something that went wrong.
 *
 * Dropped on purpose: the four-guard list and the replay panel. Both described
 * mechanism rather than a decision, and the two guards that carry an argument
 * are now sentences in the panel that needs them.
 */
export function RepairModule({ facts }: Props) {
  const [tab, setTab] = useState("why");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "why" && <Loss facts={facts} />}
      {tab === "rules" && <Rules facts={facts} />}
    </div>
  );
}

/* ── formatting ─────────────────────────────────────────────────── */

function num(x: number): string {
  return x.toLocaleString("en-US");
}

function pct(x: number): string {
  return `${Math.round(x * 100)}%`;
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
    <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-2.5 py-3 text-center">
      <div className={`text-[36px] font-black leading-[1.1] ${colors[tone]}`} dir="ltr">
        {value}
      </div>
      <div className="mt-1.5 text-[15px] leading-snug text-[var(--dk-ink-2)]">
        {label}
      </div>
    </div>
  );
}

function Missing() {
  return (
    <p className="text-[16px] text-[var(--dk-ink-3)]">
      אין קובץ מדידות — הדיאגרמות מוצגות בלי המספרים.
    </p>
  );
}

/* ── 1. what the verifier costs, and one rejection up close ─────── */

function Loss({ facts }: Props) {
  const r = facts?.repair;

  return (
    <Stage cols="grid-cols-[56%_1fr]">
      <Panel
        title={
          r
            ? `מאמת שרק מוחק הפיל ${r.verifier.quotes_rejected} מתוך ${r.verifier.quotes_total} ציטוטי הראיה`
            : "מה המאמת מוחק"
        }
      >
        {r ? (
          <div className="flex flex-col gap-4">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              לכל טענה שהמודל מחלץ הוא מצרף ציטוט ראיה — משפט מהכתבה שתומך בה.
              קוד דטרמיניסטי מחפש את המשפט הזה מילה במילה באותם{" "}
              {r.constants.lead_chars} תווים שהמודל קרא, ומוחק כל ציטוט שאינו שם.
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              <Big
                value={pct(r.verifier.quotes_rejected / r.verifier.quotes_total)}
                label="מציטוטי הראיה נמחקו"
                tone="bad"
              />
              <Big
                value={pct(r.verifier.terms_rejected / r.verifier.terms_total)}
                label="מהמילים הטעונות נמחקו"
                tone="good"
              />
            </div>
            {/* The two rates side by side are the panel's second claim: the
                same rule barely touches one output and guts the other. A
                single word is easy to find in the text; a whole sentence has
                to survive every comma the model moved. */}
            <div className="flex flex-col gap-2.5">
              <BarRow
                label="quotes"
                n={r.verifier.quotes_rejected}
                max={r.verifier.quotes_total}
                tone="bad"
                note={`מתוך ${r.verifier.quotes_total}`}
              />
              <BarRow
                label="terms"
                n={r.verifier.terms_rejected}
                max={r.verifier.terms_total}
                tone="good"
                note={`מתוך ${r.verifier.terms_total}`}
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              ‏0% = הכל נמצא בטקסט · 100% = שום דבר לא. אותו כלל בדיוק חל על
              שניהם, ומילה בודדת קל למצוא הרבה יותר ממשפט שלם.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              המחיקה נכונה, והיא גם עולה: טענה שנשארת בלי ציטוט יורדת מהמסך.
              החלופה למחיקה כסוף הדרך היא ניסיון שני, מוגבל למה שנפסל.
            </p>
            {/* The tier, which is the module's whole thesis: the model is
                asked twice and trusted zero times, and the same deterministic
                check stands at both exits. Shown as a ladder because the
                argument is the order — a retry before a verifier is a way to
                launder a bad answer, and after one it is a recovery path. */}
            <Ladder
              rungs={[
                {
                  label: "חילוץ",
                  detail: "מודל בתשלום מוציא טענה וציטוט ראיה",
                  tone: "accent",
                },
                {
                  label: "אימות",
                  detail: "קוד משווה מילה במילה ומוחק מה שאינו בטקסט",
                  tone: "good",
                  fallsThroughWhen: "רק מה שנמחק ממשיך הלאה",
                },
                {
                  label: "תיקון",
                  detail: `אותו מודל, ניסיון ${r.constants.max_attempts}, ורק על המקורות שנפסלו`,
                  tone: "accent",
                },
                {
                  label: "אימות שוב",
                  detail: "אותה בדיקה בדיוק — התיקון אינו מאשר את עצמו",
                  tone: "good",
                },
              ]}
            />
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="ההבדל בין ציטוט שנפסל לציטוט שעבר הוא סימן פיסוק" hint="מקרה מהקורפוס">
        {r?.example ? (
          <div className="flex flex-col gap-3">
            <div className="text-[15px] text-[var(--dk-ink-3)]">
              {r.example.headline}
            </div>
            <div className="rounded-xl border border-[var(--dk-bad)]/45 bg-[var(--dk-bad)]/8 p-3">
              <div className="mb-1.5 flex items-center gap-2">
                <Chip tone="bad">נפסל</Chip>
                <span className="text-[15px] text-[var(--dk-ink-3)]">
                  {r.example.source}
                </span>
              </div>
              <p className="text-[17px] leading-snug">״{r.example.before}״</p>
            </div>
            <div className="rounded-xl border border-[var(--dk-good)]/45 bg-[var(--dk-good)]/8 p-3">
              <div className="mb-1.5 flex items-center gap-2">
                <Chip tone="good">עבר</Chip>
                <span className="text-[15px] text-[var(--dk-ink-3)]">
                  אחרי סבב אחד
                </span>
              </div>
              <p className="text-[17px] leading-snug">״{r.example.after}״</p>
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              המודל קיצר את המשפט וסגר אותו בנקודה שלא הייתה בטקסט. הציטוט
              המלא היה שם כל הזמן — וזה מה שהסבב השני מחזיר.
            </p>
            {/* The decision the example is here to support. Without it the
                panel is an anecdote about one quote; with it the anecdote is
                the price of a check the audience can verify by eye. */}
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              המאמת משווה מחרוזות, לא משמעות. החלופה — מודל שני שמחליט אם
              הציטוט ״בערך״ מופיע בטקסט — הייתה מצילה את הפסילה הזאת, ומחליפה
              בדיקה שכל אחד יכול לאמת בעיניו בשיקול דעת של מודל נוסף.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

/* ── 2. the gain, the ceiling, and the acceptance rule ───────────── */

function Rules({ facts }: Props) {
  const r = facts?.repair;
  const second = r?.attempts.find((a) => a.n === 2);

  return (
    <Stage cols="grid-cols-[50%_1fr]">
      <Panel
        title={
          r
            ? `${r.loop.fixed_fully} מתוך ${r.loop.entered} הפריטים תוקנו בניסיון אחד`
            : "מה הלולאה מחזירה"
        }
      >
        {r ? (
          <div className="flex flex-col gap-4">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              פריט הוא ציטוט שהמאמת פסל. הלולאה מחזירה אותו למודל עם הטקסט
              המקורי ועם ההנחיה להעתיק ממנו — ולא לנסח מחדש.
            </p>
            <div className="flex flex-col gap-2.5">
              <BarRow
                label="לפני"
                n={r.loop.violations_before}
                max={r.loop.violations_before}
                tone="bad"
                note="הפרות שנכנסו"
              />
              <BarRow
                label="אחרי"
                n={r.loop.violations_after}
                max={r.loop.violations_before}
                tone="good"
                note="הפרות שנשארו"
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              הפרה = ציטוט שהמודל החזיר ושאינו מופיע בטקסט שהוא קרא.
            </p>
            <div className="grid grid-cols-3 gap-2.5">
              <Big value={num(r.loop.regrounded)} label="ציטוטים שהוחזרו" tone="good" />
              <Big value={num(r.loop.nulled)} label="הודה שאין ציטוט" tone="muted" />
              <Big value={num(r.loop.destroyed)} label="ציטוטים תקינים שנהרסו" tone="good" />
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              שתי התוצאות הראשונות נראות זהות בספירת ההפרות, ורק אחת מהן היא
              רווח. השנייה היא מודל שמסרב להמציא, וזו תשובה טובה.
            </p>
            {/* Both attempt constants are read from facts rather than written
                into the sentence: the claim is that the ceiling was measured,
                and a hard-coded "1" here would go on making that claim after
                the cap moved. */}
            {second && (
              <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
                התקרה נמדדה ולא נוחשה: הלולאה רצה על{" "}
                {r.constants.max_attempts_measured} ניסיונות, השני תיקן{" "}
                {second.accepted} מתוך {second.calls}, ולכן הקוד רץ על{" "}
                {r.constants.max_attempts}. {r.loop.calls} קריאות בסך הכל —{" "}
                {pct(r.bill.share_of_layer)} מחשבון שכבת המודל.
              </p>
            )}
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          r
            ? `קבלה לפי ספירת הפרות בלבד מוחקת ${r.regression.destroyed_before_guard} ציטוטים תקינים`
            : "מה עוצר את הלולאה"
        }
      >
        {r ? (
          <div className="flex flex-col gap-4">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              תשובה שכולה null היא תשובה בלי אף הפרה. לכן ״פחות הפרות״ אינו
              תנאי הקבלה: תיקון מתקבל רק אם הוא נוגע במקורות שהמאמת פסל, ורק
              אם מספר הציטוטים המאומתים אחריו אינו נמוך מלפניו.
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              <Big
                value={num(r.regression.destroyed_before_guard)}
                label="נמחקים בתנאי ״פחות הפרות״"
                tone="bad"
              />
              <Big
                value={num(r.regression.destroyed_now)}
                label="נמחקים בתנאי שנבחר"
                tone="good"
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              ‏0 = שום ציטוט מאומת לא אבד · 13 = מספר הציטוטים שכלל הקבלה
              הפשוט מוחק על אותם נתונים.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              אותו מאמת בודק גם את התיקון, על אותו חלון של{" "}
              {r.constants.contrast_lead_chars} תווים. המודל לא מאשר את עצמו,
              וחלון רחב יותר היה מכשיר ציטוט מטקסט שהקריאה הראשונה לא ראתה.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              וכשהתיקון נכשל או שאין רשת, הציטוט נשאר ריק — בדיוק כפי שהמאמת
              השאיר אותו. הלולאה יכולה להחזיר ראיה, ולעולם לא להחליף אותה
              בראיה שגויה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}
