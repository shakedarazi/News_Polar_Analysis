"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import { Chip, CodeRef, Node, Panel, Stage, SubNav, type TabDef } from "./kit";

const TABS: TabDef[] = [
  { id: "why", label_he: "למה משלמים על מודל" },
  { id: "check", label_he: "איך יודעים שלא המציא" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the one layer that is not deterministic, and the deterministic
 * check bolted to its output.
 *
 * Two tabs. First why a paid model is the right tier here at all — framing is
 * the only question in this system without a computable answer, and the panel
 * shows exactly what was asked and what came back, so "framing" stops being a
 * word and becomes five fields. Then the guard rails: valid JSON buys parsing
 * and not truth, so every phrase is checked for literal presence in the same
 * window the model read, and the verifier itself is audited — most of what it
 * rejects is punctuation, and the rule stayed strict anyway.
 *
 * Both errors fall the same direction: less on the wall, never more. That is
 * the whole argument of this module and every number here serves it.
 */
export function FramingModule({ facts }: Props) {
  const [tab, setTab] = useState("why");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "why" && <WhyModel facts={facts} />}
      {tab === "check" && <Check facts={facts} />}
    </div>
  );
}

/** The five keys the prompt asks for, in the order the extractor lists them. */
const FIELD: Record<string, { label_he: string; why_he: string }> = {
  actor: {
    label_he: "מי מוצג כמבצע",
    why_he: "אותה עובדה, עם נושא מפורש או בלעדיו",
  },
  responsibility: {
    label_he: "למי מיוחסת האחריות",
    why_he: "מי מוצג כאשם במצב — לרוב לא מי שביצע",
  },
  loaded_terms: {
    label_he: "מילים טעונות בכותרת",
    why_he: "תארים שיפוטיים, ולא תיאור",
  },
  voice: {
    label_he: "קול פעיל או סביל",
    why_he: "״נהרגו״ מול ״כוחותינו הרגו״ — אחריות אחרת",
  },
  lead_perspective: {
    label_he: "מנקודת מבט של מי נפתח",
    why_he: "מי מקבל את המשפט הראשון",
  },
};

/* ── 1. the one question code cannot answer ─────────────────────── */

