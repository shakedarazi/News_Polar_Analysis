"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import {
  BarRow,
  Caveat,
  Chip,
  CodeRef,
  MetricCard,
  Panel,
  Stage,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "score", label_he: "ציון לתגובה" },
  { id: "weight", label_he: "משקל הלייקים" },
  { id: "tail", label_he: "הזנב הקולני" },
  { id: "limits", label_he: "מה המספר מרשה" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the audience signal — the only input the pipeline does not control.
 *
 * Four decisions, one per tab: score a ratio instead of a raw count, and pay
 * for it with a denominator of one; weight likes logarithmically so a viral
 * comment cannot decide an article, on data two outlets never expose; read the
 * 85th percentile rather than the mean, because three quarters of the comments
 * score zero and drag the mean toward silence; and keep the claim descriptive —
 * no author identity, no timestamps, and a topic gap that is a gap, not a cause.
 */
export function AudienceModule({ facts }: Props) {
  const [tab, setTab] = useState("score");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "score" && <Score facts={facts} />}
      {tab === "weight" && <Weight facts={facts} />}
      {tab === "tail" && <Tail facts={facts} />}
      {tab === "limits" && <Limits facts={facts} />}
    </div>
  );
}

/* ── formatting ─────────────────────────────────────────────────── */

function num(n: number): string {
  return n.toLocaleString("en-US");
}

