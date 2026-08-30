"use client";

import { useState } from "react";
import type { Facts, RetrievalNeighbour } from "./facts";
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
  { id: "why", label_he: "למה מילים נכשלות" },
  { id: "index", label_he: "האינדקס" },
  { id: "cut", label_he: "הסף" },
  { id: "walk", label_he: "אירוע אחד, צעד־צעד" },
  { id: "limits", label_he: "מה זה לא עושה" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the retrieval layer — the first place in the system where a
 * learned model earns its keep.
 *
 * The whole module is built around one measurement: how many versions of the
 * same event a keyword baseline would have found. That number is recomputed
 * from the snapshot by demo/snapshot/build_explainer_facts.py, together with
 * the threshold sweep — so the table on the wall is the experiment itself,
 * not a remembered result.
 */
export function RetrievalModule({ facts }: Props) {
  const [tab, setTab] = useState("why");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "why" && <WhyWords facts={facts} />}
      {tab === "index" && <IndexPanel facts={facts} />}
      {tab === "cut" && <Cut facts={facts} />}
      {tab === "walk" && <Walk facts={facts} />}
      {tab === "limits" && <Limits facts={facts} />}
    </div>
  );
}

function pct(x: number): string {
  return `${(x * 100).toFixed(0)}%`;
}

