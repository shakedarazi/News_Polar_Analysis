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
  { id: "window", label_he: "למה חלון" },
  { id: "clean", label_he: "ניקוי וטוקניזציה" },
  { id: "lexicon", label_he: "הלקסיקון" },
  { id: "win_numbers", label_he: "מדדי החלון" },
  { id: "aud_numbers", label_he: "מדדי הקהל" },
  { id: "determinism", label_he: "דטרמיניזם" },
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
 * Module: the deterministic analysis layer — what gets cut, what gets
 * counted, and what each resulting number actually licenses you to say.
 *
 * The worked example running through these panels is computed by the real
 * pipeline functions in demo/snapshot/build_explainer_facts.py, so the
 * arithmetic on the wall is the arithmetic in the database.
 */
export function AlgorithmModule({ facts }: Props) {
  const [tab, setTab] = useState("window");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "window" && <WhyWindow facts={facts} />}
      {tab === "clean" && <Cleaning facts={facts} />}
      {tab === "lexicon" && <LexiconPanel facts={facts} />}
      {tab === "win_numbers" && <WindowNumbers facts={facts} />}
      {tab === "aud_numbers" && <AudienceNumbers facts={facts} />}
      {tab === "determinism" && <Determinism facts={facts} />}
    </div>
  );
}

/* ── 1. why a window ────────────────────────────────────────────── */