function share(part: number, whole: number): string {
  return whole > 0 ? `${((part / whole) * 100).toFixed(1)}%` : "—";
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

/* ── 1. a ratio per comment, and what the denominator costs ─────── */

function Score({ facts }: Props) {
  const a = facts?.audience;
  const c = a?.comments;
  const art = a?.artifacts;
  const maxRatio = Math.max(1, ...(c?.ratio_hist.map((b) => b.n) ?? [1]));

  return (
    <Stage cols="grid-cols-[47%_1fr]">
      <Panel
        title={
          art
            ? `${num(art.ratio_one)} תגובות קיבלו את הציון המקסימלי`
            : "שיעור, לא ספירה"
        }
        hint={art ? `${num(art.single_token)} מהן בנות טוקן אחד` : undefined}
      >
        {c && art ? (
          <div className="flex flex-col gap-2.5">
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              ספירה גולמית של מילים טעונות הייתה מודדת אורך: תגובה בת{" "}
              {c.len_max} טוקנים גוברת על כל שורה קצרה. החלוקה באורך מנטרלת את
              זה, והמחיר הוא מכנה של אחת.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {art.examples.map((x, i) => (
                <span
                  key={`${x.text}-${i}`}
                  className="rounded-lg border border-[var(--dk-bad)]/40 bg-[var(--dk-bad)]/8 px-2 py-0.5 text-[14.5px]"
                >
                  {x.text}
                  <span
                    className="ms-1.5 font-mono text-[12.5px] text-[var(--dk-ink-3)]"
                    dir="ltr"
                  >
                    {x.likes}♥
                  </span>
                </span>
              ))}
            </div>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              <code dir="ltr" className="font-mono text-[14px]">
                max(1, len)
              </code>{" "}
              מונע חלוקה באפס, לא מכנה של אחת.
            </p>
            <MetricCard
              name="שיעור מילים טעונות"
              field="polar_ratio"
              formula="polar_count / max(1, comment_len)"
              range="[0, 1]"
              reads={[
                { value: "0.00", means: "המילון לא מכיר אף מילה בתגובה" },
                { value: "0.05", means: "מילה טעונה אחת לכל עשרים מילים" },
                {
                  value: "1.00",
                  means: "כל מילה בתגובה טעונה — כמעט תמיד תגובה בת מילה אחת",
                },
              ]}
              measured={`ממוצע ${c.ratio_mean.toFixed(4)} · אורך חציוני ${c.len_median} טוקנים · הארוכה ביותר ${c.len_max}`}
            />
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          c
            ? `${num(c.zero_polar)} מתוך ${num(c.total)} התגובות מקבלות 0.0000`
            : "התפלגות הציונים"
        }
        hint={
          a && c
            ? `${num(c.articles)} כתבות · מילון של ${num(a.polar_lexicon_forms)} צורות`
            : undefined
        }
      >
        {c ? (
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              {c.ratio_hist.map((b) => (
                <BarRow
                  key={b.label}
                  label={b.label}
                  n={b.n}
                  max={maxRatio}
                  tone={b.label === "0" ? "muted" : "accent"}
                />
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              <Big
                value={share(c.zero_polar, c.total)}
                label="מהתגובות בלי אף מילה מהמילון"
                tone="warn"
              />
              <Big
                value={num(c.len_under_4)}
                label="תגובות באורך 3 טוקנים או פחות"
                tone="accent"
              />
            </div>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              האות נשען על מיעוט התגובות, ולכן הוא רגיש לרעש הרבה יותר ממה
              ש־{num(c.total)} תגובות מרמזות.
            </p>
            <Caveat>
              המילון מודד שכיחות מילים מרשימה, לא כעס. תגובה זועמת שהמילון לא
              מכיר את מילותיה מקבלת 0, ותגובה עניינית עם מילה אחת מהרשימה מקבלת
              ציון חיובי.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

/* ── 2. logarithmic weight, on data two outlets never expose ────── */

function Weight({ facts }: Props) {
  const a = facts?.audience;
  const w = a?.weight;
  const c = a?.comments;
  const g = a?.aggregate;
  const ctrl = a?.controversy;
  const peak = w?.curve[w.curve.length - 1];
  const noLikes = w?.per_source.filter((s) => s.likes === 0) ?? [];
  const noLikeComments = noLikes.reduce((t, s) => t + s.comments, 0);
  const noLikeArticles = noLikes.reduce((t, s) => t + s.articles, 0);

  return (
    <Stage cols="grid-cols-[44%_1fr]">
      <Panel
        title={
          peak
            ? `${num(peak.likes)} לייקים שווים ${peak.weight.toFixed(3)}, לא ${num(peak.likes + 1)}`
            : "עקומת המשקל"
        }
        hint="מול החלופה הליניארית"
      >
        {w && peak ? (
          <div className="flex flex-col gap-3">
            <CodeRef path="engagement_weight = 1 + ln(1 + likes + dislikes)" />
            <table className="w-full text-[15px]" dir="ltr">
              <thead>
                <tr className="text-[13.5px] text-[var(--dk-ink-3)]">
                  <th className="pb-1 text-left font-medium">likes</th>
                  <th className="pb-1 text-left font-medium">weight</th>
                  <th className="pb-1 text-left font-medium">linear</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {w.curve.map((p) => (
                  <tr
                    key={p.likes}
                    className="border-t border-[var(--dk-border)]/60"
                  >
                    <td className="py-0.5">{num(p.likes)}</td>
                    <td className="py-0.5 text-[var(--dk-accent)]">
                      {p.weight.toFixed(3)}
                    </td>
                    <td className="py-0.5 text-[var(--dk-ink-3)]">
                      {num(1 + p.likes)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              משקל ליניארי היה נותן לתגובה הוויראלית ביותר את משקלן של{" "}
              {num(peak.likes + 1)} תגובות, וכתבה שלמה הייתה נקבעת בשורה אחת.
              הלוגריתם מקצץ אותה ל־{peak.weight.toFixed(3)}.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          w && c
            ? `${num(w.inert)} מתוך ${num(c.total)} התגובות מקבלות משקל 1.000`
            : "כיסוי הלייקים"
        }
        hint="מה שכל ערוץ בוחר לחשוף"
      >
        {w && g && ctrl ? (
          <div className="flex flex-col gap-2.5">
            <table className="w-full text-[15px]">
              <thead>
                <tr className="text-[13.5px] text-[var(--dk-ink-3)]">
                  <th className="pb-1 text-right font-medium">ערוץ</th>
                  <th className="pb-1 text-right font-medium">תגובות</th>
                  <th className="pb-1 text-right font-medium">לייקים</th>
                  <th className="pb-1 text-right font-medium">משקל = 1</th>
                  <th className="pb-1 text-right font-medium">שינוי ב-p85</th>
                </tr>
              </thead>
              <tbody>
                {w.per_source.map((s) => (
                  <tr
                    key={s.source}
                    className="border-t border-[var(--dk-border)]/60"
                  >
                    <td className="py-1 font-semibold">{s.source_he}</td>
                    <td className="py-1 font-mono text-[14px]" dir="ltr">
                      {num(s.comments)}
                    </td>
                    <td
                      className={`py-1 font-mono text-[14px] ${s.likes === 0 ? "text-[var(--dk-bad)]" : "text-[var(--dk-ink-2)]"}`}
                      dir="ltr"
                    >
                      {num(s.likes)}
                    </td>
                    <td
                      className={`py-1 font-mono text-[14px] ${s.inert === s.comments ? "text-[var(--dk-bad)]" : "text-[var(--dk-ink-2)]"}`}
                      dir="ltr"
                    >
                      {share(s.inert, s.comments)}
                    </td>
                    <td className="py-1 font-mono text-[14px]" dir="ltr">
                      {s.mean_p85_shift === 0
                        ? "0.00000"
                        : s.mean_p85_shift.toFixed(5)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              {noLikes.map((s) => s.source_he).join(" ו-")} לא חושפים ספירת
              לייקים, ולכן {num(noLikeComments)} תגובות ב־{num(noLikeArticles)}{" "}
              כתבות אינן ניתנות לשקלול כלל.
            </p>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              היכן שיש לייקים ההזזה הממוצעת ב-p85 היא{" "}
              <span className="font-mono" dir="ltr">
                {w.shift_p85.toFixed(5)}
              </span>{" "}
              על סקאלה שהחציון שלה{" "}
              <span className="font-mono" dir="ltr">
                {g.p85_median.toFixed(4)}
              </span>
              , וב־{w.articles_unaffected} מתוך {w.articles} כתבות היא אפס.
            </p>
            <Caveat>
              השקלול נשאר כי הוא נכון עקרונית ועובד היכן שיש נתונים, לא כי הוא
              מכריע. כל מסקנה על ערוץ חייבת לעמוד גם בלעדיו.
            </Caveat>
            <Caveat>
              מדד המחלוקת{" "}
              <code dir="ltr" className="font-mono text-[14px]">
                4p(1−p)
              </code>{" "}
              חי בקוד בלי נתונים: אף ערוץ לא חושף דיסלייקים, ולכן{" "}
              <code dir="ltr" className="font-mono text-[14px]">
                p
              </code>{" "}
              תמיד 1 והתוצאה{" "}
              <span className="font-mono">{ctrl.at_one_like.toFixed(1)}</span> ב-
              {ctrl.articles} הכתבות — {ctrl.nonzero} מהן חורגות מאפס. בחלוקה
              שווה הוא היה מגיע ל-
              <span className="font-mono">{ctrl.at_even_split.toFixed(1)}</span>.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

/* ── 3. the percentile reads the tail the mean dilutes ──────────── */

function Tail({ facts }: Props) {
  const a = facts?.audience;
  const g = a?.aggregate;
  const c = a?.comments;
  const e = a?.example;
  const q = a?.quantile;
  // The claim in the title: the same comments, read two ways, two medians.
  const factor =
    g && g.mean_median > 0 ? (g.p85_median / g.mean_median).toFixed(1) : null;
  const top = e?.comments[0];
  const carrying = e?.comments.filter((x) => x.polar > 0) ?? [];
  const hits = Array.from(new Set(carrying.flatMap((x) => x.hits))).map(
    (x) => `״${x}״`,
  );
  const last = e ? e.walk[e.walk.length - 2] : undefined;

  return (
    <Stage cols="grid-cols-[45%_1fr]">
      <Panel
        title={
          q !== undefined && factor
            ? `חציון אחוזון ${qLabel(q)} גדול פי ${factor} מחציון הממוצע`
            : "ממוצע מול אחוזון"
        }
        hint={
          g
            ? `חציון ${g.counts.median} תגובות לכתבה · ${num(g.counts.total)} כתבות`
            : undefined
        }
      >
        {g && c && q !== undefined ? (
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-2.5">
              <MetricCard
                name="ממוצע הקהל"
                field="audience_mean"
                formula="Σ(ratio·w) / Σw"
                range="[0, 1]"
                reads={[
                  { value: "0.00", means: "אף תגובה לא נגעה במילון" },
                  { value: "0.10", means: "דיון טעון לאורך כל התגובות" },
                ]}
                measured={`חציון ${g.mean_median.toFixed(4)}`}
              />
              <MetricCard
                name={`אחוזון ${qLabel(q)}`}
                field="audience_p85"
                formula={`quantile(ratio, w, ${q})`}
                range="[0, 1]"
                reads={[
                  { value: "0.00", means: "גם הקצה נקי ממילים טעונות" },
                  { value: "1.00", means: "הקצה כולו מילים מהמילון" },
                ]}
                measured={`חציון ${g.p85_median.toFixed(4)} · ${g.p85_zero} כתבות ב-0, ${g.p85_one} ב-1`}
              />
            </div>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              {num(c.zero_polar)} התגובות שקיבלו 0 גוררות את הממוצע מטה, והוא
              מודד בעיקר כמה קוראים לא אמרו כלום. אחוזון {qLabel(q)} — הערך
              ש-{qLabel(q)}% מהמשקל מתחתיו — שואל כמה טעון הקצה של הדיון.
            </p>
            <Caveat>
              אחוזון {qLabel(q)} על 4 תגובות הוא התגובה השנייה מלמעלה, ולא אומד
              של דבר. {g.counts.under_5} כתבות עם פחות מ-5 תגובות ו-
              {g.counts.under_10} עם פחות מ-10 נספרות ככל השאר.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          e
            ? `${e.comments.length} תגובות, ${carrying.length} מהן מחזיקות את הציון`
            : "דוגמה מעובדת"
        }
        hint={e ? `${e.source_he} · ${e.title}` : undefined}
      >
        {e && q !== undefined && top && last ? (
          <div className="flex flex-col gap-2.5">
            <p className="text-[14px] text-[var(--dk-ink-3)]">
              היעד:{" "}
              <span dir="ltr" className="font-mono">
                {q} × {e.sum_weight} = {e.target}
              </span>
            </p>
            <div className="flex flex-col gap-1">
              {e.walk.map((s, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-2 rounded-md px-2 py-0.5 text-[14px] ${
                    s.hit
                      ? "border border-[var(--dk-accent)]/55 bg-[var(--dk-accent-dim)]"
                      : ""
                  }`}
                  dir="ltr"
                >
                  <span className="w-[54px] font-mono text-[var(--dk-ink)]">
                    {s.value.toFixed(4)}
                  </span>
                  <span className="w-[52px] font-mono text-[var(--dk-ink-3)]">
                    +{s.weight.toFixed(3)}
                  </span>
                  <span
                    className={`w-[62px] font-mono ${s.cum >= e.target ? "text-[var(--dk-accent)]" : "text-[var(--dk-ink-2)]"}`}
                  >
                    {s.cum.toFixed(3)}
                  </span>
                  {s.hit && (
                    <span className="text-[13px] font-semibold text-[var(--dk-accent)]">
                      ← ‏p85
                    </span>
                  )}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              <Big
                value={e.weighted.p85.toFixed(4)}
                label={`audience_p85 · בלי משקלים ${e.unweighted.p85.toFixed(4)}`}
                tone="accent"
              />
              <Big
                value={e.weighted.mean.toFixed(4)}
                label={`audience_mean · בלי משקלים ${e.unweighted.mean.toFixed(4)}`}
                tone="good"
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              המשקל המצטבר עצר על{" "}
              <span className="font-mono" dir="ltr">
                {last.cum.toFixed(3)}
              </span>{" "}
              מול יעד{" "}
              <span className="font-mono" dir="ltr">
                {e.target}
              </span>
              . פער של פחות מעשירית משקל הזיז את התוצאה מ-
              <span className="font-mono" dir="ltr">
                {last.value.toFixed(4)}
              </span>{" "}
              ל-
              <span className="font-mono" dir="ltr">
                {e.weighted.p85.toFixed(4)}
              </span>
              .
            </p>
            <Caveat>
              התגובה הכי אהודה כאן —{" "}
              <span className="font-semibold">
                &quot;{top.text.slice(0, 46)}…&quot;
              </span>{" "}
              עם {top.likes} לייקים — מקבלת{" "}
              <span className="font-mono" dir="ltr">
                {top.ratio.toFixed(4)}
              </span>
              . המילון לא מכיר אף אחת מ-{top.len} מילותיה, וכל האות פה נשען על{" "}
              {carrying.length} תגובות שכללו את {hits.join(" ו")}.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

/* ── 4. what the number is allowed to say ───────────────────────── */

function Limits({ facts }: Props) {
  const a = facts?.audience;
  const c = a?.comments;
  const h = a?.hijack;
  const q = a?.quantile;
  const maxPair = Math.max(1, ...(h?.pairs.map((p) => p.n) ?? [1]));

  return (
    <Stage cols="grid-cols-[52%_1fr]">
      <Panel
        title={
          h
            ? `ב-${h.hijacked} מתוך ${h.comparable} הגרסאות התגובות נפלו בקטגוריה אחרת`
            : "נושא הכתבה מול נושא התגובות"
        }
        hint={h ? `${h.events} אירועים · לקסיקון שבע הקטגוריות` : undefined}
      >
        {h ? (
          <div className="flex flex-col gap-2.5">
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              נושא הכתבה נמדד מהטקסט, נושא התגובות מכל התגובות יחד, ושניהם באותו
              מילון.
            </p>
            <div className="flex flex-col gap-1.5">
              {h.pairs.map((p) => (
                <div
                  key={`${p.article_he}-${p.comments_he}`}
                  className="flex items-center gap-2.5"
                >
                  <span className="w-[150px] shrink-0 text-[14.5px]">
                    {p.article_he} ← {p.comments_he}
                  </span>
                  <div className="h-4 flex-1 overflow-hidden rounded-md bg-[var(--dk-surface-2)]">
                    <div
                      className="h-full rounded-md bg-[var(--dk-accent)]"
                      style={{ width: `${(p.n / maxPair) * 100}%` }}
                    />
                  </div>
                  <span
                    dir="ltr"
                    className="w-[26px] shrink-0 text-left font-mono text-[13.5px] text-[var(--dk-ink-2)]"
                  >
                    {p.n}
                  </span>
                </div>
              ))}
            </div>
            {h.examples.slice(0, 2).map((x) => (
              <div
                key={x.title}
                className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-2.5"
              >
                <div className="flex items-baseline gap-2">
                  <Chip tone="neutral">{x.article_he}</Chip>
                  <span className="text-[var(--dk-ink-3)]">←</span>
                  <Chip tone="accent">{x.comments_he}</Chip>
                  <span className="text-[13px] text-[var(--dk-ink-3)]">
                    {x.source_he} · {x.num_comments} תגובות
                  </span>
                </div>
                <div className="mt-1 text-[15px] font-semibold leading-snug">
                  {x.title}
                </div>
                <div className="mt-1 text-[14px] leading-snug text-[var(--dk-ink-2)]">
                  <span className="text-[var(--dk-ink-3)]">
                    התגובה המובילה ({x.top_likes} לייקים):{" "}
                  </span>
                  {x.top_comment.split("\n")[0].slice(0, 96)}
                </div>
              </div>
            ))}
            <Caveat>
              מילון הכתבות נבנה לטקסט עיתונאי ומופעל כאן על שפת דיבור — שימוש
              מחוץ להגדרה המקורית. הפער תיאורי: הוא לא אומר שהכתבה הסיטה את
              הדיון.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="הטבלה לא שומרת מי כתב ומתי">
        {c && q !== undefined ? (
          <div className="flex flex-col gap-2.5">
            <CodeRef path="comments(comment_id, article_id, source, text, like_count)" />
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              {num(c.total)} תגובות ב-{num(c.articles)} כתבות, וזו כל הטבלה. אין
              זהות מגיב ואין חותמת זמן — החלטה מה-RFC, לא חוסר.
            </p>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              היא שוללת מראש פרופיל של אדם, ושוללת גם ניתוח לגיטימי כמו התפתחות
              הדיון לאורך היום. ויתרנו על השני כדי למנוע את הראשון.
            </p>
            <Caveat>
              אחוזון {qLabel(q)} של כתבה לא מוצג לבדו: כל השוואה בין ערוצים רצה
              מול חציון האירוע. ממוצע גולמי לערוץ מודד אילו סיפורים הוא בחר
              לסקר, לא איך סיקר אותם.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}