/** A big number with a caption — the module's only "headline" element. */
function Big({
  value,
  label,
  tone = "accent",
}: {
  value: string;
  label: string;
  tone?: "accent" | "bad" | "good";
}) {
  const colors = {
    accent: "text-[var(--dk-accent)]",
    bad: "text-[var(--dk-bad)]",
    good: "text-[var(--dk-good)]",
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

/* ── 1. why a keyword search fails ──────────────────────────────── */

function WhyWords({ facts }: Props) {
  const r = facts?.retrieval;
  const k = r?.keyword;
  const maxJ = Math.max(1, ...(k?.histogram.map((b) => b.n) ?? [1]));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[48%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="הבעיה: אותו אירוע, אפס מילים משותפות">
          <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
            כדי להשוות מסגור בין ערוצים צריך קודם לדעת מי סיקר את אותו סיפור.
            בעברית זה לא עובד לפי מילים: לכל מערכת יש בחירת מילים משלה, ולכן שתי
            כותרות על אותו אירוע יכולות לא לחלוק אף מילה — לא בגלל שהן על נושאים
            שונים, אלא בגלל שכל אחת בחרה זווית אחרת.
          </p>
        </Panel>

        <Panel
          title="הבסיס המילולי שמדדנו מולו"
          hint="demo/core/framing.py · keyword_jaccard"
        >
          <div className="flex flex-col gap-2.5">
            <div
              dir="ltr"
              className="rounded-lg border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)]/40 px-3 py-2 text-center font-mono text-[16px] text-[var(--dk-accent)]"
            >
              J(a,b) = |tokens(a) ∩ tokens(b)| / |tokens(a) ∪ tokens(b)|
            </div>
            <p className="text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
              טוקנים עבריים באורך 3+ מהכותרת. נחשב &quot;נמצא&quot; אם{" "}
              <span dir="ltr" className="font-mono">
                J ≥ {r?.keyword_jaccard ?? 0.25}
              </span>{" "}
              — סף נדיב: הוא מספיק ששליש מהמילים יחפפו.
            </p>
          </div>
        </Panel>

        {k && (
          <div className="grid grid-cols-3 gap-2">
            <Big value={`${k.found}/${k.total}`} label="גרסאות שחיפוש מילולי מוצא" tone="bad" />
            <Big value={pct(k.recall)} label="שיעור האחזור המילולי" tone="bad" />
            <Big
              value={String(k.zero_overlap)}
              label="זוגות כותרות בלי אף מילה משותפת"
            />
          </div>
        )}
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="חפיפת מילים בין גרסאות של אותו אירוע"
          hint={k ? `${k.total} זוגות · חציון J = ${k.median}` : undefined}
        >
          {k ? (
            <div className="flex flex-col gap-2">
              {k.histogram.map((b) => (
                <div key={b.label} className="flex-1">
                  <BarRow
                    label={b.label}
                    n={b.n}
                    max={maxJ}
                    tone={b.label === "0.25+" ? "good" : "bad"}
                    note={b.label === "0.25+" ? "נמצא מילולית" : undefined}
                  />
                </div>
              ))}
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        {k && r && (
          <Panel title="ברמת האירוע">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              ב־
              <b className="text-[var(--dk-bad)]">{k.blind_events}</b> מתוך{" "}
              <b>{r.events.total}</b> האירועים בסנאפשוט, חיפוש מילולי לא היה מוצא
              אף גרסה נוספת — כלומר האירוע כולו לא היה קיים כאירוע. זה לא כשל של
              מימוש מסוים; זה מה שקורה כשמזהים סיפור לפי מחרוזות.
            </p>
          </Panel>
        )}

        <Caveat>
          77 הזוגות האלה הוגדרו על ידי האחזור הסמנטי עצמו, ולכן הוא מוצא 100%
          מהם בהגדרה. המספר שאפשר לטעון עליו הוא רק זה: מבין הזוגות שהאמבדינגים
          מצאו, חיפוש מילולי היה משחזר {k ? pct(k.recall) : "כ־22%"}. זו לא מדידה
          על ground truth ידני.
        </Caveat>
      </div>
    </div>
  );
}

/* ── 2. the index ───────────────────────────────────────────────── */

function IndexPanel({ facts }: Props) {
  const r = facts?.retrieval;
  const maxArticles = Math.max(1, ...(r?.corpus.per_source.map((s) => s.articles) ?? [1]));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[52%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="מה נכנס לווקטור"
          hint="demo/snapshot/prepare_demo.py · passage_text"
        >
          <div className="flex flex-col gap-2">
            <Node
              title="כותרת + פתיח הכתבה"
              sub={
                <>
                  {r?.passage_lead_chars ?? 400} תווים ראשונים מהגוף. הפתיח מספיק
                  כדי לקבע על איזה אירוע מדובר; גוף מלא היה מוסיף פרשנות ומטשטש
                  את ההבדל בין אירועים.
                </>
              }
            />
            <Node
              title='קידומת "passage: " / "query: "'
              mono
              sub="e5 אומן עם הקידומות האלה. בלעדיהן הווקטורים עדיין מתקבלים — פשוט פחות טובים. זו דרישה של המודל, לא קישוט."
            />
            <Node
              title="נרמול L2 לאורך 1"
              sub="ולכן קוסינוס = מכפלה סקלרית. אין חלוקה בזמן שאילתה, ואין דרך שגודל הווקטור יזלוג לתוך הציון."
            />
          </div>
        </Panel>

        <Panel title="למה מטריצת numpy ולא בסיס נתונים וקטורי">
          <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
            בגודל הזה שאילתה היא מכפלת מטריצה אחת:{" "}
            <b dir="ltr" className="font-mono text-[var(--dk-accent)]">
              {r ? `${r.query_ms.toFixed(3)} ms` : "≈0.01 ms"}
            </b>{" "}
            למדידה מלאה על כל האינדקס. אינדקס משוער (HNSW ודומיו) היה מחליף
            תוצאה מדויקת בקירוב — ומכניס תהליך נוסף שיכול ליפול באמצע התערוכה.
            הקיוסק לא צריך את זה.
          </p>
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="האינדקס בפועל">
          {r ? (
            <div className="grid grid-cols-2 gap-2">
              <Big value={r.vectors.toLocaleString("en-US")} label="ווקטורים" />
              <Big value={String(r.dims)} label="ממדים לווקטור" />
              <Big
                value={`${(r.bytes / 1024 / 1024).toFixed(2)} MB`}
                label="גודל האינדקס בזיכרון"
              />
              <Big value={`${r.query_ms.toFixed(3)} ms`} label="שאילתה מלאה" tone="good" />
              <div className="col-span-2 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-3 py-2 text-center">
                <code dir="ltr" className="font-mono text-[15px] text-[var(--dk-ink)]">
                  {r.model}
                </code>
                <div className="text-[13px] text-[var(--dk-ink-3)]">
                  רץ אופליין פעם אחת בזמן ההכנה — הקיוסק לא טוען מודל
                </div>
              </div>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel
          title="מי נכנס לאינדקס"
          hint={
            r
              ? `${r.corpus.indexed} מתוך ${r.corpus.total} כתבות · סף ${r.corpus.total - r.corpus.indexed === r.corpus.too_short ? "" : ""}${r.min_text_chars} תווים`
              : undefined
          }
        >
          {r ? (
            <div className="flex flex-col gap-2">
              {r.corpus.per_source.map((s) => (
                <div key={s.source} className="flex items-center gap-2">
                  <span className="w-[68px] shrink-0 text-[14px] text-[var(--dk-ink-2)]">
                    {s.source_he}
                  </span>
                  <div className="h-4 flex-1 overflow-hidden rounded-md bg-[var(--dk-surface-2)]">
                    <div
                      className="h-full bg-[var(--dk-ink-3)]/50"
                      style={{ width: `${(s.articles / maxArticles) * 100}%` }}
                    >
                      <div
                        className="h-full rounded-e-md bg-[var(--dk-accent)]"
                        style={{
                          width: `${(s.indexed / Math.max(s.articles, 1)) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                  <span
                    dir="ltr"
                    className="w-[86px] shrink-0 text-left font-mono text-[13.5px] text-[var(--dk-ink-2)]"
                  >
                    {s.indexed}/{s.articles}
                  </span>
                </div>
              ))}
              <p className="mt-1 text-[14px] leading-snug text-[var(--dk-ink-2)]">
                כתבה מתחת ל־{r.min_text_chars} תווים לא נכנסת: אין לה פתיח שאפשר
                לעגן עליו. זו בדיוק החתיכה שנחתכה במודול האיסוף — הארץ מגיע
                קטוע מהפיי־וול, ולכן {r.corpus.per_source.find((s) => s.source === "haaretz")?.indexed ?? 82}{" "}
                מתוך {r.corpus.per_source.find((s) => s.source === "haaretz")?.articles ?? 235}{" "}
                מהכתבות שלו בכלל מגיעות לשלב הזה.
              </p>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>
    </div>
  );
}

/* ── 3. the threshold ───────────────────────────────────────────── */

function Cut({ facts }: Props) {
  const r = facts?.retrieval;
  const sim = r?.similarity;
  const maxBucket = Math.max(1, ...(sim?.histogram.map((b) => b.n) ?? [1]));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[50%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="ציון קוסינוס בפני עצמו לא אומר כלום"
          hint={sim ? `${sim.pairs.toLocaleString("en-US")} זוגות בסנאפשוט` : undefined}
        >
          {sim ? (
            <div className="flex flex-col gap-2">
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                החציון של <em>כל</em> זוג כתבות במאגר הוא{" "}
                <b dir="ltr" className="font-mono text-[var(--dk-accent)]">
                  {sim.median}
                </b>
                . כלומר 0.80 הוא &quot;שתי כתבות חדשותיות בעברית&quot;, לא
                &quot;אותו סיפור&quot;. מה שקובע זה איפה הערך יושב בהתפלגות.
              </p>
              {sim.histogram.map((b) => (
                <div key={b.label} className="flex-1">
                  <BarRow
                    label={b.label}
                    n={b.n}
                    max={maxBucket}
                    tone={
                      b.label === "0.90-0.95" || b.label === "0.95-1.00"
                        ? "good"
                        : "muted"
                    }
                  />
                </div>
              ))}
            </div>
          ) : (
            <Missing />
          )}
        </Panel>

        {sim && r && (
          <Panel title="הסף שנבחר במונחי אחוזון">
            <div className="flex flex-wrap items-center gap-2">
              {sim.above.map((a) => (
                <Chip
                  key={a.threshold}
                  tone={a.threshold === r.cluster_sim ? "accent" : "neutral"}
                >
                  <span dir="ltr" className="font-mono">
                    ≥{a.threshold} → {a.pct}%
                  </span>
                </Chip>
              ))}
            </div>
            <p className="mt-2 text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
              הסף {r.cluster_sim} משאיר את{" "}
              {sim.above.find((a) => a.threshold === r.cluster_sim)?.pct}% העליונים
              של כל הזוגות. זה מה שהופך אותו לסף ולא לקירוב.
            </p>
          </Panel>
        )}
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="סריקת הסף — מה כל ערך עולה"
          hint="נמדד מחדש בכל בנייה, לא זיכרון"
        >
          {r ? (
            <table className="w-full text-[15px]">
              <thead>
                <tr className="text-[13.5px] text-[var(--dk-ink-3)]">
                  <th className="pb-1.5 text-right font-normal">סף</th>
                  <th className="pb-1.5 text-right font-normal">אירועים</th>
                  <th className="pb-1.5 text-right font-normal">גרסאות</th>
                  <th className="pb-1.5 text-right font-normal">עם 3+ ערוצים</th>
                </tr>
              </thead>
              <tbody>
                {r.sweep.map((row) => (
                  <tr
                    key={row.threshold}
                    className={
                      row.chosen
                        ? "bg-[var(--dk-accent-dim)]/50 text-[var(--dk-accent)]"
                        : "text-[var(--dk-ink-2)]"
                    }
                  >
                    <td dir="ltr" className="py-1 text-right font-mono font-bold">
                      {row.threshold.toFixed(2)}
                      {row.chosen ? " ←" : ""}
                    </td>
                    <td dir="ltr" className="py-1 text-right font-mono">
                      {row.events}
                    </td>
                    <td dir="ltr" className="py-1 text-right font-mono">
                      {row.versions}
                    </td>
                    <td
                      dir="ltr"
                      className={`py-1 text-right font-mono ${
                        row.three_plus === 0 && !row.chosen
                          ? "text-[var(--dk-bad)]"
                          : ""
                      }`}
                    >
                      {row.three_plus}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Missing />
          )}
        </Panel>

        <Panel title="למה 0.90 ולא נמוך יותר">
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            0.84 היה נותן יותר אירועים עם שלושה ערוצים — אבל האשכולות שם כבר לא
            אירוע אחד אלא &quot;כל מה שקשור לאיראן&quot;, וההשוואה בין ערוצים
            מאבדת משמעות כשהיא רצה על סיפורים שונים. 0.92 ומעלה שומר על טוהר
            ומאבד את ההשוואה לגמרי: אפס אירועים עם שלושה ערוצים. 0.90 הוא
            הבחירה, והטבלה משמאל היא מה שהיא עלתה.
          </p>
        </Panel>

        <Caveat>
          הגבול בין &quot;אירוע אחד&quot; ל&quot;סיפור מתגלגל&quot; נקבע בעין,
          לא במדד. הטבלה מראה את ההשלכה המספרית של כל ערך; היא לא מוכיחה
          ש־0.90 הוא הנכון.
        </Caveat>
      </div>
    </div>
  );
}

/* ── 4. one event, step by step ─────────────────────────────────── */

function Walk({ facts }: Props) {
  const r = facts?.retrieval;
  const ex = r?.example;

  if (!ex || !r) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        <Panel title="אירוע לדוגמה">
          <Missing />
        </Panel>
      </div>
    );
  }

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[1fr_31%] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-2.5">
        <Panel
          title="נקודת המוצא"
          hint={ex.topic_he ? `נושא האירוע: ${ex.topic_he}` : undefined}
        >
          <div className="flex items-center gap-3">
            <Chip tone="accent">{ex.seed.source_he}</Chip>
            <span className="text-[17px] font-bold leading-snug">
              {ex.seed.title}
            </span>
          </div>
        </Panel>

        <div className="flex flex-col gap-2">
          {ex.neighbours.map((n, i) => (
            <NeighbourRow key={n.title} n={n} rank={i + 1} />
          ))}
          {ex.rejected && (
            <div className="flex items-stretch gap-2.5 rounded-xl border border-dashed border-[var(--dk-border)] px-3 py-2 opacity-60">
              <div
                dir="ltr"
                className="flex w-[76px] shrink-0 flex-col items-center justify-center"
              >
                <span className="font-mono text-[17px] font-bold text-[var(--dk-ink-3)]">
                  {ex.rejected.cos}
                </span>
                <span className="text-[11.5px] text-[var(--dk-ink-3)]">cos</span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <Chip tone="bad">מתחת לסף — נעצר כאן</Chip>
                  <span className="text-[13.5px] text-[var(--dk-ink-3)]">
                    {ex.rejected.source_he}
                  </span>
                </div>
                <div className="mt-0.5 truncate text-[14.5px] text-[var(--dk-ink-2)]">
                  {ex.rejected.title}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="איך לקרוא את השורות">
          <div className="flex flex-col gap-2 text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
            <div>
              <b dir="ltr" className="font-mono text-[var(--dk-accent)]">
                cos
              </b>{" "}
              — קרבה סמנטית לנקודת המוצא. הסריקה עוצרת ברגע שהיא יורדת אל מתחת
              ל־{r.cluster_sim}.
            </div>
            <div>
              <b dir="ltr" className="font-mono text-[var(--dk-bad)]">
                J
              </b>{" "}
              — חפיפת המילים. השורה הראשונה כאן היא אותו סיפור עם{" "}
              <b>אפס</b> מילים משותפות.
            </div>
          </div>
        </Panel>

        <Panel title="כלל גרסה אחת לכל ערוץ" hint="_one_per_source">
          <p className="text-[14.5px] leading-relaxed text-[var(--dk-ink-2)]">
            שתי שורות כאן עברו את הסף ובכל זאת ירדו: הערוץ שלהן כבר תרם גרסה.
            זה לא ניקיון קוסמטי — כל השוואה בהמשך היא מול <b>חציון האירוע</b>,
            וערוץ שתורם שלוש גרסאות מתוך חמש הופך בעצמו לחציון ומודד סטייה אפס
            מעצמו.
          </p>
        </Panel>

        <Caveat>
          שורה 4 עברה את הסף ואינה אותו סיפור. כלל גרסה־אחת־לערוץ הסיר אותה
          כאן במקרה, לא בגלל שהמערכת זיהתה טעות. סף על קוסינוס לא יודע להבחין
          בין &quot;אותו אירוע&quot; ל&quot;אותו תחום&quot;.
        </Caveat>
      </div>
    </div>
  );
}

function NeighbourRow({ n, rank }: { n: RetrievalNeighbour; rank: number }) {
  return (
    <div
      className={`flex items-stretch gap-2.5 rounded-xl border px-3 py-2 ${
        n.kept
          ? "border-[var(--dk-good)]/40 bg-[var(--dk-good)]/6"
          : "border-[var(--dk-border)] bg-[var(--dk-surface-2)]/40"
      }`}
    >
      <div className="flex w-[76px] shrink-0 flex-col items-center justify-center">
        <span
          dir="ltr"
          className="font-mono text-[17px] font-bold text-[var(--dk-accent)]"
        >
          {n.cos}
        </span>
        <span className="text-[11.5px] text-[var(--dk-ink-3)]">cos</span>
      </div>
      <div
        className={`flex w-[64px] shrink-0 flex-col items-center justify-center rounded-lg ${
          n.jaccard === 0 ? "bg-[var(--dk-bad)]/12" : ""
        }`}
      >
        <span
          dir="ltr"
          className={`font-mono text-[16px] font-bold ${
            n.jaccard === 0 ? "text-[var(--dk-bad)]" : "text-[var(--dk-ink-2)]"
          }`}
        >
          {n.jaccard.toFixed(3)}
        </span>
        <span className="text-[11.5px] text-[var(--dk-ink-3)]">J</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[12.5px] text-[var(--dk-ink-3)]" dir="ltr">
            #{rank}
          </span>
          <Chip tone={n.kept ? "good" : "warn"}>
            {n.kept ? `${n.source_he} · נכנס לאירוע` : `${n.source_he} · ירד`}
          </Chip>
          {!n.kept && (
            <span className="text-[13px] text-[var(--dk-ink-3)]">
              הערוץ כבר תרם גרסה
            </span>
          )}
        </div>
        <div className="mt-0.5 text-[15px] leading-snug">{n.title}</div>
        <div className="mt-0.5 text-[13px] text-[var(--dk-ink-3)]">
          מילים משותפות:{" "}
          {n.shared.length ? (
            n.shared.join(" · ")
          ) : (
            <b className="text-[var(--dk-bad)]">אין</b>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── 5. limits ──────────────────────────────────────────────────── */

function Limits({ facts }: Props) {
  const r = facts?.retrieval;
  const dup = r?.duplicates;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[52%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="מה האינדקס גילה על שכבת הזהות"
          hint={dup ? `${dup.pairs} זוגות בקוסינוס ${dup.threshold}+` : undefined}
        >
          {dup && dup.examples.length ? (
            <div className="flex flex-col gap-2">
              <p className="text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
                <CodeRef path="article_id = sha256(canonical_url)" /> היא זהות של
                כתובת, לא של תוכן. אותה כתבה בדיוק, שמוגשת בשני נתיבים באתר, היא
                שתי שורות במסד. האמבדינגים לא מתקנים את זה — הם הופכים את זה
                לגלוי:
              </p>
              {dup.examples.map((d) => (
                <div
                  key={d.id_a}
                  className="rounded-xl border border-[var(--dk-warn)]/35 bg-[var(--dk-warn)]/6 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <Chip tone="warn">
                      <span dir="ltr" className="font-mono">
                        cos {d.cos}
                      </span>
                    </Chip>
                    <span className="truncate text-[14px] text-[var(--dk-ink-2)]">
                      {d.title}
                    </span>
                  </div>
                  <UrlDiff a={d.url_a} b={d.url_b} />
                </div>
              ))}
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="שלוש מגבלות שלא נסגרו">
          <div className="flex flex-col gap-2.5">
            <Node
              title="אשכול חמדני, תלוי סדר"
              tone="bad"
              sub="הסריקה עוברת על הכתבות לפי מזהה וכל אחת נתפסת על ידי האשכול הראשון שקלט אותה. זה דטרמיניסטי — אותו קלט תמיד אותו פלט — אבל לא אופטימלי: סדר אחר היה יכול לתת חלוקה אחרת."
            />
            <Node
              title="אין חלון זמן"
              tone="bad"
              sub="שתי כתבות דומות מאוד בהפרש של שבועיים יאושכלו יחד. בסנאפשוט הזה הטווח קצר ולכן זה כמעט לא קורה, אבל שום דבר בקוד לא מונע את זה."
            />
            <Node
              title="הסף לא מבחין בין אירוע לתחום"
              tone="bad"
              sub="קוסינוס מודד קרבה סמנטית, לא זהות אירוע. שתי כתבות שונות על אותו סכסוך יכולות לעבור את הסף — ראו את שורה 4 בלשונית הקודמת."
            />
          </div>
        </Panel>

        <Panel title="מה כן מותר לומר מכאן">
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            שהאחזור הסמנטי מייצר{" "}
            <b>{r ? r.events.total : "—"}</b> קבוצות של כתבות שרובן המכריע הוא
            באמת אותו סיפור, ושחיפוש מילולי לא היה מייצר אותן. לא שהחלוקה
            מושלמת, ולא שכל אירוע במציאות נתפס — רק שזה השלב שבו המודל הלמוד
            עושה עבודה שהשכבה הדטרמיניסטית לא יכולה לעשות.
          </p>
        </Panel>
      </div>
    </div>
  );
}

/**
 * Two URLs with only the part that differs highlighted.
 *
 * These paths are long and nearly identical, and a truncated pair proves
 * nothing — the whole claim is *which* segment differs, so that segment is
 * the one thing that must survive on a wall screen.
 */
function UrlDiff({ a, b }: { a: string; b: string }) {
  let head = 0;
  while (head < a.length && head < b.length && a[head] === b[head]) head += 1;
  let tail = 0;
  while (
    tail < a.length - head &&
    tail < b.length - head &&
    a[a.length - 1 - tail] === b[b.length - 1 - tail]
  )
    tail += 1;

  const render = (url: string) => (
    <span className="break-all">
      <span className="opacity-55">{url.slice(0, head)}</span>
      <mark className="rounded bg-[var(--dk-warn)]/25 px-0.5 text-[var(--dk-warn)]">
        {url.slice(head, url.length - tail) || "∅"}
      </mark>
      <span className="opacity-55">{url.slice(url.length - tail)}</span>
    </span>
  );

  return (
    <div
      dir="ltr"
      className="mt-1 flex flex-col gap-0.5 font-mono text-[12px] text-[var(--dk-ink-3)]"
    >
      {render(a)}
      {render(b)}
    </div>
  );
}

/* ── shared ────────────────────────────────────────────── */

function Missing() {
  return (
    <p className="text-[15px] text-[var(--dk-ink-3)]">
      אין קובץ מדידות — הדיאגרמות מוצגות בלי המספרים.
    </p>
  );
}
