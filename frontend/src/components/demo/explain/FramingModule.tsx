"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import {
  Caveat,
  Chip,
  CodeRef,
  Node,
  Panel,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "why", label_he: "למה מודל ולא קוד" },
  { id: "output", label_he: "פלט המודל" },
  { id: "ground", label_he: "כלל העיגון" },
  { id: "rejects", label_he: "למה ציטוטים נפסלו" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the one layer that is not deterministic, and the deterministic
 * check bolted to its output.
 *
 * Four decisions, one per tab: pay for framing because it is the only
 * question here without a computable answer; do not lean on the provider's
 * JSON guarantee, because valid JSON says nothing about whether the content
 * is true; verify against exactly the window the model read, from a single
 * shared constant; and leave the verifier strict even after measuring that
 * most of its rejections are punctuation rather than invention.
 */
export function FramingModule({ facts }: Props) {
  const [tab, setTab] = useState("why");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "why" && <WhyModel facts={facts} />}
      {tab === "output" && <Output facts={facts} />}
      {tab === "ground" && <Ground facts={facts} />}
      {tab === "rejects" && <Rejects facts={facts} />}
    </div>
  );
}

/* ── 1. the question that has no computable answer ──────────────── */

/** The five keys the prompt asks for, in the order the extractor lists them. */
const FIELD: Record<string, { label_he: string; why_he: string }> = {
  actor: {
    label_he: "מי מוצג כמבצע",
    why_he: "אותה עובדה עם נושא מפורש או בלעדיו",
  },
  responsibility: {
    label_he: "למי מיוחסת האחריות",
    why_he: "מי מוצג כאשם במצב — לרוב לא מי שביצע",
  },
  loaded_terms: {
    label_he: "מילים טעונות בכותרת",
    why_he: "תארים שיפוטיים; השדה שהמאמת בודק הכי קשוח",
  },
  voice: {
    label_he: "קול פעיל או סביל",
    why_he: '"נהרגו" מול "כוחותינו הרגו" — אחריות אחרת',
  },
  lead_perspective: {
    label_he: "מנקודת מבט של מי נפתח",
    why_he: "מי מקבל את המשפט הראשון",
  },
};

