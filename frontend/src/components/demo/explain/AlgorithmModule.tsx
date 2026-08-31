"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import {
  Arrow,
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
  { id: "why", label_he: "למה מילון" },
  { id: "lexicon", label_he: "הרחבה אופליין" },
  { id: "window", label_he: "החיתוך לחלונות" },
  { id: "dominance", label_he: "דומיננטיות" },
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
 * Module: the deterministic analysis layer.
 *
 * Four decisions, one per tab: score with a dictionary instead of a model
 * because a research claim has to be reproducible; expand the Hebrew prefixes
 * once at build time so the runtime never touches a token and cannot invent a
 * match; cut at the sentence with a token ceiling so one paragraph cannot be
 * averaged away; and define dominance as a ratio inside the window, with NULL
 * — not zero — when the window holds no lexicon word at all.
 *
 * The worked example running through the last tab is computed by the real
 * pipeline functions in demo/snapshot/build_explainer_facts.py, so the
 * arithmetic on the wall is the arithmetic in the database.
 */
export function AlgorithmModule({ facts }: Props) {
  const [tab, setTab] = useState("why");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "why" && <WhyLexicon facts={facts} />}
      {tab === "lexicon" && <LexiconPanel facts={facts} />}
      {tab === "window" && <WindowCut facts={facts} />}
      {tab === "dominance" && <Dominance facts={facts} />}
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
    <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-2">
      <div className="text-2xl font-black text-[var(--dk-accent)]" dir="ltr">
        {value}
      </div>
      <div className="text-[13px] text-[var(--dk-ink-2)]">{label}</div>
    </div>
  );
}

/* ── 1. a dictionary, and what it cannot see ────────────────────── */

