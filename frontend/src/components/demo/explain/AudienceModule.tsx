"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import { CodeRef, MetricCard, Panel, Stage, SubNav, type TabDef } from "./kit";

const TABS: TabDef[] = [
  { id: "lexicon", label_he: "המילון ומה הקהל מדבר בו" },
  { id: "measures", label_he: "מה כל מספר אומר על הקהל" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the audience signal — the only input the pipeline does not control.
 *
 * Two tabs, four panels. First where the word list comes from: a published
 * dictionary (Simchon, Brady & Van Bavel 2022) that was found rather than
 * written, and its two axes — what the argument is about, and who it is
 * against — read against this snapshot's own comments. Then every variable the
 * layer measures, in one table with a plain sentence per row, and the one
 * reading decision that changes the answer: the 85th percentile, not the mean.
 *
 * The two-axis counts and `polar_ratio` come from two different word lists and
 * are never blended on screen; see demo/README.md item 59.
 */
export function AudienceModule({ facts }: Props) {
  const [tab, setTab] = useState("lexicon");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "lexicon" && <Dictionary facts={facts} />}
      {tab === "measures" && <Measures facts={facts} />}
    </div>
  );
}

/* ── shared ─────────────────────────────────────────────────────── */

function num(n: number): string {
  return n.toLocaleString("en-US");
}

function share(part: number, whole: number): string {
  return whole > 0 ? `${((part / whole) * 100).toFixed(0)}%` : "—";
}

/** The quantile as it is spoken on screen: 0.85 → "85". */
function qLabel(q: number): string {
  return (q * 100).toFixed(0);
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
    <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-2.5 py-3 text-center">
      <div
        className={`text-[34px] font-black leading-[1.1] ${colors[tone]}`}
        dir="ltr"
      >
        {value}
      </div>
      <div className="mt-1.5 text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
        {label}
      </div>
    </div>
  );
}