function WhyModel({ facts }: Props) {
  const f = facts?.framing;
  const d = f?.distribution;
  const passive = d?.voice.find((v) => v.label === "passive")?.n ?? 0;
  const zeroTerms = d?.terms_per_article.find((t) => t.terms === 0)?.n ?? 0;

  return (
    <Stage cols="grid-cols-[45%_1fr]">
      <Panel title="שאלה שאין לה תשובה מחושבת — ורק עליה משלמים">
        {f ? (
          <div className="flex flex-col gap-4">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              מסגור הוא איך אותה עובדה מוצגת: מי מופיע כמי שעשה, מי מואשם, ואיזו
              מילה נבחרה. אין נוסחה שמחשבת את זה ואין מילון שמגיע לשם, ולכן זו
              הנקודה היחידה במערכת שבה משלמים למודל.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              הסדר קבוע ולא משתנה: קודם קוד רגיל, ורק מה שנשאר ממשיך הלאה.{" "}
              {f.cache.framing} כותרות הגיעו למודל אחרי שכל שאלה עם תשובה
              מחושבת כבר נענתה בלעדיו.
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              <Node title={f.model} mono sub="הדגם שמחלץ את המסגור" />
              <Node
                title={`temperature = ${f.temperature}`}
                mono
                sub="אותה כותרת, כמעט תמיד אותה תשובה — כמה שאפשר לקרב מודל לדטרמיניזם"
              />
              <Node
                title={`${f.lead_chars} תווים`}
                sub="הכותרת והפתיח — כל ההקשר שהמודל מקבל, ולכן גם כל מה שיאומת מולו"
              />
              <Node
                title={`max_tokens = ${f.max_tokens.framing}`}
                mono
                sub="תשובה קצרה ומובנית, בלי מקום לנאום שאיש לא יקרא"
              />
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              ‏{f.cache.contrast} קריאות נוספות משוות עד {f.contrast_versions}{" "}
              גרסאות של אותו אירוע זו לזו. זו שאלה שאי אפשר לענות עליה מכתבה
              אחת — צריך קודם למצוא את האחיות שלה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="מה בדיוק ביקשנו, ומה חזר" hint="חמישה שדות, אותם חמישה בכל כותרת">
        {f && d ? (
          <div className="flex flex-col gap-3.5">
            <div className="flex flex-col gap-1.5">
              {f.keys.map((key) => (
                <div
                  key={key}
                  className="flex items-baseline gap-2.5 rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-3 py-2"
                >
                  <span className="w-[168px] shrink-0 text-[16px] font-semibold">
                    {FIELD[key]?.label_he ?? key}
                  </span>
                  <span className="flex-1 text-[14.5px] leading-snug text-[var(--dk-ink-3)]">
                    {FIELD[key]?.why_he}
                  </span>
                  <code
                    dir="ltr"
                    className="shrink-0 font-mono text-[12.5px] text-[var(--dk-ink-3)]"
                  >
                    {key}
                  </code>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-2.5 text-center">
              <Stat n={passive} of={d.total} label="כותרות בקול סביל" />
              <Stat n={d.actor_null} of={d.total} label="בלי מבצע מזוהה" />
              <Stat
                n={d.responsibility_null}
                of={d.total}
                label="בלי ייחוס אחריות"
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              המספר העליון הוא כמה כותרות ענו כך, מתוך {d.total} שנותחו.
            </p>

            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              רק {passive} כותרות בקול סביל, והן בדיוק אותן {passive} שבהן אין
              מבצע מזוהה — סביל פירושו שאין מי שעשה. זה ממצא על העיתונות
              הישראלית שנמדד כאן ולא הנחה שהתחלנו ממנה, ובסנאפשוט הזה המשתנה
              כמעט לא מפריד בין ערוצים.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              ‏{zeroTerms} כותרות חזרו בלי אף מילה טעונה. שדה ריק הוא תשובה ולא
              כישלון — כותרת ניטרלית היא בדיוק מה שרצינו למדוד.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

function Stat({ n, of, label }: { n: number; of: number; label: string }) {
  return (
    <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-2 py-2.5">
      <div
        className="text-[30px] font-black leading-none text-[var(--dk-accent)]"
        dir="ltr"
      >
        {n}
        <span className="text-[16px] font-normal text-[var(--dk-ink-3)]">
          /{of}
        </span>
      </div>
      <div className="mt-1 text-[13.5px] leading-snug text-[var(--dk-ink-2)]">
        {label}
      </div>
    </div>
  );
}

/* ── 2. the guard rails, and the audit of the guard rails ───────── */

const REASONS: Record<
  string,
  { label_he: string; note_he: string; tone: "bad" | "warn" | "good" }
> = {
  paraphrase: {
    label_he: "ניסוח מחדש או השמטה",
    note_he: "המודל חיבר משפטים או שינה מילים — פסילה נכונה",
    tone: "good",
  },
  punct: {
    label_he: "הבדל בפיסוק בלבד",
    note_he: "מילה במילה, למעט פיסוק שהמודל הוסיף — לרוב נקודה בסוף",
    tone: "bad",
  },
  wrapper: {
    label_he: "תווית שהמודל הוסיף",
    note_he: "הציטוט נכון אבל עטוף ב״כותרת:״ — פסילה מיותרת",
    tone: "warn",
  },
};

function Check({ facts }: Props) {
  const f = facts?.framing;
  const v = f?.verifier;
  const a = f?.acronyms;
  const ex = f?.term_example;
  const maxReason = Math.max(1, ...(v?.quote_reasons.map((r) => r.n) ?? [1]));
  const punct = v?.quote_reasons.find((r) => r.kind === "punct")?.n ?? 0;
  const bad = v?.quote_reasons.find((r) => r.kind === "paraphrase")?.n ?? 0;

  return (
    <Stage cols="grid-cols-[47%_1fr]">
      <Panel title="ביטוי שלא נמצא בטקסט כלשונו לא עולה למסך">
        {f && v ? (
          <div className="flex flex-col gap-3.5">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              המודל מחזיר תשובה בפורמט קבוע, וזה קונה פענוח — לא אמת. לכן כל
              ביטוי שהוא מחזיר נבדק מול הטקסט: השוואת מחרוזות פשוטה, לא דעה
              שנייה של מודל אחר.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              הבדיקה קוראת בדיוק את אותם {f.lead_chars} תווים שהמודל קיבל,
              מאותו קבוע יחיד. חלון רחב יותר היה מאשר ביטוי שהמודל מעולם לא
              ראה — אימות שמאשר את עצמו.
            </p>

            <div className="flex flex-col gap-2.5">
              <RateRow
                label="מילים טעונות"
                rejected={v.terms_rejected}
                total={v.terms_total}
              />
              <RateRow
                label="שמות מבצע"
                rejected={v.actors_rejected}
                total={v.actors_total}
              />
              <RateRow
                label="ציטוטי ראיה"
                rejected={v.quotes_rejected}
                total={v.quotes_total}
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              כל פס הוא סוג ביטוי אחד. האדום הוא החלק שנפסל, מתוך כל מה שהמודל
              החזיר מאותו סוג.
            </p>

            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              ‏{v.quotes_rejected} מתוך {v.quotes_total} ציטוטי הראיה לא נמצאו
              כלשונם, ושיעור כזה נשמע כמו מודל שממציא. פירקנו אותם אחד־אחד:
              ‏{punct} מהם זהים לטקסט מילה במילה למעט פיסוק, ורק{" "}
              <b className="text-[var(--dk-bad)]">{bad}</b> הם ניסוח מחדש אמיתי —{" "}
              {((bad / Math.max(v.quotes_total, 1)) * 100).toFixed(1)}% מכלל
              הציטוטים.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              המדידה הזאת לא ריככה את הכלל. ריכוך היה קונה שיעור מעבר גבוה יותר
              במחיר הערובה היחידה כאן — ששני סוגי הטעות נופלים לאותו כיוון:
              פחות על המסך, אף פעם לא יותר.
            </p>
            {ex && ex.dropped.length > 0 && (
              <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-3 py-2.5">
                <div className="text-[13px] text-[var(--dk-ink-3)]">
                  {ex.source_he} · הכיוון שבו בחרנו לטעות
                </div>
                <div className="text-[15.5px] font-semibold leading-snug">
                  {ex.title}
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-2">
                  <span className="text-[15px] text-[var(--dk-ink-3)]">
                    המודל החזיר:
                  </span>
                  {ex.dropped.map((term) => (
                    <span
                      key={term}
                      className="rounded-md border border-[var(--dk-bad)]/45 bg-[var(--dk-bad)]/10 px-2 py-0.5 text-[15.5px] font-semibold text-[var(--dk-bad)] line-through"
                    >
                      {term}
                    </span>
                  ))}
                </div>
                <p className="mt-1 text-[15px] leading-snug text-[var(--dk-ink-2)]">
                  הבדיקה משווה מחרוזות ולא נטיות. הפתיח כותב את אותו שורש בנטייה
                  אחרת, ולכן המילה ירדה למרות שהיא שם. זו טעות — והיא בדיוק
                  בכיוון שבחרנו.
                </p>
              </div>
            )}
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="מה המודל כתב, ומה כתוב בטקסט" hint="דוגמה אחת מכל סוג פסילה">
        {f?.quote_examples.length && v ? (
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-2">
              {v.quote_reasons.map((r) => {
                const meta = REASONS[r.kind];
                return (
                  <div key={r.kind} className="flex items-center gap-2.5">
                    <span className="w-[150px] shrink-0 text-[15px] font-semibold">
                      {meta?.label_he ?? r.kind}
                    </span>
                    <div className="h-4 flex-1 overflow-hidden rounded-md bg-[var(--dk-surface-2)]">
                      <div
                        className={`h-full rounded-md ${
                          meta?.tone === "good"
                            ? "bg-[var(--dk-good)]"
                            : "bg-[var(--dk-bad)]"
                        }`}
                        style={{ width: `${(r.n / maxReason) * 100}%` }}
                      />
                    </div>
                    <span
                      dir="ltr"
                      className="w-[34px] shrink-0 text-left font-mono text-[15px] font-bold text-[var(--dk-ink)]"
                    >
                      {r.n}
                    </span>
                  </div>
                );
              })}
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              כמה מ־{v.quotes_rejected} הפסילות נפלו בכל סיבה. ירוק = הכלל תפס
              בעיה אמיתית, אדום = הכלל היה קשוח מדי.
            </p>

            {f.quote_examples.map((q) => (
              <div
                key={q.kind}
                className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/40 px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <Chip tone={REASONS[q.kind]?.tone ?? "bad"}>
                    {REASONS[q.kind]?.label_he ?? q.kind}
                  </Chip>
                  <span className="text-[13.5px] text-[var(--dk-ink-3)]">
                    {q.source_he}
                  </span>
                </div>
                <div className="mt-1 text-[15px] leading-snug text-[var(--dk-ink)]">
                  ״{q.evidence}״
                </div>
                <div className="mt-1 text-[13px] text-[var(--dk-ink-3)]">
                  בטקסט באותו מקום
                </div>
                <div className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                  …{q.excerpt}…
                </div>
              </div>
            ))}

            {a && (
              <div className="rounded-xl border border-[var(--dk-warn)]/35 bg-[var(--dk-warn)]/6 px-3 py-2.5">
                <div className="text-[15.5px] font-bold text-[var(--dk-warn)]">
                  ראשי תיבות בעברית שברו את הפורמט, ותוקנו בבטחה
                </div>
                <p className="mt-1 text-[15px] leading-snug text-[var(--dk-ink-2)]">
                  ‏{a.framing_hits} מ־{a.framing_total} התשובות מכילות גרשיים
                  בתוך מילה, כמעט תמיד ראשי תיבות (
                  {a.examples
                    .filter((x) => x.indexOf('"') > 1)
                    .slice(0, 3)
                    .join(" · ")}
                  ). הגרשיים האלה סוגרים בטעות את המחרוזת שהם יושבים בתוכה. גרש
                  שיש אות עברית משני צדיו לעולם אינו תוחם, ולכן אפשר להבריח
                  אותו בלי לגעת בערך.
                </p>
                <p className="mt-1 text-[14.5px] text-[var(--dk-ink-3)]">
                  <CodeRef path="_repair_hebrew_quotes" />
                </p>
              </div>
            )}
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

function RateRow({
  label,
  rejected,
  total,
}: {
  label: string;
  rejected: number;
  total: number;
}) {
  const share = total > 0 ? (rejected / total) * 100 : 0;
  return (
    <div className="flex items-center gap-2.5">
      <span className="w-[104px] shrink-0 text-[15.5px] text-[var(--dk-ink-2)]">
        {label}
      </span>
      <div className="h-5 flex-1 overflow-hidden rounded-md bg-[var(--dk-good)]/25">
        <div
          className="h-full bg-[var(--dk-bad)]/70"
          style={{ width: `${Math.max(share, rejected > 0 ? 2 : 0)}%` }}
        />
      </div>
      <span
        dir="ltr"
        className="w-[92px] shrink-0 text-left font-mono text-[14.5px] text-[var(--dk-ink-2)]"
      >
        {rejected}/{total}
      </span>
    </div>
  );
}

/* ── shared ─────────────────────────────────────────────────────── */

function Missing() {
  return (
    <p className="text-[15px] text-[var(--dk-ink-3)]">
      אין קובץ מדידות — הדיאגרמות מוצגות בלי המספרים.
    </p>
  );
}