function WhyLexicon({ facts }: Props) {
  const w = facts?.windows;
  const maxDom = Math.max(1, ...(w?.dominance_hist.map((b) => b.n) ?? [1]));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <Panel
        title={
          w
            ? `${num(w.total)} חלונות נמדדו בלי אף קריאת מודל`
            : "חיפוש במילון במקום מודל שפה"
        }
      >
        {w ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              אפס קריאות מודל בשכבה הזאת, ולכן אותו קלט מחזיר אותו מספר גם בעוד
              שנה. מודל שפה, גם בטמפרטורה 0, תלוי בגרסה שהספק מגיש היום.
            </p>
            <div className="grid grid-cols-2 gap-2">
              <Node
                title="לקסיקון"
                tone="good"
                sub="אותו קלט → אותו פלט · ניתן להסבר מילה־מילה · עיוור למסגור"
              />
              <Node
                title="מודל שפה"
                tone="accent"
                sub="קורא מסגור וקול · אינו מבטיח שחזור · חייב אימות חיצוני"
              />
            </div>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              כל תוצאה נשמרת עם <CodeRef path="lexicon_version" /> — ‏sha256 של
              קובץ המילון המורחב. השתנה המילון, השתנה המזהה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          w
            ? `${pct(w.null_dominance / w.total)} מהחלונות בלי אף מילת לקסיקון`
            : "מה השכבה הזאת לא רואה"
        }
        hint={w ? `${num(w.total)} חלונות` : undefined}
      >
        {w ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              {num(w.null_dominance)} מתוך {num(w.total)} החלונות אינם מכילים אף
              מילת לקסיקון. הם נשמרים כ־NULL ולא כאפס: ״לא נמדד״ אינו ״נמדד ויצא
              אפס״.
            </p>
            <div className="flex flex-col gap-1">
              {w.dominance_hist
                .slice()
                .sort((a, b) => b.n - a.n)
                .map((b) => (
                  <BarRow
                    key={b.bucket}
                    label={b.bucket}
                    n={b.n}
                    max={maxDom}
                    tone={b.bucket === "null" ? "muted" : "accent"}
                    note={
                      b.bucket === "null"
                        ? "אין מילות לקסיקון"
                        : b.bucket === "1.0"
                          ? "חד־נושאי"
                          : undefined
                    }
                  />
                ))}
            </div>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              ספירת מילים גם אינה רואה מי המבצע ולמי מיוחסת האחריות. הפער הזה הוא
              מה שמצדיק מודל בהמשך — ולכן המודל מגיע עם מאמת שפוסל כל ביטוי שאינו
              בטקסט.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

/* ── 2. the lexicon is built once, offline ──────────────────────── */

function LexiconPanel({ facts }: Props) {
  const lx = facts?.lexicon;
  const lc = facts?.constants.lexicon;
  const maxBase = Math.max(1, ...(lx?.per_category.map((c) => c.base) ?? [1]));
  const top = lx?.per_category.reduce((a, b) => (b.base > a.base ? b : a));
  const low = lx?.per_category.reduce((a, b) => (b.base < a.base ? b : a));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <Panel
        title={
          lx
            ? `${lx.article_base} למות הפכו ל־${num(lx.article_expanded)} צורות לפני הריצה`
            : "המילון נבנה פעם אחת, אופליין"
        }
        hint="src/lexicon/load_lexicon.py"
      >
        {lx && lc ? (
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-center gap-1">
              <Node title="למות בסיס" sub="רשימות המחקר" />
              <Arrow label="הרחבת תחיליות" />
              <Node title="צורות פני־שטח" tone="accent" />
              <Arrow label="sha256" />
              <Node title="גרסת לקסיקון" tone="good" mono />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <ExpandStat
                title="לקסיקון הכתבות"
                base={lx.article_base}
                expanded={lx.article_expanded}
                factor={lx.article_factor}
              />
              <ExpandStat
                title="לקסיקון התגובות"
                base={lx.comment_base}
                expanded={lx.comment_expanded}
                factor={lx.comment_factor}
              />
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[14.5px] text-[var(--dk-ink-3)]">
                תחילית לכל למה באורך {lc.min_base_length} ומעלה:
              </span>
              {lc.single_prefixes.map((p) => (
                <code
                  key={p}
                  className="rounded bg-[var(--dk-surface-2)] px-1.5 py-0.5 font-mono text-[14.5px] text-[var(--dk-accent)]"
                >
                  {p}
                </code>
              ))}
            </div>
            <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
              ההרחבה רצה בבנייה, ורשימת הצמדים סגורה — שתי תחיליות חופשיות
              מייצרות מילים שאינן קיימות. בזמן הריצה הקוד לא נוגע בטוקן אלא מחפש
              אותו, ולכן אינו יכול להמציא התאמה.
            </p>
            <Caveat>
              צורה ששתי קטגוריות מייצרות נרשמת לקטגוריה שמספרה נמוך יותר. ההכרעה
              שרירותית, והיא זהה בכל ריצה.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title={
          top && low
            ? `${top.name_he} מחזיקה פי ${(top.base / low.base).toFixed(1)} למות מ${low.name_he}`
            : "גודל הקטגוריות"
        }
        hint={lx ? `${lx.article_base} למות בסיס` : undefined}
      >
        {lx && top && low ? (
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              {lx.per_category.map((c) => (
                <div key={c.category} className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 shrink-0 rounded-sm"
                    style={{ background: CAT_COLORS[c.category - 1] }}
                  />
                  <span className="w-[74px] shrink-0 text-[14.5px]">
                    {c.name_he}
                  </span>
                  <div className="flex-1">
                    <BarRow label={`c${c.category}`} n={c.base} max={maxBase} />
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              {top.base} למות מול {low.base}. ספירה גולמית הייתה מעדיפה את
              הקטגוריות העשירות, ולכן הדומיננטיות היא יחס בתוך החלון ולא ספירה
              בין חלונות.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
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
      <div className="text-[13.5px] text-[var(--dk-ink-2)]">{title}</div>
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

/* ── 3. where the text is cut ───────────────────────────────────── */

function WindowCut({ facts }: Props) {
  const cap = facts?.constants.windows.max_window_tokens;
  const w = facts?.windows;
  const ex = facts?.worked_example;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[44%_1fr] gap-3">
      <Panel title="יחידת הניתוח היא המשפט, לא הכתבה" hint="src/nlp/sentence_splitter.py">
        {cap ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              {cap} טוקנים הם התקרה, והמשפט הוא הגבול הראשון. ממוצע ברמת הכתבה
              היה מטביע פסקה ביטחונית אחת בתוך אלף מילות כלכלה.
            </p>
            <div className="flex items-center justify-center gap-1">
              <Node title="טקסט גולמי" />
              <Arrow label="פיצול" />
              <Node title="[.!?…] + רווח" mono tone="accent" />
              <Arrow label={`> ${cap} טוקנים`} />
              <Node title={`נתחים של ${cap}`} tone="accent" />
            </div>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              הפיצול רץ על הטקסט הגולמי, לפני הנרמול. בסדר ההפוך הנרמול מוחק את
              סימני הפיסוק, ואז כל הכתבה מתכווצת לחלון אחד ענק.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="הכתבה שעל המסך, חתוכה למשפטים"
        hint={ex ? `${ex.source_he} · ${ex.text_chars} תווים` : undefined}
      >
        {ex && w && cap ? (
          <div className="flex h-full min-h-0 flex-col gap-2">
            <div className="text-[15.5px] font-semibold leading-snug">
              {ex.title}
            </div>
            <div className="flex flex-wrap gap-1.5">
              <Chip tone="accent">{ex.sentences_total} משפטים</Chip>
              <Chip tone="accent">{ex.windows_total} חלונות</Chip>
            </div>
            <ol className="flex min-h-0 flex-1 flex-col gap-1 overflow-auto pe-1">
              {ex.sentences.map((s, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-2.5 py-1.5"
                >
                  <span
                    dir="ltr"
                    className={`mt-0.5 shrink-0 rounded px-1.5 font-mono text-[12.5px] ${
                      s.tokens > cap
                        ? "bg-[var(--dk-warn)]/20 text-[var(--dk-warn)]"
                        : "text-[var(--dk-ink-3)]"
                    }`}
                  >
                    {s.tokens}
                  </span>
                  <span className="text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
                    {s.text}
                  </span>
                </li>
              ))}
            </ol>
            <p className="text-[13.5px] text-[var(--dk-ink-3)]">
              המספר לצד כל משפט הוא ספירת הטוקנים שלו.
            </p>
            <div className="grid grid-cols-3 gap-2 text-center">
              <Stat label="חלונות לכתבה" value={String(w.per_article.avg)} />
              <Stat label="הכתבה הארוכה ביותר" value={String(w.per_article.max)} />
              <Stat label="טוקנים לחלון" value={String(w.avg_len)} />
            </div>
            <Caveat>
              <code dir="ltr" className="font-mono">
                window_len
              </code>{" "}
              נמדד אחרי הנרמול, והנרמול מפרק צירופים כמו{" "}
              <span dir="ltr">״א,ב״</span> לשני טוקנים. לכן {w.at_or_over_cap}{" "}
              חלונות יושבים על {cap} ומעלה והמקסימום הוא {w.max_len}. התקרה חלה
              על החיתוך בלבד.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

/* ── 4. what the number says, and what it refuses to say ────────── */

function Dominance({ facts }: Props) {
  const w = facts?.windows;
  const ex = facts?.worked_example;
  const cats = facts?.constants.categories_he ?? [];
  const one = w?.dominance_hist.find((b) => b.bucket === "1.0")?.n;
  const mixed = w?.active_hist
    .filter((b) => Number(b.bucket) >= 3)
    .reduce((s, b) => s + b.n, 0);

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[42%_1fr] gap-3">
      <Panel title="‏1.0 יכול להיות מילת לקסיקון אחת">
        {w && one !== undefined && mixed !== undefined ? (
          <div className="flex flex-col gap-3">
            <MetricCard
              name="דומיננטיות"
              field="windows_features.dominance"
              formula="max(c1..c7) / Σ(c1..c7)"
              range="(0, 1] ∪ {NULL}"
              reads={[
                { value: "1.0", means: "כל מילות הלקסיקון בחלון מקטגוריה אחת" },
                { value: "0.5", means: "הקטגוריה החזקה מחזיקה מחצית מהן" },
                {
                  value: "NULL",
                  means: "אין אף מילת לקסיקון — לא נמדד, לא אפס",
                },
              ]}
              measured={`${num(one)} מתוך ${num(w.total - w.null_dominance)} החלונות שנמדדו יצאו 1.0`}
            />
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              {num(one)} חלונות יצאו 1.0 — כל אלה שקטגוריה אחת פעילה בהם, גם אם
              היא נשענת על מילה בודדת. היחס מודד הרכב, לא עוצמה.
            </p>
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              {num(mixed)} חלונות מערבבים שלוש קטגוריות ומעלה. שם המספר מפריד בין
              משפט שנוגע בנושא אחד לבין משפט שקושר כמה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="החלון שעל המסך, מחושב"
        hint={ex ? `${ex.source_he} · חלון #${ex.window.index}` : undefined}
      >
        {ex ? (
          <div className="flex flex-col gap-2.5">
            <div className="flex flex-wrap gap-1 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-2">
              {ex.window.tokens.map((t, i) => (
                <span
                  key={i}
                  className="rounded px-1 py-0.5 text-[13.5px]"
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

            <div className="flex flex-wrap gap-1.5">
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
                className="text-center font-mono text-[16.5px] leading-relaxed text-[var(--dk-accent)]"
              >
                dominance = max({ex.window.counts.join(", ")}) /{" "}
                {ex.window.cat_words}
                <br />= {ex.window.max_count} / {ex.window.cat_words} ={" "}
                <b>{ex.window.dominance}</b>
              </div>
            </div>

            <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
              {ex.window.window_len} טוקנים, ובתוכם {ex.window.cat_words} מילות
              לקסיקון מ־{ex.window.active} קטגוריות. החזקה מחזיקה{" "}
              {ex.window.max_count} מהן, ולכן החלון{" "}
              {ex.window.dominance !== null && ex.window.dominance >= 0.75
                ? "כמעט חד־נושאי"
                : "מפוצל בין נושאים"}
              .
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}
