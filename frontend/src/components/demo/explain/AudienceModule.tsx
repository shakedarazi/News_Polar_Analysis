"use client";

import { useState } from "react";
import type { AudienceComment, Facts } from "./facts";
import {
  BarRow,
  Caveat,
  Chip,
  CodeRef,
  MetricCard,
  Node,
  Panel,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "comment", label_he: "מה נמדד בתגובה" },
  { id: "weight", label_he: "משקל המעורבות" },
  { id: "aggregate", label_he: "ממוצע ואחוזון 85" },
  { id: "walk", label_he: "מאמר אחד, צעד־צעד" },
  { id: "hijack", label_he: "חטיפת נושא" },
  { id: "limits", label_he: "מה זה לא מודד" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the audience signal — the only input the pipeline does not control.
 *
 * Every other layer works on text we fetched and rules we wrote. Here the
 * data is whatever each outlet's comment widget happens to expose, and two of
 * the four outlets expose no like counts at all. So the module spends as much
 * time on coverage as on formulas: a weighting that is inert for 14,405 of
 * 38,492 comments, and a controversy metric the code computes on every comment
 * and that is identically zero because nobody ships a dislike count.
 */
export function AudienceModule({ facts }: Props) {
  const [tab, setTab] = useState("comment");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "comment" && <PerComment facts={facts} />}
      {tab === "weight" && <Weight facts={facts} />}
      {tab === "aggregate" && <Aggregate facts={facts} />}
      {tab === "walk" && <Walk facts={facts} />}
      {tab === "hijack" && <Hijack facts={facts} />}
      {tab === "limits" && <Limits facts={facts} />}
    </div>
  );
}

function num(n: number): string {
  return n.toLocaleString("en-US");
}

