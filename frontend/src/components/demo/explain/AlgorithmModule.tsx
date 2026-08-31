"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import {
  BarRow,
  Chip,
  MetricCard,
  Node,
  Panel,
  Stage,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "why", label_he: "למה מילון ולא מודל" },
  { id: "measure", label_he: "איך נמדדת כתבה" },
];

/** One hue per lexicon category, stable across every panel in the module. */
const CAT_COLORS = [
  "#22d3ee",
  "#f472b6",
  "#fbbf24",
  "#34d399",
  "#a78bfa",
  "#fb923c",
  "#60a5fa",
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the deterministic analysis layer — the part of the system that owes
 * nobody an API key.
 *
 * Two tabs. First the choice: score against a fixed dictionary rather than a
 * model, because a research claim has to give the same answer next year, and
 * because the dictionary is built once offline so the runtime only ever looks
 * a word up and cannot invent a match. Then the measurement itself: the unit
 * is the sentence, and the score is a ratio inside one window.
 *
 * The worked example is computed by the real pipeline functions in
 * demo/snapshot/build_explainer_facts.py, so the arithmetic on the wall is
 * the arithmetic in the database.
 */
export function AlgorithmModule({ facts }: Props) {
  const [tab, setTab] = useState("why");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "why" && <WhyLexicon facts={facts} />}
      {tab === "measure" && <Measure facts={facts} />}
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

function Missing() {
  return (
    <p className="text-[15.5px] text-[var(--dk-ink-3)]">אין קובץ מדידות.</p>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-2 py-2.5">
      <div
        className="text-[26px] font-black leading-none text-[var(--dk-accent)]"
        dir="ltr"
      >
        {value}
      </div>
      <div className="mt-1 text-[13.5px] leading-snug text-[var(--dk-ink-2)]">
        {label}
      </div>
    </div>
  );
}

/* ── 1. a dictionary, built once, looked up forever ─────────────── */

function WhyLexicon({ facts }: Props) {
  const w = facts?.windows;
  const lx = facts?.lexicon;
  const lc = facts?.constants.lexicon;
  const maxBase = Math.max(1, ...(lx?.per_category.map((c) => c.base) ?? [1]));

  return (
    <Stage cols="grid-cols-[46%_1fr]">
      <Panel
        title={
          w
            ? `${num(w.total)} מדידות, ואף אחת מהן לא עברה במודל`
            : "מילון קבוע במקום מודל שפה"
        }
      >
        {w ? (
          <div className="flex flex-col gap-4">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              זו עבודה מחקרית, ומספר במחקר צריך להיות ניתן לשחזור. מודל שפה לא
              נותן את זה: גם בטמפרטורה 0, שבה הוא אמור לבחור תמיד את המילה
              הסבירה ביותר, אותה בקשה יכולה לחזור עם תשובה אחרת — החישוב על
              כרטיס גרפי תלוי באילו בקשות אחרות עובדו יחד באותו רגע, והפרש
              זעיר בסדר החיבור מספיק כדי להזיז מילה אחת ואחריה את כל המשפט.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              כאן כל כתבה נחתכת למשפטים, וכל משפט נספר מול מילון קבוע של מילים
              לפי נושא. אותו טקסט יחזיר את אותו מספר גם בעוד שנה, גם בלי חיבור
              לאינטרנט, ובעלות אפס.
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              <Node
                title="מילון קבוע"
                tone="good"
                sub="אותו קלט, אותו מספר · אפשר להצביע על המילה שגרמה · לא רואה מסגור"
              />
              <Node
                title="מודל שפה"
                tone="accent"
                sub="רואה מסגור וקול · אותה בקשה, לא תמיד אותה תשובה · דורש אימות"
              />
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              מילים מתיישנות — אוצר המילים של החדשות זז, והמילון חייב להתעדכן.
              לכן כל מדידה נושאת את חתימת גרסת המילון שהפיקה אותה: ניהול גרסאות
              (<code dir="ltr" className="font-mono text-[16px]">versioning</code>
              ) בדיוק כמו לקוד.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              נוספה מילה, מריצים הכל מחדש ורואים אילו מספרים זזו ולמה — רגרסיה
              שאפשר לאתר, במקום לגלות חודש אחר כך שהשוואה נשענה על שתי גרסאות
              שונות. הריצה החוזרת לא עולה כלום ולא תלויה בספק, ולכן עדכון מילון
              הוא החלטה מוצרית ולא סעיף תקציב.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              ספירת מילים לא רואה מי מוצג כמבצע ולמי מיוחסת אחריות. בשביל זה יש
              מודל בהמשך, והוא מגיע עם מאמת שפוסל כל ביטוי שאינו בטקסט כלשונו.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          lx
            ? `${lx.article_base} מילות בסיס הפכו ל־${num(lx.article_expanded)} צורות לפני הריצה`
            : "המילון נבנה פעם אחת, מראש"
        }
      >
        {lx && lc ? (
          <div className="flex flex-col gap-3.5">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              בעברית אותה מילה מופיעה בעשר צורות: בחירות, הבחירות, ובחירות,
              שהבחירות. במקום לנסות לפרק אותן בזמן אמת, כל הצורות נוצרות מראש
              ובזמן הריצה המערכת רק מחפשת התאמה מדויקת.
            </p>
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[15px] text-[var(--dk-ink-3)]">
                התחיליות שמודבקות לכל מילה באורך {lc.min_base_length} ומעלה:
              </span>
              {lc.single_prefixes.map((p) => (
                <code
                  key={p}
                  className="rounded bg-[var(--dk-surface-2)] px-1.5 py-0.5 font-mono text-[15px] text-[var(--dk-accent)]"
                >
                  {p}
                </code>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              <ExpandStat
                title="מילון הכתבות"
                base={lx.article_base}
                expanded={lx.article_expanded}
                factor={lx.article_factor}
              />
              <ExpandStat
                title="מילון התגובות"
                base={lx.comment_base}
                expanded={lx.comment_expanded}
                factor={lx.comment_factor}
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              המספר הקטן הוא מילות הבסיס, הגדול הוא כמה צורות הן מייצרות.
              ‏×{lx.article_factor} = בממוצע {lx.article_factor} צורות לכל מילת
              בסיס.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              בזמן ריצה הקוד לא נוגע במילה אלא מחפש אותה, ולכן הוא לא יכול
              להמציא התאמה. רשימת צירופי התחיליות סגורה — צירוף חופשי היה מייצר
              מילים שלא קיימות בעברית.
            </p>
            <div className="flex flex-col gap-1.5">
              {lx.per_category.map((c) => (
                <div key={c.category} className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 shrink-0 rounded-sm"
                    style={{ background: CAT_COLORS[c.category - 1] }}
                  />
                  <span className="w-[74px] shrink-0 text-[15px]">
                    {c.name_he}
                  </span>
                  <div className="flex-1">
                    <BarRow
                      label={String(c.category)}
                      n={c.base}
                      max={maxBase}
                    />
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              שבעת הנושאים שהמילון מכסה, ולצד כל אחד מספר מילות הבסיס שלו. הם
              אינם שווים בגודלם, ולכן הציון בהמשך הוא יחס בתוך המשפט ולא ספירה
              בין משפטים.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

function ExpandStat({
  title,
  base,
  expanded,
  factor,
}: {
  title: string;
  base: number;
  expanded: number;
  factor: number;
}) {
  return (
    <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-2.5 text-center">
      <div className="text-[14px] text-[var(--dk-ink-2)]">{title}</div>
      <div className="flex items-baseline justify-center gap-2" dir="ltr">
        <span className="font-mono text-lg text-[var(--dk-ink-3)]">{base}</span>
        <span className="text-[var(--dk-ink-3)]">→</span>
        <span className="font-mono text-2xl font-black text-[var(--dk-accent)]">
          {expanded.toLocaleString("en-US")}
        </span>
      </div>
      <div className="text-[13px] text-[var(--dk-ink-3)]" dir="ltr">
        ×{factor}
      </div>
    </div>
  );
}

/* ── 2. the sentence is the unit, the score is a ratio ──────────── */

function Measure({ facts }: Props) {
  const cap = facts?.constants.windows.max_window_tokens;
  const w = facts?.windows;
  const ex = facts?.worked_example;
  const cats = facts?.constants.categories_he ?? [];
  const one = w?.dominance_hist.find((b) => b.bucket === "1.0")?.n;

  return (
    <Stage cols="grid-cols-[46%_1fr]">
      <Panel
        title="יחידת המדידה היא המשפט, לא הכתבה"
        hint={ex ? `${ex.source_he} · ${ex.text_chars} תווים` : undefined}
      >
        {ex && w && cap ? (
          <div className="flex min-h-0 flex-col gap-3">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              כתבה שלמה שמקבלת ציון אחד מטביעה את עצמה: פסקה אחת על ביטחון בתוך
              אלף מילים על כלכלה נעלמת בממוצע. לכן כל משפט נמדד לחוד.
            </p>
            <div className="text-[16px] font-semibold leading-snug">
              {ex.title}
            </div>
            <div className="flex flex-wrap gap-1.5">
              <Chip tone="accent">{ex.sentences_total} משפטים</Chip>
              <Chip tone="accent">{ex.windows_total} יחידות מדידה</Chip>
            </div>
            <ol className="flex min-h-0 flex-col gap-1 overflow-auto pe-1">
              {ex.sentences.map((s, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-2.5 py-1.5"
                >
                  <span
                    dir="ltr"
                    className={`mt-0.5 shrink-0 rounded px-1.5 font-mono text-[13px] ${
                      s.tokens > cap
                        ? "bg-[var(--dk-warn)]/20 text-[var(--dk-warn)]"
                        : "text-[var(--dk-ink-3)]"
                    }`}
                  >
                    {s.tokens}
                  </span>
                  <span className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                    {s.text}
                  </span>
                </li>
              ))}
            </ol>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              מוצגים {ex.sentences.length} המשפטים הראשונים מתוך{" "}
              {ex.sentences_total}, והמספר לצד כל אחד הוא כמה מילים יש בו. משפט
              ארוך מ־{cap} מילים נחתך לנתחים, כדי שיחידה אחת לא תבלע פסקה
              שלמה; ‏{w.at_or_over_cap} יחידות יוצאות מעט מעל התקרה, כי הספירה
              הסופית נעשית אחרי ניקוי הטקסט.
            </p>
            <div className="grid grid-cols-3 gap-2.5 text-center">
              <Stat label="יחידות בכתבה ממוצעת" value={String(w.per_article.avg)} />
              <Stat label="בכתבה הארוכה ביותר" value={String(w.per_article.max)} />
              <Stat label="מילים ביחידה ממוצעת" value={String(w.avg_len)} />
            </div>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="הציון אומר על מה המשפט, לא כמה חזק הוא"
        hint={ex ? `${ex.source_he} · יחידה מספר ${ex.window.index}` : undefined}
      >
        {ex && w && one !== undefined ? (
          <div className="flex flex-col gap-3">
            <MetricCard
              name="דומיננטיות"
              field="windows_features.dominance"
              formula="max(c1..c7) / Σ(c1..c7)"
              range="0 – 1"
              reads={[
                { value: "1.0", means: "כל מילות המילון במשפט מאותו נושא" },
                { value: "0.5", means: "הנושא החזק מחזיק מחצית מהן" },
                {
                  value: "NULL",
                  means: "אין אף מילת מילון במשפט — לא נמדד, לא אפס",
                },
              ]}
              measured={`${num(one)} מתוך ${num(w.total - w.null_dominance)} היחידות שנמדדו יצאו 1.0`}
            />

            <div className="flex flex-wrap gap-1 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-2">
              {ex.window.tokens.map((t, i) => (
                <span
                  key={i}
                  className="rounded px-1 py-0.5 text-[14px]"
                  style={
                    t.category
                      ? {
                          background: `${CAT_COLORS[t.category - 1]}22`,
                          color: CAT_COLORS[t.category - 1],
                          fontWeight: 700,
                        }
                      : { color: "var(--dk-ink-3)" }
                  }
                >
                  {t.t}
                </span>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[15px] text-[var(--dk-ink-3)]">
                כל צבע הוא נושא; מילה אפורה אינה במילון.
              </span>
              {ex.window.counts.map((n, i) =>
                n > 0 ? (
                  <Chip key={i}>
                    <span
                      className="h-2 w-2 rounded-sm"
                      style={{ background: CAT_COLORS[i] }}
                    />
                    {cats[i] ?? `c${i + 1}`} = {n}
                  </Chip>
                ) : null,
              )}
            </div>

            <div className="rounded-xl border border-[var(--dk-accent)]/30 bg-[var(--dk-accent-dim)]/40 p-3">
              <div
                dir="ltr"
                className="text-center font-mono text-[17px] leading-relaxed text-[var(--dk-accent)]"
              >
                dominance = max({ex.window.counts.join(", ")}) /{" "}
                {ex.window.cat_words}
                <br />= {ex.window.max_count} / {ex.window.cat_words} ={" "}
                <b>{ex.window.dominance}</b>
              </div>
            </div>

            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              ‏{ex.window.cat_words} מילות מילון מ־{ex.window.active} נושאים,
              והחזק מחזיק {ex.window.max_count} מהן. הציון מודד הרכב ולא עוצמה:
              נושא יחיד נותן 1.0 גם כשהוא נשען על מילה אחת.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              משפט בלי אף מילת מילון נשמר כ־NULL ולא כאפס — {pct(
                w.null_dominance / w.total,
              )}{" "}
              מהיחידות. ״לא נמדד״ אינו ״נמדד ויצא אפס״, ומיצוע של השניים יחד היה
              מזייף כל השוואה בהמשך.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}
