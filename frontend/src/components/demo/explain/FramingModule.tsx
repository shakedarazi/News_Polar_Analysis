"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import {
  BarRow,
  Caveat,
  Chip,
  CodeRef,
  Node,
  Panel,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "why", label_he: "למה מודל שפה" },
  { id: "back", label_he: "מה חוזר בפועל" },
  { id: "contrast", label_he: "הצעד הקונטרסטיבי" },
  { id: "verify", label_he: "המאמת" },
  { id: "audit", label_he: "ביקורת על המאמת" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the one layer that is not deterministic, and the deterministic
 * check bolted to its output.
 *
 * The order of the tabs is the argument: a model is used only where counting
 * cannot reach, everything it returns is measured across the whole cache, and
 * the last tab turns the same scrutiny on our own verifier — which turns out
 * to reject twice as much for punctuation as for invention.
 */
export function FramingModule({ facts }: Props) {
  const [tab, setTab] = useState("why");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "why" && <WhyModel facts={facts} />}
      {tab === "back" && <WhatComesBack facts={facts} />}
      {tab === "contrast" && <Contrast facts={facts} />}
      {tab === "verify" && <Verify facts={facts} />}
      {tab === "audit" && <Audit facts={facts} />}
    </div>
  );
}

/* ── 1. why a model at all ──────────────────────────────────────── */

const VARIABLES: { key: string; label_he: string; why_he: string }[] = [
  {
    key: "actor",
    label_he: "מי מוצג כמבצע",
    why_he: "אותה עובדה כשהיא מיוחסת לגורם מפורש או נשארת בלי נושא",
  },
  {
    key: "responsibility",
    label_he: "למי מיוחסת האחריות",
    why_he: "מי מוצג כאשם במצב — לרוב לא אותו גורם שביצע",
  },
  {
    key: "loaded_terms",
    label_he: "מילים טעונות בכותרת",
    why_he: "תארים שיפוטיים; זה השדה שהמאמת בודק הכי קשוח",
  },
  {
    key: "voice",
    label_he: "קול פעיל או סביל",
    why_he: '"נהרגו" מול "כוחותינו הרגו" — אותו אירוע, אחריות אחרת',
  },
  {
    key: "lead_perspective",
    label_he: "מנקודת מבט של מי נפתח",
    why_he: "מי מקבל את המשפט הראשון",
  },
];