function share(part: number, whole: number): string {
  return whole > 0 ? `${((part / whole) * 100).toFixed(1)}%` : "—";
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

/* ── 1. what is measured inside one comment ─────────────────────── */

function PerComment({ facts }: Props) {
  const a = facts?.audience;
  const c = a?.comments;
  const maxRatio = Math.max(1, ...(c?.ratio_hist.map((b) => b.n) ?? [1]));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[47%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="תגובה נכנסת, מספר אחד יוצא"
          hint="src/analysis/comments_scoring.py"
        >
          <div className="flex flex-col gap-2">
            <div className="flex items-stretch gap-2">
              <Node
                title="נרמול"
                sub="ניקוד, גרשיים, רווחים"
                tone="neutral"
                wide
              />
              <Node title="טוקניזציה" sub="מילים עבריות" tone="neutral" wide />
              <Node
                title="חיפוש במילון"
                sub={
                  a ? `${num(a.polar_lexicon_forms)} צורות` : "מילון קיטוב"
                }
                tone="accent"
                wide
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              אותה שיטה בדיוק כמו בכתבות: מילון שהורחב פעם אחת מראש, וחיפוש ישיר
              בזמן ריצה. אין גזירת שורש, אין מודל, אין ניקוד רגש — רק ספירה של
              כמה מהמילים בתגובה נמצאות ברשימה.
            </p>
          </div>
        </Panel>

        <Panel title="הציון">
          <MetricCard
            name="שיעור מילים טעונות"
            field="polar_ratio"
            formula="polar_count / max(1, comment_len)"
            range="[0, 1]"
            reads={[
              { value: "0.00", means: "אף מילה בתגובה לא נמצאת במילון הקיטוב" },
              {
                value: "0.05",
                means: "מילה טעונה אחת בערך לכל 20 מילים — סביב החציון של מאמר",
              },
              {
                value: "1.00",
                means:
                  "כל מילה בתגובה טעונה. בפועל זה כמעט תמיד תגובה בת מילה אחת",
              },
            ]}
            measured={
              c
                ? `ממוצע ${c.ratio_mean.toFixed(4)} · אורך חציוני ${c.len_median} טוקנים · הארוכה ביותר ${c.len_max}`
                : undefined
            }
          />
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="ההתפלגות האמיתית"
          hint={c ? `${num(c.total)} תגובות · ${num(c.articles)} כתבות` : undefined}
        >
          {c ? (
            <div className="flex flex-col gap-1.5">
              {c.ratio_hist.map((b) => (
                <div key={b.label} className="flex-1">
                  <BarRow
                    label={b.label}
                    n={b.n}
                    max={maxRatio}
                    tone={b.label === "0" ? "muted" : "accent"}
                  />
                </div>
              ))}
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="מה זה אומר">
          {c ? (
            <div className="flex flex-col gap-2.5">
              <div className="grid grid-cols-2 gap-2.5">
                <Big
                  value={share(c.zero_polar, c.total)}
                  label={`${num(c.zero_polar)} תגובות מקבלות בדיוק 0`}
                  tone="warn"
                />
                <Big
                  value={num(c.len_under_4)}
                  label="תגובות באורך 3 טוקנים או פחות"
                  tone="accent"
                />
              </div>
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                שלושה רבעים מהתגובות אינן תורמות דבר לאות. זו לא תקלה — מילון
                הקיטוב מכיל אלפי צורות ספורות, והשפה של תגובה ממוצעת פשוט לא
                נמצאת בהן. המשמעות המעשית: האות נשען על מיעוט התגובות שכן פגעו
                במילון, ולכן הוא רגיש הרבה יותר לרעש ממה שהגודל של{" "}
                {num(c.total)} תגובות מרמז.
              </p>
              <Caveat>
                זה מודד <b>שכיחות מילים מרשימה</b>, לא כעס. תגובה זועמת שכתובה
                במילים שלא נמצאות במילון תקבל 0, ותגובה עניינית שמשתמשת במילה
                אחת מהרשימה תקבל ציון חיובי. בלשונית &quot;מאמר אחד&quot; יש דוגמה
                מדודה בדיוק לזה.
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

/* ── 2. the engagement weight, and where it is inert ────────────── */

function Weight({ facts }: Props) {
  const w = facts?.audience.weight;
  const ctrl = facts?.audience.controversy;
  const noLikes = w?.per_source.filter((s) => s.likes === 0) ?? [];
  const noLikeComments = noLikes.reduce((t, s) => t + s.comments, 0);
  const noLikeArticles = noLikes.reduce((t, s) => t + s.articles, 0);

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[44%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="השקלול" hint="src/analysis/comments_scoring.py">
          <MetricCard
            name="משקל מעורבות"
            field="engagement_weight"
            formula="1 + ln(1 + likes + dislikes)"
            range="[1, ∞)"
            reads={[
              { value: "1.000", means: "תגובה בלי אף לייק — המשקל המינימלי" },
              {
                value: "3.398",
                means: "עשרה לייקים שווים פי 3.4 מתגובה בלי לייקים, לא פי 10",
              },
              {
                value: "8.511",
                means: `הלייקים הרבים ביותר בסנאפשוט (${num(w?.max_likes ?? 0)})`,
              },
            ]}
            measured="הלוגריתם הוא הבחירה: תגובה ויראלית לא בולעת את כל הכתבה"
          />
        </Panel>

        <Panel title="עקומת המשקל" hint="מול החלופה הליניארית">
          {w ? (
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
          ) : (
            <Missing />
          )}
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="הבעיה: חצי מהתגובות לא נושאות לייקים"
          hint="מה שכל ערוץ בוחר לחשוף"
        >
          {w ? (
            <div className="flex flex-col gap-2">
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
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                {noLikes.map((s) => s.source_he).join(" ו-")} לא חושפים ספירת
                לייקים בכלל, כך שכל {num(noLikeComments)} התגובות שלהם מקבלות
                משקל 1.000. עבור {num(noLikeArticles)} כתבות השקלול לא יכול
                לשנות דבר — וזה נמדד: השינוי המוחלט הממוצע שם הוא בדיוק אפס.
              </p>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="וגם איפה שיש לייקים — כמה זה בכלל מזיז">
          {w && ctrl ? (
            <div className="flex flex-col gap-2.5">
              <div className="grid grid-cols-3 gap-2.5">
                <Big
                  value={w.shift_p85.toFixed(5)}
                  label="שינוי ממוצע ב-p85 מול אותו אומד בלי משקלים"
                  tone="accent"
                />
                <Big
                  value={`${w.articles_unaffected}/${w.articles}`}
                  label="כתבות שבהן השקלול לא שינה את p85 כלל"
                  tone="warn"
                />
                <Big
                  value={`${ctrl.nonzero}/${ctrl.articles}`}
                  label="כתבות עם מדד מחלוקת שאינו אפס"
                  tone="bad"
                />
              </div>
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                הצינור מחשב לכל תגובה גם{" "}
                <code dir="ltr" className="font-mono text-[14px]">
                  controversy = 4p(1−p)
                </code>{" "}
                כאשר{" "}
                <code dir="ltr" className="font-mono text-[14px]">
                  p = likes / (likes + dislikes)
                </code>
                . אף אחד מהערוצים לא חושף דיסלייקים, ולכן{" "}
                <code dir="ltr" className="font-mono text-[14px]">
                  p
                </code>{" "}
                תמיד 1 והמדד תמיד{" "}
                <span className="font-mono">{ctrl.at_one_like.toFixed(1)}</span>
                . זה מדד חי בקוד בלי נתונים מאחוריו — הוא היה מגיע ל-
                <span className="font-mono">
                  {ctrl.at_even_split.toFixed(1)}
                </span>{" "}
                בחלוקה שווה, אם רק היה מי שיספק אותה.
              </p>
              <Caveat>
                השקלול אמיתי אבל קטן. הוא נשאר כי הוא נכון עקרונית ועובד היכן
                שיש נתונים, לא כי הוא מזיז את התוצאה — וכל מסקנה על ערוץ חייבת
                לעמוד גם בלעדיו.
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

/* ── 3. from comments to one number per article ─────────────────── */

function Aggregate({ facts }: Props) {
  const a = facts?.audience;
  const g = a?.aggregate;
  const maxP85 = Math.max(1, ...(g?.p85_hist.map((b) => b.n) ?? [1]));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[47%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="שני מספרים לכל כתבה" hint="src/analysis/aggregation.py">
          <div className="grid grid-cols-2 gap-2.5">
            <MetricCard
              name="ממוצע הקהל"
              field="audience_mean"
              formula="Σ(ratio·w) / Σw"
              range="[0, 1]"
              reads={[
                { value: "0.02", means: "החציון בסנאפשוט — הטון הכללי" },
                { value: "0.10", means: "דיון טעון לאורך כל התגובות" },
              ]}
              measured={g ? `חציון ${g.mean_median.toFixed(4)}` : undefined}
            />
            <MetricCard
              name="אחוזון 85"
              field="audience_p85"
              formula="quantile(ratio, w, 0.85)"
              range="[0, 1]"
              reads={[
                { value: "0.00", means: "גם הזנב העליון נקי ממילים טעונות" },
                { value: "0.06", means: "החציון בסנאפשוט" },
                { value: "1.00", means: "כמעט תמיד עיוות של תגובה קצרה" },
              ]}
              measured={
                g
                  ? `חציון ${g.p85_median.toFixed(4)} · ${g.p85_zero} כתבות ב-0`
                  : undefined
              }
            />
          </div>
        </Panel>

        <Panel title="למה אחוזון ולא רק ממוצע">
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            הממוצע נגרר כלפי מטה על ידי הרוב הדומם: ברגע ש-76% מהתגובות מקבלות 0,
            הממוצע מודד בעיקר <b>כמה אנשים לא אמרו כלום מעניין</b>. אחוזון 85
            שואל שאלה אחרת — כמה טעון הוא <b>הקצה</b> של הדיון, אחרי שמסדרים את
            התגובות מהרגועה לטעונה וצועדים 85% מהמשקל פנימה. את ההצדקה הזו אפשר
            לראות במספרים: החציון של הממוצע הוא{" "}
            <span className="font-mono" dir="ltr">
              {g?.mean_median.toFixed(4) ?? "—"}
            </span>{" "}
            ושל האחוזון{" "}
            <span className="font-mono" dir="ltr">
              {g?.p85_median.toFixed(4) ?? "—"}
            </span>{" "}
            — פי שניים ויותר, על אותן תגובות בדיוק.
          </p>
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="אחוזון 85 על פני הכתבות"
          hint={g ? `${num(g.counts.total)} כתבות עם תגובות` : undefined}
        >
          {g ? (
            <div className="flex flex-col gap-1.5">
              {g.p85_hist.map((b) => (
                <div key={b.label} className="flex-1">
                  <BarRow
                    label={b.label}
                    n={b.n}
                    max={maxP85}
                    tone={b.label === "0" ? "muted" : "accent"}
                  />
                </div>
              ))}
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="כמה תגובות עומדות מאחורי מספר">
          {g ? (
            <div className="flex flex-col gap-2.5">
              <div className="grid grid-cols-3 gap-2.5">
                <Big
                  value={num(g.counts.median)}
                  label="תגובות בכתבה חציונית"
                  tone="good"
                />
                <Big
                  value={num(g.counts.under_10)}
                  label="כתבות עם פחות מ-10 תגובות"
                  tone="warn"
                />
                <Big
                  value={num(g.counts.under_5)}
                  label="כתבות עם פחות מ-5 תגובות"
                  tone="bad"
                />
              </div>
              <Caveat>
                אחוזון 85 על 4 תגובות הוא פשוט התגובה השנייה מלמעלה. המספר
                מחושב שם באותה נוסחה, אבל הוא לא אומד של שום דבר —{" "}
                {num(g.counts.under_5)} כתבות בסנאפשוט נמצאות במצב הזה, והן
                נספרות ככל השאר.
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

/* ── 4. one article, end to end ─────────────────────────────────── */

function CommentRow({ c }: { c: AudienceComment }) {
  return (
    <tr className="border-t border-[var(--dk-border)]/60 align-top">
      <td className="py-1 font-mono text-[13.5px] text-[var(--dk-ink-3)]" dir="ltr">
        {c.likes}
      </td>
      <td className="py-1 pe-2 text-[14px] leading-snug">
        <span className={c.polar === 0 ? "text-[var(--dk-ink-3)]" : ""}>
          {c.text.length > 62 ? `${c.text.slice(0, 62)}…` : c.text}
        </span>
        {c.hits.length > 0 && (
          <span className="ms-1 whitespace-nowrap">
            {c.hits.map((h) => (
              <span
                key={h}
                className="ms-1 rounded bg-[var(--dk-accent-dim)] px-1 font-semibold text-[var(--dk-accent)]"
              >
                {h}
              </span>
            ))}
          </span>
        )}
      </td>
      <td className="py-1 font-mono text-[13.5px] text-[var(--dk-ink-3)]" dir="ltr">
        {c.polar}/{c.len}
      </td>
      <td
        className={`py-1 font-mono text-[13.5px] ${c.ratio === 0 ? "text-[var(--dk-ink-3)]" : "text-[var(--dk-accent)]"}`}
        dir="ltr"
      >
        {c.ratio.toFixed(4)}
      </td>
      <td className="py-1 font-mono text-[13.5px] text-[var(--dk-ink-2)]" dir="ltr">
        {c.weight.toFixed(3)}
      </td>
    </tr>
  );
}

function Walk({ facts }: Props) {
  const e = facts?.audience.example;
  const q = facts?.audience.quantile ?? 0.85;

  if (!e) {
    return (
      <div className="grid min-h-0 flex-1 place-items-center">
        <Missing />
      </div>
    );
  }
  const top = e.comments[0];

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[56%_1fr] gap-3">
      <Panel
        title={e.title}
        hint={`${e.source_he} · ${e.comments.length} תגובות`}
      >
        <table className="w-full">
          <thead>
            <tr className="text-[13px] text-[var(--dk-ink-3)]">
              <th className="pb-1 text-right font-medium">לייק</th>
              <th className="pb-1 text-right font-medium">תגובה</th>
              <th className="pb-1 text-right font-medium">טעון/אורך</th>
              <th className="pb-1 text-right font-medium">ratio</th>
              <th className="pb-1 text-right font-medium">משקל</th>
            </tr>
          </thead>
          <tbody>
            {e.comments.map((c, i) => (
              <CommentRow key={`${c.likes}-${i}`} c={c} />
            ))}
          </tbody>
        </table>
      </Panel>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title={`הצעידה אל אחוזון ${(q * 100).toFixed(0)}`}
          hint={`יעד: ${q} × ${e.sum_weight} = ${e.target}`}
        >
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
        </Panel>

        <Panel title="התוצאה, ומה היא לא תפסה">
          <div className="flex flex-col gap-2.5">
            <div className="grid grid-cols-2 gap-2.5">
              <Big
                value={e.weighted.p85.toFixed(4)}
                label={`audience_p85 · בלי משקלים היה ${e.unweighted.p85.toFixed(4)}`}
                tone="accent"
              />
              <Big
                value={e.weighted.mean.toFixed(4)}
                label={`audience_mean · בלי משקלים ${e.unweighted.mean.toFixed(4)}`}
                tone="good"
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              שימו לב לשורה לפני האחרונה: המשקל המצטבר עצר על{" "}
              <span className="font-mono" dir="ltr">
                {e.walk[e.walk.length - 2]?.cum.toFixed(3)}
              </span>{" "}
              מול יעד{" "}
              <span className="font-mono" dir="ltr">
                {e.target}
              </span>
              . פער של פחות מעשירית משקל אחד הוא שהזיז את התוצאה מ-
              <span className="font-mono" dir="ltr">
                {e.walk[e.walk.length - 2]?.value.toFixed(4)}
              </span>{" "}
              ל-
              <span className="font-mono" dir="ltr">
                {e.weighted.p85.toFixed(4)}
              </span>
              . על עשר תגובות, אומד אחוזון הוא שביר.
            </p>
            {top && (
              <Caveat>
                התגובה הכי אהודה כאן —{" "}
                <span className="font-semibold">
                  &quot;{top.text.slice(0, 46)}…&quot;
                </span>{" "}
                עם {top.likes} לייקים — מקבלת{" "}
                <span className="font-mono" dir="ltr">
                  0.0000
                </span>
                . אף אחת מ-{top.len} המילים שלה לא במילון. כל האות פה נשען על
                שתי תגובות שבמקרה כללו את &quot;חייבים&quot; ו&quot;בושה&quot;.
              </Caveat>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}

/* ── 5. topic hijacking ─────────────────────────────────────────── */

function Hijack({ facts }: Props) {
  const h = facts?.audience.hijack;
  const maxPair = Math.max(1, ...(h?.pairs.map((p) => p.n) ?? [1]));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[45%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="מה נמדד" hint="demo/core/framing.py · audience_hijacked">
          <div className="flex flex-col gap-2">
            <div className="flex items-stretch gap-2">
              <Node title="נושא הכתבה" sub="קטגוריית הלקסיקון הדומיננטית בטקסט" wide />
              <Node
                title="נושא התגובות"
                sub="אותו לקסיקון, על כל התגובות יחד"
                tone="accent"
                wide
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              שני הצדדים מחושבים באותו מילון קטגוריות בן שבע הקטגוריות. אם הם
              שונים, הקהל לקח את הסיפור למקום אחר מזה שהכתבה עסקה בו. זה לא
              &quot;הקוראים טועים&quot; — זה מדד לפער בין מה שהמערכת בחרה לספר
              לבין מה שהקוראים בחרו לדבר עליו.
            </p>
          </div>
        </Panel>

        <Panel title="כמה זה קורה">
          {h ? (
            <div className="flex flex-col gap-2.5">
              <Big
                value={`${h.hijacked}/${h.comparable}`}
                label={`גרסאות שבהן נושא התגובות שונה מנושא הכתבה, מתוך ${h.events} אירועים`}
                tone="warn"
              />
              <table className="w-full text-[15px]">
                <tbody>
                  {h.per_source.map((s) => (
                    <tr
                      key={s.source}
                      className="border-t border-[var(--dk-border)]/60"
                    >
                      <td className="py-1 font-semibold">{s.source_he}</td>
                      <td className="py-1 font-mono text-[14px]" dir="ltr">
                        {s.hijacked}/{s.total}
                      </td>
                      <td className="py-1 text-[13.5px] text-[var(--dk-ink-3)]">
                        {s.total < 5 ? "מדגם קטן מדי לדיווח" : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="לאן הקהל לוקח את זה" hint="הכתבה ← התגובות">
          {h ? (
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
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="דוגמאות">
          {h && h.examples.length > 0 ? (
            <div className="flex flex-col gap-2">
              {h.examples.map((x) => (
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
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>
    </div>
  );
}

/* ── 6. the limits ──────────────────────────────────────────────── */

function Limits({ facts }: Props) {
  const a = facts?.audience;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[47%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="מכנה קטן, ציון מקסימלי">
          {a ? (
            <div className="flex flex-col gap-2.5">
              <div className="grid grid-cols-2 gap-2.5">
                <Big
                  value={num(a.artifacts.ratio_one)}
                  label="תגובות עם ציון 1.0000 מדויק"
                  tone="bad"
                />
                <Big
                  value={num(a.artifacts.single_token)}
                  label="מהן בנות טוקן אחד בלבד"
                  tone="bad"
                />
              </div>
              <div className="flex flex-wrap gap-1.5">
                {a.artifacts.examples.map((x, i) => (
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
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                <code dir="ltr" className="font-mono text-[14px]">
                  max(1, len)
                </code>{" "}
                מונע חלוקה באפס אבל לא מגן מפני מכנה של 1. תגובה בת מילה אחת
                שנמצאת במילון מקבלת את הציון המקסימלי האפשרי במערכת — יותר מכל
                נאום זועם בן חמישים מילה.
              </p>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="מה לא נאסף בכוונה">
          <div className="flex flex-col gap-2">
            <CodeRef path="comments(comment_id, article_id, source, text, like_count)" />
            <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
              זו כל הטבלה. אין זהות מגיב ואין חותמת זמן לתגובה — החלטה מה-RFC
              ולא חוסר. היא שוללת מראש פרופיל של אדם, וגם שוללת ניתוחים
              לגיטימיים כמו התפתחות הדיון לאורך היום. אנחנו מוותרים על השני כדי
              למנוע את הראשון.
            </p>
          </div>
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="לאן המספר הזה בכלל הולך" hint="סטייה בתוך אירוע">
          {a ? (
            <div className="flex flex-col gap-2">
              <table className="w-full text-[15px]">
                <thead>
                  <tr className="text-[13.5px] text-[var(--dk-ink-3)]">
                    <th className="pb-1 text-right font-medium">ערוץ</th>
                    <th className="pb-1 text-right font-medium">גרסאות</th>
                    <th className="pb-1 text-right font-medium">חציון סטייה</th>
                  </tr>
                </thead>
                <tbody>
                  {a.deviation.map((d) => (
                    <tr
                      key={d.source}
                      className="border-t border-[var(--dk-border)]/60"
                    >
                      <td className="py-1 font-semibold">{d.source_he}</td>
                      <td
                        className={`py-1 font-mono text-[14px] ${d.n < 10 ? "text-[var(--dk-bad)]" : "text-[var(--dk-ink-2)]"}`}
                        dir="ltr"
                      >
                        {d.n}
                      </td>
                      <td className="py-1 font-mono text-[14px]" dir="ltr">
                        {d.median >= 0 ? "+" : ""}
                        {d.median.toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                אחוזון 85 של כתבה לעולם לא מוצג לבדו. הוא נכנס להשוואה מול{" "}
                <b>חציון האירוע</b> — כלומר מול הגרסאות של אותו סיפור בערוצים
                אחרים — כי ממוצע גולמי לערוץ מודד אילו סיפורים הוא בחר לסקר, לא
                איך הוא סיקר אותם. המודול הסטטיסטי מפרק את זה.
              </p>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="שלוש הסתייגויות שנשארות על המסך">
          {a ? (
            <div className="flex flex-col gap-2">
              <Caveat>
                מילון הקיטוב נבנה למדידת <b>עוצמה</b>, לא כיוון. ציון גבוה אומר
                &quot;דיון טעון&quot;, לא &quot;דיון בעד&quot; או &quot;נגד&quot;.
              </Caveat>
              <Caveat>
                חטיפת הנושא מודדת את הכתבה ואת התגובות באמצעות{" "}
                <b>לקסיקון הכתבות</b> — מילון שנבנה לטקסט עיתונאי ומופעל כאן על
                שפת דיבור. זה שימוש מחוץ להגדרה המקורית, והוא מוצהר ככזה.
              </Caveat>
              <Caveat>
                {a.deviation.filter((d) => d.n < 10).map((d) => d.source_he).join(", ") ||
                  "אין"}{" "}
                — תאים עם פחות מ-10 גרסאות. הם מופיעים בטבלה כדי שלא ייווצר רושם
                של כיסוי מלא, ולא מדווחים כממצא.
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

function Missing() {
  return (
    <p className="text-[15px] text-[var(--dk-ink-3)]">
      אין קובץ מדידות — הדיאגרמות מוצגות בלי המספרים.
    </p>
  );
}