function WhyModel({ facts }: Props) {
  const f = facts?.framing;
  const d = f?.distribution;
  const passive = d?.voice.find((v) => v.label === "passive")?.n ?? 0;
  const zeroTerms = d?.terms_per_article.find((t) => t.terms === 0)?.n ?? 0;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[42%_1fr] gap-3">
      <Panel
        title="מילון לא יודע מי מוצג כמבצע"
        hint={
          f
            ? `${f.cache.contrast} קריאות השוואה נוספות · עד ${f.contrast_versions} גרסאות`
            : undefined
        }
      >
        {f ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              {f.cache.framing} כותרות הגיעו למודל, אחרי שכל שאלה עם תשובה
              מחושבת נענתה בקוד. מסגור — איך אותה עובדה מוצגת — הוא מידע תחבירי,
              ומילון עשיר יותר לא מגיע לשם.
            </p>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              הדרג קבוע: קוד דטרמיניסטי, מודל מקומי, קריאה בתשלום, ואימות
              דטרמיניסטי אחריה.
            </p>
            <div className="grid grid-cols-2 gap-2">
              <Node title={f.model} mono sub="דגם החילוץ" />
              <Node
                title={`temperature = ${f.temperature}`}
                mono
                sub="אותה כותרת מחזירה אותו פלט; קרוב לדטרמיניזם, לא הבטחה"
              />
              <Node
                title={`${f.lead_chars} תווים`}
                sub="הכותרת והפתיח — כל ההקשר שהמודל מקבל"
              />
              <Node
                title={`max_tokens = ${f.max_tokens.framing}`}
                mono
                sub="JSON קצר, בלי מקום לנאום"
              />
            </div>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="חמשת השדות, ומה חזר בהם" hint="מחקר מסגור תקשורתי">
        {f && d ? (
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              {f.keys.map((key) => (
                <div
                  key={key}
                  className="flex items-baseline gap-2.5 rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-3 py-1.5"
                >
                  <code
                    dir="ltr"
                    className="w-[128px] shrink-0 font-mono text-[13px] text-[var(--dk-accent)]"
                  >
                    {key}
                  </code>
                  <span className="text-[15px] font-semibold">
                    {FIELD[key]?.label_he ?? key}
                  </span>
                  <span className="text-[13.5px] leading-snug text-[var(--dk-ink-3)]">
                    {FIELD[key]?.why_he}
                  </span>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-2 text-center">
              <Stat n={passive} of={d.total} label="קול סביל" />
              <Stat n={d.actor_null} of={d.total} label="בלי מבצע מזוהה" />
              <Stat
                n={d.responsibility_null}
                of={d.total}
                label="בלי ייחוס אחריות"
              />
            </div>

            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              רק {passive} כותרות בסביל. זה ממצא על העיתונות הישראלית שנמדד כאן,
              לא הנחה, והמשתנה הזה כמעט לא מפריד בין ערוצים בסנאפשוט.
            </p>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              {zeroTerms} כותרות חזרו בלי אף מילה טעונה. שדה ריק הוא תשובה, לא
              כישלון.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

function Stat({ n, of, label }: { n: number; of: number; label: string }) {
  return (
    <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-2">
      <div className="text-2xl font-black text-[var(--dk-accent)]" dir="ltr">
        {n}
        <span className="text-[15px] font-normal text-[var(--dk-ink-3)]">
          /{of}
        </span>
      </div>
      <div className="text-[13px] leading-snug text-[var(--dk-ink-2)]">
        {label}
      </div>
    </div>
  );
}

/* ── 2. structured output, and the parser that does not trust it ── */

function Output({ facts }: Props) {
  const f = facts?.framing;
  const a = f?.acronyms;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[44%_1fr] gap-3">
      <Panel title="‏JSON תקין לא מבטיח שהתוכן נכון">
        <div className="flex flex-col gap-3">
          <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
            הפייפליין מבקש מהמודל אובייקט JSON דרך{" "}
            <CodeRef path="response_format" />. שכבת הסוכנים כאן לא נשענת עליו.
          </p>
          <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
            היא מחלצת את האובייקט הראשון מהמחרוזת, ואז מאמתת כל ביטוי מול הטקסט.
            סכמה קונה פענוח, לא אמת.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <CodeRef path="src/nlp/classify.py" />
            <CodeRef path="demo/core/framing.py · _json_object" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Node
              title="גדרות קוד ופרוזה עוטפת"
              sub="חלק מהתשובות מגיעות עטופות בגדר קוד או עם משפט מלווה. נחלץ את האובייקט הראשון במקום להיכשל."
            />
            <Node
              title='המחרוזת "null" במקום null'
              sub="המודל מחזיר לפעמים את המילה. שלושה שדות מנורמלים ידנית."
            />
            <Node
              title="voice שאינו active/passive"
              sub="כל ערך אחר הופך ל־null. שדה ריק עדיף על ערך שאי אפשר להשוות."
            />
          </div>
        </div>
      </Panel>

      <Panel title="גרש בתוך ראשי תיבות שבר את ה־JSON" hint="_repair_hebrew_quotes">
        {a ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              {a.framing_hits + a.contrast_hits} מתוך{" "}
              {a.framing_total + a.contrast_total} הפלטים במטמון מכילים ראשי
              תיבות עם גרש ({a.distinct} שונים).
            </p>
            <div className="flex flex-wrap gap-1.5">
              {a.examples.map((x) => (
                <span
                  key={x}
                  className="rounded-md border border-[var(--dk-warn)]/35 bg-[var(--dk-warn)]/8 px-2 py-0.5 font-mono text-[13px] text-[var(--dk-warn)]"
                >
                  {x}
                </span>
              ))}
            </div>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              המודל פולט את הגרש לא מוברח, והוא שובר את מחרוזת ה־JSON שהוא יושב
              בתוכה. בלי התיקון הפלטים האלה היו נופלים בפענוח.
            </p>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              גרש שיש אות עברית משני צדיו אף פעם אינו תוחם, ולכן ההברחה בטוחה
              והערך שומר על ראשי התיבות כלשונם.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

/* ── 3. the grounding rule and what it caught ───────────────────── */

function Ground({ facts }: Props) {
  const f = facts?.framing;
  const v = f?.verifier;
  const ex = f?.term_example;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[40%_1fr] gap-3">
      <Panel title="קבוע אחד לחילוץ ולאימות, אחרי אישור שווא">
        {f ? (
          <div className="flex flex-col gap-3">
            <div
              dir="rtl"
              className="rounded-lg border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)]/40 px-3 py-2 text-center text-[15.5px] font-semibold text-[var(--dk-accent)]"
            >
              ביטוי שאינו מופיע בטקסט שהמודל קיבל — יורד מהמסך
            </div>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              עיגון הוא השוואת מחרוזות: מנרמלים גרשיים ורווחים ובודקים הכלה
              בכותרת ובפתיח. אין כאן דעה שנייה של מודל.
            </p>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              כשהאימות קרא חלון רחב מ־{f.lead_chars} התווים שהחילוץ קיבל, ביטוי
              שהמודל מעולם לא ראה עבר אימות. לכן{" "}
              <CodeRef path="EXTRACT_LEAD_CHARS" /> הוא קבוע יחיד שהשניים
              מייבאים.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          v
            ? `${v.terms_rejected} מתוך ${v.terms_total} מילים טעונות נפסלו`
            : "שיעורי הפסילה"
        }
        hint="על כל המטמון, לא על אירוע אחד"
      >
        {v && ex ? (
          <div className="flex flex-col gap-3">
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
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              {v.actors_exact} מהמבצעים נמצאו כמחרוזת מלאה ו־{v.actors_word_level}{" "}
              רק ברמת מילה בודדת. המודל מחזיר לפעמים שם מלא שהכתבה עצמה קיצרה,
              ולכן ההתאמה למבצע רופפת מזו של מילה טעונה.
            </p>

            <div className="rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/60 px-3 py-2">
              <div className="text-[13px] text-[var(--dk-ink-3)]">
                {ex.source_he} · כותרת
              </div>
              <div className="text-[15.5px] font-semibold leading-snug">
                {ex.title}
              </div>
              <div className="mt-1.5 text-[13px] text-[var(--dk-ink-3)]">
                הפתיח שהמודל וגם המאמת ראו
              </div>
              <div className="max-h-[92px] overflow-auto text-[14px] leading-snug text-[var(--dk-ink-2)]">
                {ex.lead}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[14px] text-[var(--dk-ink-3)]">
                המודל החזיר:
              </span>
              {ex.dropped.map((t) => (
                <span
                  key={t}
                  className="rounded-md border border-[var(--dk-bad)]/45 bg-[var(--dk-bad)]/10 px-2 py-0.5 text-[15px] font-semibold text-[var(--dk-bad)] line-through"
                >
                  {t}
                </span>
              ))}
              {ex.kept.map((t) => (
                <span
                  key={t}
                  className="rounded-md border border-[var(--dk-good)]/45 bg-[var(--dk-good)]/10 px-2 py-0.5 text-[15px] font-semibold text-[var(--dk-good)]"
                >
                  {t}
                </span>
              ))}
            </div>

            <Caveat>
              המאמת משווה מחרוזות ולא נטיות. הפתיח כותב את אותו שורש בנטייה
              אחרת, ולכן ״{ex.dropped[0]}״ ירד. זה הכיוון הבטוח לטעות בו, וזו
              עדיין טעות.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
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
      <span className="w-[104px] shrink-0 text-[15px] text-[var(--dk-ink-2)]">
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
        className="w-[92px] shrink-0 text-left font-mono text-[14px] text-[var(--dk-ink-2)]"
      >
        {rejected}/{total}
      </span>
    </div>
  );
}

/* ── 4. auditing the verifier itself ────────────────────────────── */

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
    note_he: 'הציטוט נכון אבל עטוף ב"כותרת:" — פסילה מיותרת',
    tone: "warn",
  },
};

function Rejects({ facts }: Props) {
  const f = facts?.framing;
  const v = f?.verifier;
  const maxReason = Math.max(1, ...(v?.quote_reasons.map((r) => r.n) ?? [1]));
  const punct = v?.quote_reasons.find((r) => r.kind === "punct")?.n ?? 0;
  const bad = v?.quote_reasons.find((r) => r.kind === "paraphrase")?.n ?? 0;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <Panel
        title={
          v
            ? `${punct} מתוך ${v.quotes_rejected} הפסילות הן פיסוק בלבד`
            : "פירוק הפסילות"
        }
        hint={v ? `על כל ${v.quotes_total} ציטוטי הראיה במטמון` : undefined}
      >
        {f && v ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              {v.quotes_rejected} מתוך {v.quotes_total} ציטוטי הראיה לא נמצאו
              בטקסט כלשונם. שיעור כזה נשמע כמו מודל שממציא.
            </p>

            <div className="flex flex-col gap-2.5">
              {v.quote_reasons.map((r) => {
                const meta = REASONS[r.kind];
                return (
                  <div key={r.kind} className="flex flex-col gap-1">
                    <div className="flex items-center gap-2.5">
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
                    <span className="pe-[150px] text-[13.5px] leading-snug text-[var(--dk-ink-3)]">
                      {meta?.note_he}
                    </span>
                  </div>
                );
              })}
            </div>

            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              המודל ניסח מחדש או השמיט ב־
              <b className="text-[var(--dk-bad)]">{bad}</b> מתוך {v.quotes_total}{" "}
              הציטוטים —{" "}
              {((bad / Math.max(v.quotes_total, 1)) * 100).toFixed(1)}%. שאר
              הפסילות הן קשיחות יתר שלנו.
            </p>

            <Caveat>
              לא ריככנו את הכלל בעקבות המדידה. ריכוך היה מעלה את שיעור המעבר על
              חשבון הערובה היחידה כאן, שכל ביטוי על המסך נמצא בטקסט כלשונו. שתי
              הטעויות נופלות לאותו כיוון: פחות על המסך, לא יותר.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="מה המודל כתב, ומה כתוב בטקסט" hint="שלוש הפסילות, אחת מכל סוג">
        {f?.quote_examples.length ? (
          <div className="flex flex-col gap-2.5">
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
                <div className="mt-1 text-[14.5px] leading-snug text-[var(--dk-ink)]">
                  ״{q.evidence}״
                </div>
                <div className="mt-1 text-[13px] text-[var(--dk-ink-3)]">
                  בטקסט באותו מקום
                </div>
                <div className="text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
                  …{q.excerpt}…
                </div>
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

/* ── shared ─────────────────────────────────────────────────────── */

function Missing() {
  return (
    <p className="text-[15px] text-[var(--dk-ink-3)]">
      אין קובץ מדידות — הדיאגרמות מוצגות בלי המספרים.
    </p>
  );
}