/** One dictionary word and how often the audience reached for it. */
function WordBar({
  word,
  n,
  max,
  tone,
}: {
  word: string;
  n: number;
  max: number;
  tone: "accent" | "bad";
}) {
  const color = tone === "bad" ? "var(--dk-bad)" : "var(--dk-accent)";
  return (
    <div className="flex items-center gap-2.5">
      <span className="w-[74px] shrink-0 text-[16px] font-semibold">{word}</span>
      <div className="h-3.5 flex-1 overflow-hidden rounded-md bg-[var(--dk-surface-2)]">
        <div
          className="h-full rounded-md"
          style={{ width: `${(n / max) * 100}%`, background: color }}
        />
      </div>
      <span
        dir="ltr"
        className="w-[42px] shrink-0 text-left font-mono text-[13.5px] text-[var(--dk-ink-2)]"
      >
        {num(n)}
      </span>
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

/* ── 1. where the words come from, and which of them the audience used ── */

function Dictionary({ facts }: Props) {
  const r = facts?.audience.research;
  const onlyAff = r ? r.with_affective - r.with_both : 0;
  const onlyIss = r ? r.with_issue - r.with_both : 0;
  const maxWord = Math.max(
    1,
    ...(r?.top_issue.map((w) => w.n) ?? [1]),
    ...(r?.top_affective.map((w) => w.n) ?? [1]),
  );

  return (
    <Stage cols="grid-cols-[49%_1fr]">
      <Panel
        title={
          r
            ? `${r.source_words} מילים מתוך מחקר שפורסם, לא רשימה שכתבנו`
            : "מאיפה המילון"
        }
      >
        {r ? (
          <div className="flex flex-col gap-3.5">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              מילון שכותבים לבד מודד את הדעות של מי שכתב אותו. המילון כאן מגיע
              ממחקר שפורסם ‏— {r.citation} — והמילים בו לא נבחרו לפי תחושה: הן
              נמצאו לפי איך שהן נעות ברשת. מילה שמתפשטת רק בתוך מחנה אחד היא
              מילה מקטבת, וזו הגדרה שאפשר למדוד.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              המחקר פיצל את המילון לשני צירים, ושניהם נמדדים כאן בנפרד:
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              <div className="rounded-xl border border-[var(--dk-accent)]/45 bg-[var(--dk-accent-dim)]/40 p-3">
                <div className="flex items-baseline gap-2">
                  <code dir="ltr" className="font-mono text-[15px] font-bold text-[var(--dk-accent)]">
                    issue
                  </code>
                  <span className="text-[16.5px] font-bold">על מה הוויכוח</span>
                </div>
                <p className="mt-1 text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
                  {r.top_issue.slice(0, 3).map((w) => w.word).join(", ")} —
                  שפה של נושא. הקהל מתווכח על העניין עצמו.
                </p>
                <div className="mt-1.5 text-[14px] text-[var(--dk-ink-3)]">
                  {r.lemmas_issue} ערכים
                </div>
              </div>
              <div className="rounded-xl border border-[var(--dk-bad)]/45 bg-[var(--dk-bad)]/8 p-3">
                <div className="flex items-baseline gap-2">
                  <code dir="ltr" className="font-mono text-[15px] font-bold text-[var(--dk-bad)]">
                    affective
                  </code>
                  <span className="text-[16.5px] font-bold">נגד מי</span>
                </div>
                <p className="mt-1 text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
                  {r.top_affective.slice(0, 3).map((w) => w.word).join(", ")} —
                  שפה של עוינות. הקהל תוקף צד, לא טענה.
                </p>
                <div className="mt-1.5 text-[14px] text-[var(--dk-ink-3)]">
                  {r.lemmas_affective} ערכים
                </div>
              </div>
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              הגרסה העברית היא {r.lemmas} ערכים, ולכל אחד רשום מאיפה הוא הגיע:{" "}
              {r.provenance.simchon} מהמילון המקורי, {r.provenance.media} מילות
              תקשורת, {r.provenance.israeli} תוספת ישראלית,{" "}
              {r.provenance.review} מסקירה. ‏{num(r.forms)} צורות נבנות מהם
              אופליין — כך אפשר לומר על כל מספר מאיזו מילה הוא בא ומי הכניס
              אותה.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              מה זה קונה: כששואלים למה{" "}
              <b>{r.top_affective[0]?.word}</b> נספרת, התשובה היא מדידה שפורסמה
              ולא הטעם שלנו — וזה ההבדל בין מדד שאפשר להגן עליו לבין דעה עם
              מספרים.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          r
            ? `${num(r.with_any)} מ־${num(r.comments)} התגובות נגעו במילון`
            : "מה הקהל אמר בפועל"
        }
        hint="שני הצירים נמדדים בנפרד על אותו טקסט"
      >
        {r ? (
          <div className="flex flex-col gap-3.5">
            <div className="grid grid-cols-3 gap-2.5">
              <Big value={num(onlyIss)} label="רק שפת נושא" />
              <Big value={num(onlyAff)} label="רק שפת עוינות" tone="bad" />
              <Big value={num(r.with_both)} label="שתיהן באותה תגובה" tone="warn" />
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              <div className="flex flex-col gap-1.5">
                {r.top_issue.map((w) => (
                  <WordBar key={w.word} word={w.word} n={w.n} max={maxWord} tone="accent" />
                ))}
              </div>
              <div className="flex flex-col gap-1.5">
                {r.top_affective.map((w) => (
                  <WordBar key={w.word} word={w.word} n={w.n} max={maxWord} tone="bad" />
                ))}
              </div>
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              שש המילים השכיחות בכל ציר: כחול = נושא, אדום = עוינות. המספר הוא
              כמה פעמים המילה הופיעה ב־{num(r.comments)} התגובות, אחרי איחוד כל
              צורות התחיליות שלה. שני הצירים על אותה סקאלה.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              המסקנה: {num(r.hits_issue)} הופעות של שפת נושא מול{" "}
              {num(r.hits_affective)} של שפת עוינות — כמעט שווה בשווה. זה לא קהל
              שרק מקלל ולא קהל שרק מתווכח, אלא שני דיונים שרצים במקביל, ו־
              {num(r.with_both)} תגובות מנהלות את שניהם באותה נשימה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

/* ── 2. every variable, and the one reading decision ────────────── */

function Measures({ facts }: Props) {
  const a = facts?.audience;
  const c = a?.comments;
  const g = a?.aggregate;
  const w = a?.weight;
  const h = a?.hijack;
  const q = a?.quantile;
  const factor =
    g && g.mean_median > 0 ? (g.p85_median / g.mean_median).toFixed(1) : null;
  const peak = w?.curve[w.curve.length - 1];
  const noLikes = w?.per_source.filter((s) => s.likes === 0) ?? [];
  const noLikeComments = noLikes.reduce((t, s) => t + s.comments, 0);

  return (
    <Stage cols="grid-cols-[52%_1fr]">
      <Panel title="שבעה מספרים, ולכל אחד תפקיד אחד" hint="כל טווח נאמר עם שני הקצוות שלו">
        {c && g && h && q !== undefined ? (
          <div className="flex flex-col gap-3">
            <table className="w-full text-[16px]">
              <thead>
                <tr className="text-[14px] text-[var(--dk-ink-3)]">
                  <th className="pb-1.5 text-right font-medium">המשתנה</th>
                  <th className="pb-1.5 text-right font-medium">מה הוא סופר</th>
                  <th className="pb-1.5 text-right font-medium">טווח</th>
                  <th className="pb-1.5 text-right font-medium">מה לומדים ממנו</th>
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    f: "polar_count",
                    what: "מילים מהמילון בתגובה",
                    range: "0 = אף אחת · בלי תקרה",
                    learn: "ספירה גולמית — מודדת גם אורך, ולכן אינה הציון",
                  },
                  {
                    f: "comment_len",
                    what: "מילים בתגובה",
                    range: `1 = מילה אחת · חציון ${c.len_median} · הארוכה ${c.len_max}`,
                    learn: "המכנה שמנטרל אורך — בלעדיו מדדנו מי כתב יותר",
                  },
                  {
                    f: "polar_ratio",
                    what: "החלק הטעון מתוך התגובה",
                    range: "0 = נקייה · 1 = כל מילה טעונה",
                    learn: "עוצמת התגובה הבודדת, בלי קשר לאורכה",
                  },
                  {
                    f: "engagement_weight",
                    what: "כמה קוראים אהבו אותה",
                    range: peak
                      ? `1 = בלי לייקים · ${peak.weight.toFixed(1)} = ${num(peak.likes)} לייקים, השיא בסנאפשוט`
                      : "1 ומעלה",
                    learn: "כמה מהציון של הכתבה התגובה הזו רשאית לקבוע",
                  },
                  {
                    f: "audience_mean",
                    what: "הממוצע המשוקלל של הכתבה",
                    range: `0 = איש לא נגע במילון · 1 = כולם · חציון ${g.mean_median.toFixed(4)}`,
                    learn: "כמה טעון הדיון כולו — כולל מי שלא אמר כלום",
                  },
                  {
                    f: "audience_p85",
                    what: "הקצה העליון של הדיון",
                    range: `0 = גם הקצה נקי · 1 = הקצה כולו טעון · חציון ${g.p85_median.toFixed(4)}`,
                    learn: "כמה טעון הקול החזק — וזה הציון שמוצג באתר",
                  },
                  {
                    f: "נושא התגובות",
                    what: "לאיזו קטגוריה נופלות כל התגובות יחד",
                    range: "אחת מ־7 קטגוריות",
                    learn: `ב־${h.hijacked} מ־${h.comparable} הכתבות הוא שונה מנושא הכתבה`,
                  },
                ].map((row) => (
                  <tr key={row.f} className="border-t border-[var(--dk-border)]/60">
                    <td className="py-1.5 pe-2 align-top">
                      <code dir="ltr" className="font-mono text-[14.5px] text-[var(--dk-accent)]">
                        {row.f}
                      </code>
                    </td>
                    <td className="py-1.5 pe-2 align-top leading-snug">{row.what}</td>
                    <td className="py-1.5 pe-2 align-top text-[14.5px] leading-snug text-[var(--dk-ink-3)]">
                      {row.range}
                    </td>
                    <td className="py-1.5 align-top leading-snug text-[var(--dk-ink-2)]">
                      {row.learn}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex flex-col gap-2 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-3">
              <CodeRef path="comments(comment_id, article_id, source, text, like_count)" />
              <p className="text-[16.5px] leading-snug text-[var(--dk-ink-2)]">
                זו כל הטבלה. אין זהות מגיב ואין חותמת זמן — ויתרנו על מעקב אחרי
                התפתחות הדיון לאורך היום כדי שהמערכת לא תוכל לבנות פרופיל של
                אדם.
              </p>
            </div>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="הממוצע מודד בעיקר כמה קוראים לא אמרו כלום"
        hint={g ? `חציון ${g.counts.median} תגובות לכתבה` : undefined}
      >
        {g && c && w && peak && q !== undefined && factor ? (
          <div className="flex flex-col gap-3.5">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              ‏{share(c.zero_polar, c.total)} מהתגובות מקבלות{" "}
              <span dir="ltr" className="font-mono">
                0.0000
              </span>{" "}
              — המילון לא מכיר אף מילה בהן. הן גוררות כל ממוצע אל השקט, ולכן
              ממוצע מודד כאן בעיקר כמה קוראים לא אמרו כלום.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              אחוזון {qLabel(q)} — הערך שמתחתיו נמצאות {qLabel(q)}% מהתגובות —
              שואל במקום זה כמה טעון הקצה הקולני. אותן תגובות, שתי קריאות, פי{" "}
              {factor}. הרווח: אותו צינור ואותם נתונים, אפס עלות נוספת — רק
              שאלה אחרת.
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              <MetricCard
                name={`אחוזון ${qLabel(q)} של הקהל`}
                field="audience_p85"
                formula={`quantile(ratio, w, ${q})`}
                range="0 – 1"
                reads={[
                  { value: "0.00", means: "גם הקצה נקי ממילים טעונות" },
                  { value: "0.05", means: "החציון בסנאפשוט" },
                  { value: "1.00", means: "הקצה כולו מילים מהמילון" },
                ]}
                measured={`${g.p85_zero} כתבות ב־0 מתוך ${num(g.counts.total)}`}
              />
              <MetricCard
                name="ממוצע הקהל"
                field="audience_mean"
                formula="Σ(ratio·w) / Σw"
                range="0 – 1"
                reads={[
                  { value: "0.00", means: "אף תגובה לא נגעה במילון" },
                  { value: "0.02", means: "החציון בסנאפשוט" },
                  { value: "0.10", means: "דיון טעון לאורך כל התגובות" },
                ]}
                measured={`חציון ${g.mean_median.toFixed(4)}`}
              />
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              תגובה אהודה שוקלת יותר, והשאלה היא כמה. שקלול לפי מספר הלייקים
              עצמו היה נותן לתגובה עם {num(peak.likes)} לייקים את משקלן של{" "}
              {num(peak.likes + 1)} תגובות, וכתבה שלמה הייתה נקבעת בשורה אחת.{" "}
              <code dir="ltr" className="font-mono text-[16px]">
                1 + ln(1 + likes)
              </code>{" "}
              מקצץ אותה ל־{peak.weight.toFixed(1)}: הקהל עדיין נשמע, אף אחד לא
              קונה את הכתבה.
            </p>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              ‏{noLikes.map((s) => s.source_he).join(" ו־")} לא חושפים ספירת
              לייקים, ולכן {num(noLikeComments)} תגובות נכנסות במשקל שווה; היכן
              שיש לייקים ההזזה הממוצעת באחוזון {qLabel(q)} היא{" "}
              {w.shift_p85.toFixed(5)} על סקאלה שהחציון שלה{" "}
              {g.p85_median.toFixed(4)}, וכל מסקנה על ערוץ עומדת גם בלי השקלול.
              ב־{g.counts.under_5} מ־{num(g.counts.total)} הכתבות יש פחות מחמש
              תגובות, ושם אחוזון {qLabel(q)} הוא התגובה השנייה מלמעלה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}