function WhyModel({ facts }: Props) {
  const f = facts?.framing;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="הגבול של הלקסיקון">
          <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
            ספירת מילים אומרת <b>על מה</b> הכתבה. היא לא יכולה לומר מי מוצג
            כמבצע הפעולה ולמי מיוחסת האחריות — שתי כותרות עם אותו פרופיל
            לקסיקוני בדיוק יכולות לייחס את אותו אירוע לשני גורמים הפוכים. זו לא
            בעיה של מילון עשיר יותר; זה מידע תחבירי, לא מילוני.
          </p>
        </Panel>

        <Panel title="חמשת המשתנים שמבקשים מהמודל" hint="מחקר מסגור תקשורתי">
          <div className="flex flex-col gap-1.5">
            {VARIABLES.map((v) => (
              <div
                key={v.key}
                className="flex items-baseline gap-2.5 rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-3 py-1.5"
              >
                <code
                  dir="ltr"
                  className="w-[128px] shrink-0 font-mono text-[13px] text-[var(--dk-accent)]"
                >
                  {v.key}
                </code>
                <span className="text-[15px] font-semibold">{v.label_he}</span>
                <span className="text-[13.5px] leading-snug text-[var(--dk-ink-3)]">
                  {v.why_he}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="הקריאה עצמה"
          hint="demo/core/framing.py · FramingExtractor"
        >
          <div className="grid grid-cols-2 gap-2">
            <Node title={f?.model ?? "gpt-4o-mini"} mono sub="דגם החילוץ" />
            <Node
              title={`temperature = ${f?.temperature ?? 0}`}
              mono
              sub="אותה כותרת מחזירה אותו פלט; לא דטרמיניזם מובטח, אבל הכי קרוב שאפשר"
            />
            <Node
              title={`${f?.lead_chars ?? 500} תווים`}
              sub="הכותרת + פתיח באורך הזה — זה כל ההקשר שהמודל מקבל"
            />
            <Node
              title={`max_tokens = ${f?.max_tokens.framing ?? 260}`}
              mono
              sub="JSON קצר, בלי מקום לנאום"
            />
          </div>
        </Panel>

        <Panel title="למה 500 הוא קבוע אחד ולא שניים">
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            אותו חלון בדיוק משמש את החילוץ ואת האימות. חלון אימות רחב יותר היה
            מכשיר ביטוי מומצא רק כי הוא במקרה מופיע עמוק בגוף הכתבה; חלון צר
            יותר היה פוסל ביטויים שהמודל באמת קרא — בדיקה מול הכותרת בלבד נתנה
            33% עיגון במקום 93% במדידה הראשונה. לכן{" "}
            <CodeRef path="EXTRACT_LEAD_CHARS" /> הוא קבוע יחיד שהשניים
            מייבאים.
          </p>
        </Panel>

        {f && (
          <Panel title="הפרומפט כפי שהוא נשלח" hint="FRAMING_SYSTEM">
            <p
              dir="rtl"
              className="max-h-[132px] overflow-auto rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/60 px-3 py-2 text-[13.5px] leading-snug text-[var(--dk-ink-2)]"
            >
              {f.framing_system}
            </p>
          </Panel>
        )}
      </div>
    </div>
  );
}

/* ── 2. what actually comes back ────────────────────────────────── */

function WhatComesBack({ facts }: Props) {
  const f = facts?.framing;
  const d = f?.distribution;
  const maxTerms = Math.max(1, ...(d?.terms_per_article.map((t) => t.n) ?? [1]));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="מילים טעונות לכתבה"
          hint={d ? `${d.total} חילוצים במטמון` : undefined}
        >
          {d ? (
            <div className="flex flex-col gap-2">
              {d.terms_per_article.map((t) => (
                <div key={t.terms} className="flex-1">
                  <BarRow
                    label={`${t.terms} מילים`}
                    n={t.n}
                    max={maxTerms}
                    tone={t.terms === 0 ? "muted" : "accent"}
                    note={t.terms === 0 ? "כותרת ניטרלית" : undefined}
                  />
                </div>
              ))}
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        {d && (
          <Panel title="שדות שחוזרים ריקים — וזה תקין">
            <div className="grid grid-cols-3 gap-2 text-center">
              <Stat n={d.voice.find((v) => v.label === "passive")?.n ?? 0} of={d.total} label="קול סביל" />
              <Stat n={d.actor_null} of={d.total} label="בלי מבצע מזוהה" />
              <Stat n={d.responsibility_null} of={d.total} label="בלי ייחוס אחריות" />
            </div>
            <p className="mt-2 text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
              רק {d.voice.find((v) => v.label === "passive")?.n ?? 0} כותרות
              בסביל. זה ממצא על העיתונות הישראלית שנמדד כאן, לא הנחה — וזה גם
              אומר שהמשתנה הזה כמעט לא מפריד בין ערוצים בסנאפשוט הזה.
            </p>
          </Panel>
        )}
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="פלט מודל הוא מחרוזת, לא מבנה" hint="_json_object">
          <div className="flex flex-col gap-1.5">
            <Node
              title="גדרות קוד ופרוזה עוטפת"
              sub="חלק מהתשובות מגיעות עטופות ב־```json או עם משפט מלווה. נחלץ את האובייקט הראשון במקום להיכשל."
            />
            <Node
              title='המחרוזת "null" במקום null'
              sub="המודל מחזיר לפעמים את המילה. שלושה שדות מנורמלים ידנית."
            />
            <Node
              title="voice שאינו active/passive"
              sub="כל ערך אחר הופך ל־null. עדיף שדה ריק על ערך שאי אפשר להשוות."
            />
          </div>
        </Panel>

        {f && (
          <Panel
            title="הבאג שהיה שליש מהכשלים: גרש בתוך ראשי תיבות"
            hint="_repair_hebrew_quotes"
          >
            <p className="text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
              ראשי תיבות בעברית נכתבים עם גרש בתוך המילה. המודל פולט אותו לא
              מוברח, וזה שובר את מחרוזת ה־JSON שהוא יושב בתוכה. גרש שיש אות
              עברית משני צדיו אף פעם אינו תוחם — ולכן אפשר להבריח אותו בבטחה.
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {f.acronyms.examples.map((a) => (
                <span
                  key={a}
                  className="rounded-md border border-[var(--dk-warn)]/35 bg-[var(--dk-warn)]/8 px-2 py-0.5 font-mono text-[13px] text-[var(--dk-warn)]"
                >
                  {a}
                </span>
              ))}
            </div>
            <p className="mt-2 text-[14.5px] text-[var(--dk-ink-2)]">
              <b className="text-[var(--dk-accent)]">
                {f.acronyms.framing_hits + f.acronyms.contrast_hits}
              </b>{" "}
              מתוך{" "}
              {f.acronyms.framing_total + f.acronyms.contrast_total} הפלטים
              במטמון מכילים ראשי תיבות כאלה ({f.acronyms.distinct} שונים).
              בלי התיקון הם היו נופלים בפענוח.
            </p>
          </Panel>
        )}
      </div>
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

/* ── 3. the contrastive step ────────────────────────────────────── */

function Contrast({ facts }: Props) {
  const f = facts?.framing;
  const ex = f?.contrast_example;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[38%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="כאן האחזור הופך להגברה">
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            הקריאה הזאת היא היחידה שמקבלת את הגרסאות המאוחזרות כהקשר. השאלה
            שנשאלת היא <b>מה ייחודי בגרסה הזאת ביחס לאחרות</b> — שאלה שאי אפשר
            לענות עליה מכתבה בודדת, ולכן זה RAG ולא &quot;לאחזר ואז לסכם&quot;.
          </p>
        </Panel>

        <Panel title="מבנה הפרומפט" hint="build_contrast_prompt">
          <pre
            dir="rtl"
            className="rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/60 px-3 py-2 text-[13.5px] leading-relaxed text-[var(--dk-ink-2)]"
          >
{`--- מקור: <שם הערוץ>
כותרת: <הכותרת>
פתיח: <400 תווים>

--- מקור: ...`}
          </pre>
          <p className="mt-2 text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
            עד {f?.contrast_versions ?? 5} גרסאות בקריאה אחת. מעבר לזה הפרומפט
            מתחיל להידלל והמודל מסכם במקום להנגיד.
          </p>
        </Panel>

        {f && (
          <Panel title="עלות">
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              {f.cache.contrast} קריאות קונטרסטיביות ו־{f.cache.framing} חילוצי
              מסגור נשמרו למטמון. בזמן המיצג לא נשלחת אף בקשה — הקיוסק מנגן פלט
              מודל אמיתי שהוקלט מראש.
            </p>
          </Panel>
        )}
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-2.5">
        {ex ? (
          <>
            <Panel
              title="מה כל הגרסאות מסכימות עליו"
              hint={ex.topic_he ? `אירוע בנושא ${ex.topic_he}` : undefined}
            >
              <p className="text-[16px] leading-snug">{ex.shared}</p>
            </Panel>
            {ex.per_source.map((row) => (
              <div
                key={row.source}
                className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/40 px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <Chip tone="accent">{row.source_he}</Chip>
                  <span className="truncate text-[13.5px] text-[var(--dk-ink-3)]">
                    {row.title}
                  </span>
                </div>
                <div className="mt-1 text-[15px] leading-snug">
                  {row.distinctive}
                </div>
                {row.evidence &&
                  (row.kept ? (
                    <div className="mt-1 border-r-2 border-[var(--dk-good)]/60 pe-2 ps-2 text-[14px] leading-snug text-[var(--dk-ink-2)]">
                      ״{row.evidence}״
                    </div>
                  ) : (
                    <div className="mt-1 flex items-start gap-2">
                      <Chip tone="bad">הציטוט נפסל</Chip>
                      <span className="text-[13.5px] leading-snug text-[var(--dk-ink-3)] line-through">
                        {row.evidence}
                      </span>
                    </div>
                  ))}
              </div>
            ))}
          </>
        ) : (
          <Panel title="דוגמה קונטרסטיבית">
            <Missing />
          </Panel>
        )}
      </div>
    </div>
  );
}

/* ── 4. the verifier ────────────────────────────────────────────── */

function Verify({ facts }: Props) {
  const f = facts?.framing;
  const v = f?.verifier;
  const ex = f?.term_example;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="הכלל" hint="verify_framing · דטרמיניסטי">
          <div className="flex flex-col gap-2">
            <div
              dir="rtl"
              className="rounded-lg border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)]/40 px-3 py-2 text-center text-[15.5px] font-semibold text-[var(--dk-accent)]"
            >
              ביטוי שאינו מופיע בטקסט שהמודל קיבל — יורד מהמסך
            </div>
            <p className="text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
              זו לא דעה שנייה של מודל. זו השוואת מחרוזות: מנרמלים גרשיים
              ורווחים, ובודקים הכלה בתוך הכותרת והפתיח. אין כאן שיפוט — יש
              בדיקה שאפשר להריץ ידנית מול המסך.
            </p>
          </div>
        </Panel>

        {v && (
          <Panel title="שיעורי הפסילה על כל המטמון">
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
            <p className="mt-2 text-[14px] leading-snug text-[var(--dk-ink-3)]">
              מתוך {v.actors_total} שמות מבצע, {v.actors_exact} נמצאו כמחרוזת
              מלאה ו־{v.actors_word_level} רק ברמת מילה בודדת — שמות פרטיים
              נכתבים אחרת בכל ערוץ, ולכן ההתאמה למבצע רופפת מזו של מילה טעונה.
            </p>
          </Panel>
        )}
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        {ex ? (
          <>
            <Panel
              title="פסילה אמיתית, צעד־צעד"
              hint={`${ex.source_he} · בדקו בעצמכם`}
            >
              <div className="flex flex-col gap-2">
                <div className="rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/60 px-3 py-2">
                  <div className="text-[13px] text-[var(--dk-ink-3)]">כותרת</div>
                  <div className="text-[15.5px] font-semibold leading-snug">
                    {ex.title}
                  </div>
                  <div className="mt-1.5 text-[13px] text-[var(--dk-ink-3)]">
                    פתיח (מה שהמודל וגם המאמת ראו)
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
              </div>
            </Panel>

            <Caveat>
              המודל לא המציא כאן כלום: הפתיח אומר &quot;הצעידה
              המבורכת&quot;, והמודל החזיר את הצורה &quot;מברכת&quot;. המאמת
              משווה מחרוזות ולא נטיות, ולכן הוא פוסל. זה הכיוון הבטוח לטעות בו
              — אבל זו טעות.
            </Caveat>
          </>
        ) : (
          <Panel title="דוגמה">
            <Missing />
          </Panel>
        )}
      </div>
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

/* ── 5. auditing the verifier itself ────────────────────────────── */

const REASONS: Record<string, { label_he: string; note_he: string; tone: "bad" | "warn" | "good" }> = {
  paraphrase: {
    label_he: "ניסוח מחדש או השמטה",
    note_he: "המודל חיבר משפטים או שינה מילים — פסילה נכונה",
    tone: "good",
  },
  punct: {
    label_he: "הבדל בפיסוק בלבד",
    note_he: "מילה במילה, למעט נקודה שהמודל הוסיף בסוף — פסילה מיותרת",
    tone: "bad",
  },
  wrapper: {
    label_he: "תווית שהמודל הוסיף",
    note_he: 'הציטוט נכון אבל עטוף ב"כותרת:" — פסילה מיותרת',
    tone: "warn",
  },
};

function Audit({ facts }: Props) {
  const f = facts?.framing;
  const v = f?.verifier;
  const maxReason = Math.max(1, ...(v?.quote_reasons.map((r) => r.n) ?? [1]));
  const bad = v?.quote_reasons.find((r) => r.kind === "paraphrase")?.n ?? 0;
  const share = v
    ? ((v.quotes_rejected / Math.max(v.quotes_total, 1)) * 100).toFixed(0)
    : null;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title={
            share
              ? `${share}% מהציטוטים נפסלו. בגלל מה?`
              : "הציטוטים שנפסלו — בגלל מה?"
          }
        >
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            שיעור פסילה גבוה נשמע כמו מודל שממציא. פירקנו את הפסילות לפי סיבה,
            ומה שיצא הוא בעיקר ביקורת על המאמת שלנו: הוא השוואת־מחרוזת נאיבית,
            ונקודה שהמודל הוסיף בסוף המשפט מפילה ציטוט מדויק לחלוטין.
          </p>
        </Panel>

        {v && (
          <Panel
            title="פירוק הפסילות"
            hint={`${v.quotes_rejected} מתוך ${v.quotes_total} ציטוטים`}
          >
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
          </Panel>
        )}

        {v && (
          <Panel title="המספר שמותר לצטט">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              המודל ניסח מחדש או השמיט ב־<b className="text-[var(--dk-bad)]">{bad}</b>{" "}
              מתוך {v.quotes_total} הציטוטים —{" "}
              {((bad / Math.max(v.quotes_total, 1)) * 100).toFixed(1)}%. שאר
              הפסילות הן קשיחות יתר שלנו. שתי הטעויות נופלות לאותו כיוון: פחות
              על המסך, לא יותר.
            </p>
          </Panel>
        )}
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-2.5">
        {f?.quote_examples.length ? (
          f.quote_examples.map((q) => (
            <Panel
              key={q.kind}
              title={REASONS[q.kind]?.label_he ?? q.kind}
              hint={q.source_he}
            >
              <div className="flex flex-col gap-1.5">
                <div>
                  <div className="text-[13px] text-[var(--dk-ink-3)]">
                    מה המודל כתב
                  </div>
                  <div className="text-[14.5px] leading-snug text-[var(--dk-ink)]">
                    ״{q.evidence}״
                  </div>
                </div>
                <div>
                  <div className="text-[13px] text-[var(--dk-ink-3)]">
                    מה כתוב בטקסט באותו מקום
                  </div>
                  <div className="text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
                    …{q.excerpt}…
                  </div>
                </div>
              </div>
            </Panel>
          ))
        ) : (
          <Panel title="דוגמאות">
            <Missing />
          </Panel>
        )}

        <Caveat>
          לא שינינו את המאמת בעקבות המדידה הזאת. ריכוך הכלל היה מעלה את שיעור
          המעבר על חשבון הערובה היחידה שיש כאן — שכל ביטוי על המסך נמצא בטקסט
          כלשונו. זו החלטה פתוחה, והמספרים לצידה.
        </Caveat>
      </div>
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