function WhyWindow({ facts }: Props) {
  const cap = facts?.constants.windows.max_window_tokens ?? 60;
  const w = facts?.windows;
  const ex = facts?.worked_example;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[47%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="יחידת הניתוח היא המשפט, לא הכתבה">
          <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
            כתבה בת אלף מילים שנוגעת בביטחון בפסקה אחת ובכלכלה בשאר — ממוצע ברמת
            הכתבה יראה אותה כ״מעורבת״ ויאבד את שתיהן. החלון שומר על ההבחנה: כל
            משפט נמדד לעצמו, והכתבה היא התפלגות של חלונות, לא נקודה אחת.
          </p>
        </Panel>

        <Panel title="כלל החיתוך" hint="src/nlp/sentence_splitter.py">
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-center gap-1">
              <Node title="טקסט גולמי" />
              <Arrow label="פיצול" />
              <Node title="[.!?…] + רווח" mono tone="accent" />
              <Arrow label={`> ${cap} טוקנים`} />
              <Node title={`נתחים של ${cap}`} tone="accent" />
            </div>
            <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
              לפני הפיצול, קיצורים כמו{" "}
              <code dir="ltr" className="font-mono">
                dr.
              </code>{" "}
              /{" "}
              <code dir="ltr" className="font-mono">
                e.g.
              </code>{" "}
              מוחלפים זמנית ב־
              <code dir="ltr" className="font-mono">
                &lt;DOT&gt;
              </code>{" "}
              כדי שנקודה של קיצור לא תשבור משפט, ומוחזרים אחריו.
            </p>
          </div>
        </Panel>

        <Panel title="החלטת סדר שקל מאוד לטעות בה">
          <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
            הפיצול רץ על הטקסט <b>הגולמי</b>, לפני הנרמול. הנרמול מוחק סימני
            פיסוק — ואם הוא רץ ראשון, אין יותר נקודות לפצל עליהן וכל הכתבה
            מתכווצת לחלון אחד ענק. אותן שתי פונקציות, סדר הפוך, וכל הניתוח
            מתמוטט בשקט בלי שאף בדיקה תיפול.
          </p>
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="כתבה אמיתית מהסנאפשוט, חתוכה בפועל"
          hint={ex ? `${ex.source_he} · ${ex.text_chars} תווים` : undefined}
        >
          {ex ? (
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
                המספר משמאל הוא ספירת הטוקנים של המשפט. משפט מעל {cap} היה נחתך
                לנתחים — בכתבה הזו זה לא קרה.
              </p>
            </div>
          ) : (
            <p className="text-[15.5px] text-[var(--dk-ink-3)]">
              אין קובץ מדידות.
            </p>
          )}
        </Panel>

        {w && (
          <Panel
            title="כמה חלונות יצאו בפועל"
            hint={`${w.total.toLocaleString("en-US")} חלונות`}
          >
            <div className="grid grid-cols-3 gap-2 text-center">
              <Stat label="לכתבה בממוצע" value={String(w.per_article.avg)} />
              <Stat
                label="הכתבה הארוכה ביותר"
                value={String(w.per_article.max)}
              />
              <Stat label="טוקנים לחלון בממוצע" value={String(w.avg_len)} />
            </div>
            <Caveat>
              <code dir="ltr" className="font-mono">
                window_len
              </code>{" "}
              נמדד <b>אחרי</b> הנרמול, והנרמול מפרק צירופים כמו{" "}
              <span dir="ltr">״א,ב״</span> לשני טוקנים. לכן {w.at_or_over_cap}{" "}
              חלונות יושבים על {cap} או מעליו, והמקסימום בפועל הוא {w.max_len} —
              התקרה חלה על החיתוך, לא על הספירה.
            </Caveat>
          </Panel>
        )}
      </div>
    </div>
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

/* ── 2. cleaning ────────────────────────────────────────────────── */

const CLEAN_STEPS = [
  { op: "URL → רווח", why: "כתובת אינה שפה, והיא מרעילה את ספירת הטוקנים" },
  {
    op: "הסרת ניקוד",
    why: "אותה מילה מנוקדת ולא־מנוקדת חייבת להיות אותו טוקן",
  },
  { op: "מירכאות ומקפים חכמים → ASCII", why: "הבדל טיפוגרפי, לא לשוני" },
  { op: "lowercase", why: "רלוונטי ללועזית שמשולבת בעברית" },
  {
    op: "תווים לא־לשוניים → רווח",
    why: "נשמרים רק אותיות, ספרות, עברית, גרש ומקף",
  },
  {
    op: "כיווץ רווחים",
    why: "טוקניזציה היא פיצול על רווח — כפילויות יוצרות טוקנים ריקים",
  },
];

function Cleaning({ facts }: Props) {
  const ex = facts?.worked_example;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[40%_1fr] gap-3">
      <Panel title="שרשרת הנרמול" hint="src/nlp/normalize.py">
        <ol className="flex flex-col gap-1.5">
          {CLEAN_STEPS.map((s, i) => (
            <li
              key={s.op}
              className="flex items-start gap-2.5 rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-2.5 py-1.5"
            >
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--dk-surface)] font-mono text-[11px] text-[var(--dk-ink-3)]">
                {i + 1}
              </span>
              <div>
                <div className="text-[15px] font-semibold">{s.op}</div>
                <div className="text-[13.5px] leading-snug text-[var(--dk-ink-3)]">
                  {s.why}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </Panel>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="החלון האמיתי, לפני ואחרי"
          hint={ex ? `חלון #${ex.window.index} בכתבה` : undefined}
        >
          {ex ? (
            <div className="flex flex-col gap-2">
              <Labeled label="גולמי">
                <span className="text-[15px] leading-relaxed text-[var(--dk-ink)]">
                  {ex.window.raw}
                </span>
              </Labeled>
              <div className="text-center text-lg text-[var(--dk-ink-3)]">
                ↓
              </div>
              <Labeled label="מנורמל">
                <span className="text-[15px] leading-relaxed text-[var(--dk-good)]">
                  {ex.window.normalized}
                </span>
              </Labeled>
            </div>
          ) : (
            <p className="text-[15.5px] text-[var(--dk-ink-3)]">
              אין קובץ מדידות.
            </p>
          )}
        </Panel>

        <Panel
          title="טוקניזציה — פיצול על רווח, וזהו"
          hint="src/nlp/tokenize.py"
        >
          <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
            אין שורש, אין למטיזציה, אין מודל מורפולוגי. טוקן הוא רצף בין שני
            רווחים. כל העברית של המערכת יושבת בצד השני של המשוואה — בלקסיקון
            שהורחב מראש. זה מה שהופך את שלב הריצה לחיפוש במילון: הוא לא יכול
            להמציא התאמה, כי הוא לא נוגע במילה.
          </p>
          <Caveat>
            הפיצול למשפטים דורש רווח אחרי הנקודה. במקור אמיתי בסנאפשוט מופיע{" "}
            <span dir="ltr">״הסדר הציבורי.לפני כחודשיים״</span> — בלי רווח, ולכן
            זה נשאר חלון אחד. שגיאת הקלדה של עורך מוזגת שני משפטים.
          </Caveat>
        </Panel>
      </div>
    </div>
  );
}

function Labeled({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-2.5">
      <div className="mb-1 text-[13px] text-[var(--dk-ink-3)]">{label}</div>
      {children}
    </div>
  );
}

/* ── 3. lexicon ─────────────────────────────────────────────────── */

function LexiconPanel({ facts }: Props) {
  const lx = facts?.lexicon;
  const lc = facts?.constants.lexicon;
  const maxBase = Math.max(1, ...(lx?.per_category.map((c) => c.base) ?? [1]));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[44%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="נבנה פעם אחת, אופליין"
          hint="src/lexicon/expand_lexicon.py"
        >
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-center gap-1">
              <Node title="למות בסיס" sub="רשימות המחקר" />
              <Arrow label="הרחבת תחיליות" />
              <Node title="צורות פני־שטח" tone="accent" />
              <Arrow label="sha256" />
              <Node title="גרסת לקסיקון" tone="good" mono />
            </div>
            {lc && (
              <>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[14.5px] text-[var(--dk-ink-3)]">
                    תחילית בודדת:
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
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[14.5px] text-[var(--dk-ink-3)]">
                    צמד מאושר בלבד:
                  </span>
                  {lc.prefix_pairs.map((p) => (
                    <code
                      key={p}
                      className="rounded bg-[var(--dk-surface-2)] px-1.5 py-0.5 font-mono text-[14.5px] text-[var(--dk-accent)]"
                    >
                      {p}
                    </code>
                  ))}
                </div>
                <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
                  רק צמדים מאושרים, ורק ללמה באורך {lc.min_base_length} ומעלה —
                  הרחבה חופשית של שתי תחיליות מייצרת מילים שאינן קיימות ומזהמת
                  את המילון.
                </p>
              </>
            )}
          </div>
        </Panel>

        <Panel title="כלל ההתנגשות">
          <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
            אם שתי למות מקטגוריות שונות מייצרות אותה צורת פני־שטח, הצורה{" "}
            <b>נמחקת מהמילון</b> — לא מוכרעת לטובת אחת מהן. המערכת מוותרת על
            ההתאמה במקום לנחש אותה. זה מוזיל את הכיסוי ומייקר את הדיוק, וזו
            ההעדפה הנכונה כשהמספר בסוף אמור להיות ראיה.
          </p>
        </Panel>
      </div>

      <Panel title="בסיס מול הרחבה — הגדלים בפועל">
        {lx ? (
          <div className="flex flex-col gap-3">
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
            <Caveat>
              הקטגוריות אינן שוות בגודלן — ״ביטחון״ מחזיקה{" "}
              {lx.per_category[1].base} למות ו״משפט״ {lx.per_category[4].base}.
              ספירה גולמית מוטה לטובת הקטגוריות העשירות, ולכן הדומיננטיות היא{" "}
              <b>יחס</b> בתוך החלון ולא ספירה מוחלטת בין חלונות.
            </Caveat>
          </div>
        ) : (
          <p className="text-[15.5px] text-[var(--dk-ink-3)]">
            אין קובץ מדידות.
          </p>
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

/* ── 4. window metrics ──────────────────────────────────────────── */

function WindowNumbers({ facts }: Props) {
  const ex = facts?.worked_example;
  const w = facts?.windows;
  const cats = facts?.constants.categories_he ?? [];
  const maxDom = Math.max(1, ...(w?.dominance_hist.map((b) => b.n) ?? [1]));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[38%_1fr] gap-3">
      <Panel
        title="החישוב על חלון אמיתי"
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
              {ex.window.window_len} טוקנים, מתוכם {ex.window.cat_words} מילות
              לקסיקון מ־{ex.window.active} קטגוריות. הקטגוריה החזקה מחזיקה{" "}
              {ex.window.max_count} מהן — כלומר החלון{" "}
              {ex.window.dominance !== null && ex.window.dominance >= 0.75
                ? "כמעט חד־נושאי"
                : "מפוצל בין נושאים"}
              , וזה בדיוק מה שהמספר אומר.
            </p>
          </div>
        ) : (
          <p className="text-[15.5px] text-[var(--dk-ink-3)]">
            אין קובץ מדידות.
          </p>
        )}
      </Panel>

      <div className="grid min-h-0 grid-rows-[1fr_auto] gap-3">
        <div className="grid min-h-0 grid-cols-3 gap-2.5">
          <MetricCard
            name="דומיננטיות"
            field="windows_features.dominance"
            formula="max(c1..c7) / Σ(c1..c7)"
            range="(0, 1] ∪ {NULL}"
            reads={[
              { value: "1.0", means: "כל מילות הלקסיקון בחלון מקטגוריה אחת" },
              { value: "0.5", means: "פיצול שווה בין שתי קטגוריות" },
              {
                value: "NULL",
                means: "אין אף מילת לקסיקון — לא 0, אלא ׳אין מדידה׳",
              },
            ]}
            measured={
              w
                ? `${w.null_dominance.toLocaleString("en-US")} מתוך ${w.total.toLocaleString("en-US")} חלונות הם NULL (${Math.round((w.null_dominance / w.total) * 100)}%)`
                : undefined
            }
          />
          <MetricCard
            name="קטגוריות פעילות"
            field="windows_features.active"
            formula="count(c_i > 0)"
            range="0 … 7"
            reads={[
              { value: "0", means: "חלון ללא לקסיקון — הבסיס של ה־NULL" },
              { value: "1", means: "חלון חד־נושאי; דומיננטיות תמיד 1.0" },
              { value: "≥3", means: "משפט שמערבב נושאים — המקרה המעניין" },
            ]}
            measured={
              w
                ? `הכי נפוץ: ${w.active_hist.reduce((a, b) => (b.n > a.n ? b : a)).bucket} קטגוריות`
                : undefined
            }
          />
          <MetricCard
            name="אורך חלון"
            field="windows_features.window_len"
            formula="len(tokens(normalize(window)))"
            range="1 … (≈60)"
            reads={[
              {
                value: "קטן",
                means: "משפט קצר; מילת לקסיקון בודדת מקפיצה את היחס",
              },
              { value: "60", means: "משפט שנחתך בתקרה" },
            ]}
            measured={
              w ? `ממוצע ${w.avg_len}, מקסימום ${w.max_len}` : undefined
            }
          />
        </div>

        {w && (
          <Panel
            title="התפלגות הדומיננטיות בפועל"
            hint={`${w.total.toLocaleString("en-US")} חלונות`}
          >
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
          </Panel>
        )}
      </div>
    </div>
  );
}

/* ── 5. audience metrics ────────────────────────────────────────── */

function AudienceNumbers({ facts }: Props) {
  const cm = facts?.comments;

  return (
    <div className="grid min-h-0 flex-1 grid-rows-[1fr_auto] gap-3">
      <div className="grid min-h-0 grid-cols-3 gap-2.5">
        <MetricCard
          name="יחס קיטוב בתגובה"
          field="comments.polar_ratio"
          formula="polar_count / max(1, comment_len)"
          range="[0, 1]"
          reads={[
            { value: "0", means: "אף מילה מהלקסיקון הקוטבי" },
            { value: "0.05", means: "מילה קוטבית אחת מכל עשרים — סביב הממוצע" },
            {
              value: "גבוה",
              means: "תגובה קצרה וטעונה; אורך קטן מנפח את היחס",
            },
          ]}
          measured={
            cm
              ? `${cm.total.toLocaleString("en-US")} תגובות, ${cm.avg_chars} תווים בממוצע`
              : undefined
          }
        />
        <MetricCard
          name="משקל מעורבות"
          field="engagement_weight"
          formula="1 + ln(1 + likes + dislikes)"
          range="[1, ∞)"
          reads={[
            { value: "1.0", means: "תגובה בלי אף לייק — עדיין נספרת" },
            { value: "≈3.7", means: "תגובה עם 14 לייקים (הממוצע כאן)" },
            { value: "≈8.5", means: "תגובה ויראלית עם 1,800 לייקים" },
          ]}
          measured={
            cm
              ? `ממוצע ${cm.avg_likes} לייקים, מקסימום ${cm.max_likes.toLocaleString("en-US")}`
              : undefined
          }
        />
        <MetricCard
          name="מחלוקת"
          field="controversy"
          formula="4·p·(1−p),  p = likes/(likes+dislikes)"
          range="[0, 1]"
          reads={[
            { value: "1.0", means: "פיצול מושלם 50/50 — הקהל חלוק" },
            { value: "0.0", means: "הצבעה חד־צדדית, או אפס הצבעות" },
          ]}
          measured="מקורות שאינם מפרסמים דיסלייקים נותנים p=1 ולכן 0"
        />
        <MetricCard
          name="ממוצע הקהל"
          field="article_comments_agg.audience_mean"
          formula="Σ(score·weight) / Σ(weight)"
          range="[0, 1]"
          reads={[
            { value: "≈0.026", means: "הרמה האופיינית לכתבה בסנאפשוט" },
            { value: "גבוה", means: "הדיון כולו טעון, לא רק קצוותיו" },
          ]}
          measured={cm ? `ממוצע ${cm.avg_audience_mean}` : undefined}
        />
        <MetricCard
          name="אחוזון 85 של הקהל"
          field="article_comments_agg.audience_p85"
          formula="weighted quantile(scores, 0.85)"
          range="[0, 1]"
          reads={[
            { value: "≈0.056", means: "פי שניים מהממוצע — הזנב הוא הסיפור" },
            { value: "= mean", means: "דיון אחיד; אין קצה קיצוני" },
          ]}
          measured={
            cm
              ? `ממוצע ${cm.avg_audience_p85} — פי ${(cm.avg_audience_p85 / cm.avg_audience_mean).toFixed(1)} מהממוצע`
              : undefined
          }
        />
        <MetricCard
          name="מספר תגובות"
          field="article_comments_agg.num_comments"
          formula="count(comments)"
          range="0 … ∞"
          reads={[
            { value: "0", means: "אין אות קהל — הכתבה לא נכנסת לחישובי הקהל" },
            { value: "נמוך", means: "אחוזון 85 מחושב על מדגם זעיר; לא ראיה" },
          ]}
          measured={
            cm
              ? `ממוצע ${cm.avg_num_comments}, מקסימום ${cm.max_num_comments.toLocaleString("en-US")}`
              : undefined
          }
        />
      </div>

      <Panel title="למה אחוזון 85 ולא ממוצע">
        <div className="flex items-center gap-5">
          {cm && (
            <div className="flex shrink-0 items-end gap-3">
              <MiniBar
                label="ממוצע"
                value={cm.avg_audience_mean}
                max={cm.avg_audience_p85}
                tone="var(--dk-ink-3)"
              />
              <MiniBar
                label="אחוזון 85"
                value={cm.avg_audience_p85}
                max={cm.avg_audience_p85}
                tone="var(--dk-accent)"
              />
            </div>
          )}
          <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
            דיון של מאות תגובות כמעט תמיד רגוע בממוצע — הרוב הגדול ניטרלי, והוא
            מדלל כל קצה. מה שמעניין בקיטוב הוא דווקא הזנב: כמה טעון הדיון
            כשמסתכלים על החלק העליון שלו. אחוזון 85, משוקלל באותם משקלי מעורבות,
            מודד בדיוק את זה — ולכן הוא יוצא פי{" "}
            {cm ? (cm.avg_audience_p85 / cm.avg_audience_mean).toFixed(1) : "2"}{" "}
            מהממוצע על אותן כתבות בדיוק.
          </p>
        </div>
      </Panel>
    </div>
  );
}

function MiniBar({
  label,
  value,
  max,
  tone,
}: {
  label: string;
  value: number;
  max: number;
  tone: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span
        className="font-mono text-[14.5px]"
        dir="ltr"
        style={{ color: tone }}
      >
        {value.toFixed(4)}
      </span>
      <div
        className="w-12 rounded-t-md"
        style={{
          height: `${Math.max(8, (value / max) * 56)}px`,
          background: tone,
        }}
      />
      <span className="text-[13.5px] text-[var(--dk-ink-2)]">{label}</span>
    </div>
  );
}

/* ── 5. determinism ─────────────────────────────────────────────── */

function Determinism({ facts }: Props) {
  const w = facts?.windows;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-2 gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="למה זה בכלל חשוב כאן">
          <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
            הטענה של הפרויקט היא טענה מחקרית על ערוצי חדשות. טענה כזו חייבת
            להיות ניתנת לשחזור: מי שמריץ את אותו קוד על אותו מסד חייב לקבל את
            אותו מספר, אחרת אין לו מה לבדוק. מודל שפה, גם בטמפרטורה 0, אינו נותן
            את ההבטחה הזו — הוא תלוי בגרסה שהספק מגיש היום.
          </p>
        </Panel>

        <Panel title="מה מבטיח את זה בפועל">
          <ul className="flex flex-col gap-2 text-[15px] leading-snug text-[var(--dk-ink-2)]">
            <li>
              <b className="text-[var(--dk-ink)]">חיפוש במילון, לא ניתוח.</b>{" "}
              אין מודל שפה, אין שורשן, אין הסתברות. טוקן נמצא במילון או לא.
            </li>
            <li>
              <b className="text-[var(--dk-ink)]">המילון מגורסה.</b> כל תוצאה
              נשמרת עם <CodeRef path="lexicon_version" /> — sha256 של קובץ
              המילון המורחב. השתנה המילון, השתנה המזהה, וברור על מה חושב מה.
            </li>
            <li>
              <b className="text-[var(--dk-ink)]">אין מקביליות בתוך כתבה.</b>{" "}
              חלונות ותגובות של אותה כתבה מעובדים בסדר קבוע.
            </li>
            <li>
              <b className="text-[var(--dk-ink)]">אין זמן בחישוב.</b> שום מדד
              אינו תלוי בשעת ההרצה.
            </li>
          </ul>
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="הגבול: מה השכבה הזו לא רואה">
          <div className="flex flex-col gap-2">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              ספירת מילים אינה מבינה מי המבצע, למי מיוחסת האחריות, או מה נאמר
              בקול סביל. שתי כתבות על אותו אירוע יכולות לקבל ספירה כמעט זהה
              ולמסגר אותו הפוך.
            </p>
            {w && (
              <div className="rounded-xl border border-[var(--dk-warn)]/30 bg-[var(--dk-warn)]/6 p-3">
                <div
                  className="text-3xl font-black text-[var(--dk-warn)]"
                  dir="ltr"
                >
                  {Math.round((w.null_dominance / w.total) * 100)}%
                </div>
                <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                  מהחלונות אינם מכילים אף מילת לקסיקון. עבורם לשכבה הדטרמיניסטית
                  אין <b>שום</b> מה לומר — וזה נשמר כ־NULL ולא כאפס, כי ״לא
                  נמדד״ אינו ״נמדד ויצא אפס״.
                </p>
              </div>
            )}
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              זה הפער שמצדיק את שכבת ה־AI בהמשך — ובדיוק בגללו היא מגיעה עם מאמת
              דטרמיניסטי שפוסל כל ביטוי שלא נמצא בטקסט שהמודל קרא.
            </p>
          </div>
        </Panel>

        <Panel title="שתי השכבות זו מול זו">
          <div className="grid grid-cols-2 gap-2">
            <Node
              title="לקסיקון"
              tone="good"
              sub="אותו קלט → אותו פלט, תמיד · ניתן להסבר מילה־מילה · עיוור למסגור"
            />
            <Node
              title="מודל שפה"
              tone="accent"
              sub="קורא מסגור וקול · אינו מבטיח שחזור · חייב אימות חיצוני"
            />
          </div>
        </Panel>
      </div>
    </div>
  );
}
