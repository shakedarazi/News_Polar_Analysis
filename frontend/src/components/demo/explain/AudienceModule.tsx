"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import {
  BarRow,
  Chip,
  CodeRef,
  MetricCard,
  Panel,
  Stage,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "one", label_he: "איך נמדדת תגובה אחת" },
  { id: "article", label_he: "מה הקהל אומר על הכתבה" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the audience signal — the only input the pipeline does not control.
 *
 * Two tabs, four panels. First what a single comment scores: a share rather
 * than a count, and the price of that denominator; then the distribution that
 * bounds the whole signal, and the four columns the table is allowed to hold.
 * Then the article-level reading: the 85th percentile rather than the mean,
 * because three quarters of the comments score zero — and the second question
 * the same comments answer, which topic they drifted to.
 *
 * Dropped on purpose (see demo/README.md items 22-26, 58): the weighted-
 * quantile walk (mechanism — the claim it carried now lives in the sentences
 * of both tabs), the per-source likes table, and `controversy = 4p(1−p)`,
 * whose entire content was the absence of dislike data anywhere in the corpus.
 */
export function AudienceModule({ facts }: Props) {
  const [tab, setTab] = useState("one");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "one" && <OneComment facts={facts} />}
      {tab === "article" && <ArticleScore facts={facts} />}
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
        className={`text-[38px] font-black leading-[1.1] ${colors[tone]}`}
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

function Missing() {
  return (
    <p className="text-[15px] text-[var(--dk-ink-3)]">
      אין קובץ מדידות — הדיאגרמות מוצגות בלי המספרים.
    </p>
  );
}

/* ── 1. one comment: a share, not a count ───────────────────────── */

function OneComment({ facts }: Props) {
  const a = facts?.audience;
  const c = a?.comments;
  const art = a?.artifacts;
  const maxRatio = Math.max(1, ...(c?.ratio_hist.map((b) => b.n) ?? [1]));

  return (
    <Stage cols="grid-cols-[47%_1fr]">
      <Panel
        title={
          c
            ? `תגובה בת ${c.len_max} מילים לא אמורה לגבור על שורה אחת חדה`
            : "שיעור, לא ספירה"
        }
      >
        {c && a && art ? (
          <div className="flex flex-col gap-4">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              מה שרוצים לדעת על דיון הוא כמה הוא טעון: כמה מהנאמר בו הוא כעס,
              האשמה, זלזול או שבח. המערכת מזהה את המילים האלה מול רשימה שנבנתה
              מראש, {num(a.polar_lexicon_forms)} צורות. ספירה שלהן הייתה מודדת
              גם אורך — תגובה ארוכה תמיד צוברת יותר.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              לכן הציון הוא שיעור: כמה מהמילים בתגובה טעונות, מתוך כל מילותיה.
              שורה בת חמש מילים ותגובה בת {c.len_max} נמדדות באותה סקאלה.
            </p>
            <MetricCard
              name="שיעור המילים הטעונות בתגובה"
              field="polar_ratio"
              formula="polar_count / max(1, comment_len)"
              range="0 – 1"
              reads={[
                { value: "0.00", means: "אף מילה בתגובה אינה ברשימה" },
                { value: "0.05", means: "מילה טעונה אחת לכל עשרים מילים" },
                { value: "1.00", means: "כל מילה בתגובה טעונה" },
              ]}
              measured={`ממוצע ${c.ratio_mean.toFixed(4)} · אורך חציוני ${c.len_median} מילים`}
            />
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              המחיר של שיעור הוא מכנה קטן: תגובה בת מילה אחת טעונה מקבלת 1.00,
              הציון הגבוה ביותר שיש. ‏{num(art.ratio_one)} מ־{num(c.total)}{" "}
              התגובות הגיעו לשם, {num(art.single_token)} מהן במילה אחת.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {art.examples.slice(0, 5).map((x, i) => (
                <span
                  key={`${x.text}-${i}`}
                  className="rounded-lg border border-[var(--dk-bad)]/40 bg-[var(--dk-bad)]/8 px-2.5 py-1 text-[16px]"
                >
                  {x.text}
                  <span
                    className="ms-1.5 font-mono text-[13px] text-[var(--dk-ink-3)]"
                    dir="ltr"
                  >
                    {x.likes}♥
                  </span>
                </span>
              ))}
            </div>
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
        hint={c ? `${num(c.articles)} כתבות` : undefined}
      >
        {c ? (
          <div className="flex flex-col gap-3.5">
            <div className="flex flex-col gap-2">
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
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              שיעור המילים הטעונות בתגובה: ‏0 = אף מילה מהרשימה, ‏1 = כל מילה
              בתגובה. השורה העליונה היא התגובות שקיבלו 0 בדיוק.
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              <Big
                value={share(c.zero_polar, c.total)}
                label="מהתגובות בלי אף מילה מהרשימה"
                tone="warn"
              />
              <Big
                value={num(c.len_under_4)}
                label="תגובות באורך שלוש מילים או פחות"
                tone="accent"
              />
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              האות נשען על מיעוט התגובות. הרשימה סופרת מילים מוכרות ולא כעס:
              תגובה זועמת שנוסחה במילים שאינן בה מקבלת 0, ולכן כל טענה כאן היא
              על מה שנאמר במפורש.
            </p>
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
    </Stage>
  );
}

/* ── 2. the article: the loud edge, and what it drifted to ──────── */

function ArticleScore({ facts }: Props) {
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
  const maxPair = Math.max(1, ...(h?.pairs.map((p) => p.n) ?? [1]));

  return (
    <Stage cols="grid-cols-[48%_1fr]">
      <Panel
        title="הממוצע מודד בעיקר כמה קוראים לא אמרו כלום"
        hint={
          g ? `חציון ${g.counts.median} תגובות לכתבה · ${num(g.counts.total)} כתבות` : undefined
        }
      >
        {g && c && w && peak && q !== undefined && factor ? (
          <div className="flex flex-col gap-4">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              עכשיו צריך להפוך את התגובות של כתבה למספר אחד. ממוצע הוא הבחירה
              המתבקשת והוא הלא נכונה כאן: {share(c.zero_polar, c.total)}{" "}
              מהתגובות מקבלות 0, והן גוררות כל ממוצע אל השקט.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              לכן הקריאה היא אחוזון {qLabel(q)} — הערך שמתחתיו נמצאות{" "}
              {qLabel(q)}% מהתגובות. הוא שואל כמה טעון הקצה הקולני של הדיון,
              ולא כמה שקט הרוב. אותן תגובות, שתי קריאות, פי {factor}.
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
                  { value: "1.00", means: "הקצה כולו מילים מהרשימה" },
                ]}
                measured={`חציון ${g.p85_median.toFixed(4)} · ${g.p85_zero} כתבות ב־0`}
              />
              <MetricCard
                name="ממוצע הקהל"
                field="audience_mean"
                formula="Σ(ratio·w) / Σw"
                range="0 – 1"
                reads={[
                  { value: "0.00", means: "אף תגובה לא נגעה ברשימה" },
                  { value: "0.02", means: "החציון בסנאפשוט" },
                  { value: "0.10", means: "דיון טעון לאורך כל התגובות" },
                ]}
                measured={`חציון ${g.mean_median.toFixed(4)}`}
              />
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              בתוך שתי הקריאות תגובה אהודה שוקלת יותר, לפי{" "}
              <code dir="ltr" className="font-mono text-[16px]">
                1 + ln(1 + likes)
              </code>
              : התגובה עם {num(peak.likes)} לייקים שוקלת{" "}
              {peak.weight.toFixed(1)} ולא {num(peak.likes + 1)}, ולכן שורה
              ויראלית אחת לא קובעת כתבה שלמה.
            </p>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              ‏{noLikes.map((s) => s.source_he).join(" ו־")} לא חושפים ספירת
              לייקים, ולכן {num(noLikeComments)} תגובות נכנסות במשקל שווה. היכן
              שיש לייקים ההזזה הממוצעת באחוזון {qLabel(q)} היא{" "}
              {w.shift_p85.toFixed(5)} על סקאלה שהחציון שלה{" "}
              {g.p85_median.toFixed(4)} — כל מסקנה על ערוץ עומדת גם בלי השקלול.
              ב־{g.counts.under_5} מ־{num(g.counts.total)} הכתבות יש פחות מחמש
              תגובות, ושם אחוזון {qLabel(q)} הוא התגובה השנייה מלמעלה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          h
            ? `ב־${h.hijacked} מ־${h.comparable} הכתבות הקהל דיבר על נושא אחר`
            : "נושא הכתבה מול נושא התגובות"
        }
        hint={h ? `${h.events} אירועים · שבע קטגוריות נושא` : undefined}
      >
        {h ? (
          <div className="flex flex-col gap-3.5">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              אותן תגובות נקראות פעם שנייה, בשאלה אחרת: על מה הן מדברות. נושא
              הכתבה נמדד מהטקסט שלה, נושא התגובות מכל התגובות יחד, ושניהם באותו
              מילון של שבע קטגוריות — מילון שנבנה לטקסט עיתונאי ומופעל כאן גם על
              שפת דיבור.
            </p>
            <div className="flex flex-col gap-2">
              {h.pairs.map((p) => (
                <div
                  key={`${p.article_he}-${p.comments_he}`}
                  className="flex items-center gap-2.5"
                >
                  <span className="w-[150px] shrink-0 text-[15.5px]">
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
                    className="w-[26px] shrink-0 text-left font-mono text-[14px] text-[var(--dk-ink-2)]"
                  >
                    {p.n}
                  </span>
                </div>
              ))}
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              נושא הכתבה ← הנושא שאליו נפלו התגובות, וכמה כתבות בכל צירוף. אלה
              ששת הצירופים הנפוצים מתוך {h.hijacked}.
            </p>
            {h.examples.slice(0, 2).map((x) => (
              <div
                key={x.title}
                className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-3"
              >
                <div className="flex items-baseline gap-2">
                  <Chip tone="neutral">{x.article_he}</Chip>
                  <span className="text-[var(--dk-ink-3)]">←</span>
                  <Chip tone="accent">{x.comments_he}</Chip>
                  <span className="text-[13px] text-[var(--dk-ink-3)]">
                    {x.source_he} · {x.num_comments} תגובות
                  </span>
                </div>
                <div className="mt-1 text-[15.5px] font-semibold leading-snug">
                  {x.title}
                </div>
                <div className="mt-1 text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
                  <span className="text-[var(--dk-ink-3)]">
                    התגובה המובילה ({x.top_likes} לייקים):{" "}
                  </span>
                  {x.top_comment.split("\n")[0].slice(0, 96)}
                </div>
              </div>
            ))}
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              את זה אפשר לראות רק כשמודדים את הקהל בנפרד מהכתבה. הפער תיאורי:
              הוא מראה לאן הלך הדיון, ולא טוען שהכתבה הסיטה אותו.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}
