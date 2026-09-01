"use client";

import { useState } from "react";
import type { Facts, RetrievalNeighbour } from "./facts";
import { BarRow, Caveat, Chip, Panel, Stage, SubNav, type TabDef } from "./kit";

const TABS: TabDef[] = [
  { id: "why", label_he: "איך מזהים אותו סיפור" },
  { id: "how", label_he: "האינדקס והסף שנבחר" },
  { id: "eval", label_he: "כמה מזה נכון" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: how the system knows that two outlets covered the same event.
 *
 * Two tabs, four panels. First the decision — match on meaning rather than on
 * shared words — with the measurement that justifies it and one real pair of
 * headlines that share nothing. Then what it costs to run: the model is local,
 * the index is a matrix in memory, and the cutoff was picked off a sweep.
 *
 * Everything here is bounded in the sentence itself. The 77 pairs were found
 * by this retriever, so every claim about them says "of the cases the system
 * found" — there is no manual ground truth and the screen never implies one.
 *
 * The third tab grades the first two. The sweep in "how" picks 0.90 off event
 * counts, which says nothing about whether the events are right; the eval says
 * how often they are, against 160 pairs sampled independently of what the
 * retriever returned (demo/evals/golden/). It reports a number that makes the
 * system look worse, because the alternative is a screen that only measures
 * what it already found.
 *
 * Dropped on purpose (see demo/README.md items 44-46, 54): the bounded-index
 * eviction replay. It measures a problem this corpus does not have yet, and a
 * tab of hypotheticals is volume, not depth.
 */
export function RetrievalModule({ facts }: Props) {
  const [tab, setTab] = useState("why");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "why" && <SameStory facts={facts} />}
      {tab === "how" && <IndexAndCut facts={facts} />}
      {tab === "eval" && <Measured facts={facts} />}
    </div>
  );
}

function num(x: number): string {
  return x.toLocaleString("en-US");
}

function pct(x: number): string {
  return `${(x * 100).toFixed(0)}%`;
}

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
    <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-2.5 py-3 text-center">
      <div className={`text-[38px] font-black leading-[1.1] ${colors[tone]}`} dir="ltr">
        {value}
      </div>
      <div className="mt-1.5 text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
        {label}
      </div>
    </div>
  );
}

/* ── 1. same story, different words ─────────────────────────────── */

function SameStory({ facts }: Props) {
  const r = facts?.retrieval;
  const k = r?.keyword;
  const ex = r?.example;
  const maxJ = Math.max(1, ...(k?.histogram.map((b) => b.n) ?? [1]));

  return (
    <Stage cols="grid-cols-[45%_1fr]">
      <Panel
        title={
          k
            ? `ב־${k.total - k.found} מתוך ${k.total} המקרים אין מספיק מילים כדי לחבר`
            : "מילים משותפות מול משמעות"
        }
      >
        {k && r ? (
          <div className="flex flex-col gap-4">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              כששני ערוצים מדווחים על אותו אירוע, המערכת צריכה לדעת שאלה אותן
              חדשות. הדרך הזולה היא להשוות את המילים בכותרות: אם שתי כותרות
              חולקות מספיק מילים, זה כנראה אותו סיפור. לקחנו {k.total} מקרים
              אמיתיים שבהם שני ערוצים סיקרו את אותו אירוע, ובדקנו כמה מהם הדרך
              הזאת הייתה מחברת.
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              <Big
                value={`${k.found}/${k.total}`}
                label="מקרים שהדרך הזאת מחברת"
                tone="bad"
              />
              <Big
                value={String(k.zero_overlap)}
                label="מקרים בלי אף מילה משותפת"
                tone="bad"
              />
            </div>
            <div className="flex flex-col gap-2.5">
              {k.histogram.map((b, i) => {
                // The top bucket starts at the keyword threshold, so it is the
                // only one a word search would have called a match.
                const found = i === k.histogram.length - 1;
                return (
                  <BarRow
                    key={b.label}
                    label={b.label}
                    n={b.n}
                    max={maxJ}
                    tone={found ? "good" : "bad"}
                    note={found ? "מספיק כדי לחבר" : undefined}
                  />
                );
              })}
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-3)]">
              כמה מהמילים בשתי הכותרות משותפות: ‏0 = אין אף מילה, ‏1 = אותן
              מילים בדיוק. במקרה החציוני משותפות {pct(k.median ?? 0)} מהן.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              לכן ההשוואה כאן היא בין המשמעות של הכותרות ולא בין המילים שבהן.
              ‏{k.blind_events} מתוך {r.events.total} האירועים שהמערכת בנתה לא
              היו נמצאים אחרת, ואיתם ההשוואה בין הערוצים עליהם.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="אותו סיפור, אפס מילים משותפות"
        hint="קרבה: 0 = אין קשר, 1 = זהה · מילים: החלק המשותף לשתי הכותרות"
      >
        {ex && r ? (
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center gap-3 rounded-xl border border-[var(--dk-accent)]/30 bg-[var(--dk-accent-dim)]/30 px-3 py-2.5">
              <Chip tone="accent">נקודת המוצא</Chip>
              <span className="text-[13.5px] text-[var(--dk-ink-3)]">
                {ex.seed.source_he}
              </span>
              <span className="min-w-0 flex-1 text-[16.5px] font-bold leading-snug">
                {ex.seed.title}
              </span>
            </div>

            {ex.neighbours.map((n, i) => (
              <NeighbourRow key={n.title} n={n} rank={i + 1} />
            ))}

            {ex.rejected && (
              <div className="flex items-stretch gap-2.5 rounded-xl border border-dashed border-[var(--dk-border)] px-3 py-2.5 opacity-60">
                <div
                  dir="ltr"
                  className="flex w-[76px] shrink-0 flex-col items-center justify-center"
                >
                  <span className="font-mono text-[17px] font-bold text-[var(--dk-ink-3)]">
                    {ex.rejected.cos}
                  </span>
                  <span className="text-[11.5px] text-[var(--dk-ink-3)]">
                    קרבה
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Chip tone="bad">
                      מתחת ל־{r.cluster_sim.toFixed(2)} — נעצר כאן
                    </Chip>
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

            <p className="mt-1 text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              השורה הראשונה מדברת על אותו אירוע בדיוק כמו נקודת המוצא, בלי מילה
              אחת משותפת. השורה האחרונה עוסקת בנושא קרוב ונעצרת מתחת לסף.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              מכל ערוץ נכנסת לאירוע גרסה אחת. אחרת ערוץ שפרסם שלוש כתבות על
              אותו אירוע היה נמדד מול עצמו, וההשוואה בין הערוצים הייתה נוטה
              לטובתו.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

function NeighbourRow({ n, rank }: { n: RetrievalNeighbour; rank: number }) {
  return (
    <div
      className={`flex items-stretch gap-2.5 rounded-xl border px-3 py-2.5 ${
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
        <span className="text-[11.5px] text-[var(--dk-ink-3)]">קרבה</span>
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
        <span className="text-[11.5px] text-[var(--dk-ink-3)]">מילים</span>
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

/* ── 2. what it costs to run, and where the line sits ───────────── */

function IndexAndCut({ facts }: Props) {
  const r = facts?.retrieval;
  const sim = r?.similarity;
  const haaretz = r?.corpus.per_source.find((s) => s.source === "haaretz");

  const chosen = r?.sweep.find((s) => s.chosen);
  const loose = r?.sweep.reduce((a, b) => (b.events > a.events ? b : a));
  const tight = r?.sweep.find((s) => chosen && s.threshold > chosen.threshold);
  const atCut = sim?.above.find((a) => a.threshold === r?.cluster_sim);

  return (
    <Stage cols="grid-cols-[47%_1fr]">
      <Panel title="המודל רץ על המחשב הזה, ולכן אין חשבון">
        {r ? (
          <div className="flex flex-col gap-4">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              המודל מתרגם כל כתבה — הכותרת ו־{r.passage_lead_chars} התווים
              הראשונים — ל־{r.dims} מספרים שמתארים את המשמעות שלה. שתי כתבות על
              אותו אירוע מקבלות מספרים דומים, גם כשהמילים שונות לגמרי.
            </p>
            <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-3 py-2.5 text-center">
              <code dir="ltr" className="font-mono text-[15.5px] text-[var(--dk-ink)]">
                {r.model}
              </code>
              <div className="text-[13.5px] text-[var(--dk-ink-3)]">
                רץ פעם אחת בהכנה — הקיוסק לא טוען מודל ולא מחייג החוצה
              </div>
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              מודל בתשלום דרך API היה גובה על כל כתבה, בכל פעם שהאינדקס נבנה
              מחדש, והיה מחייב רשת בחדר. כאן הבנייה המלאה עולה אפס והמסך עובד
              גם בלי חיבור.
            </p>
            <div className="grid grid-cols-3 gap-2.5">
              <Big value={num(r.vectors)} label="כתבות באינדקס" />
              <Big
                value={`${(r.bytes / 1024 / 1024).toFixed(2)} MB`}
                label="כל האינדקס בזיכרון"
              />
              <Big
                value={`${r.query_ms.toFixed(3)} ms`}
                label="חיפוש שעובר על כולו"
                tone="good"
              />
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              בגודל הזה חיפוש עובר על כל האינדקס ומחזיר תשובה מדויקת. בסיס
              נתונים וקטורי קיים כדי לקרב תשובה כשאי אפשר לעבור על הכל — כאן
              הוא היה מוסיף שירות שיכול ליפול מול קהל, בתמורה לקירוב.
            </p>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-3)]">
              נכנסת כתבה עם פתיח של {r.min_text_chars} תווים לפחות:{" "}
              {r.corpus.indexed} מתוך {r.corpus.total}
              {haaretz ? `, ובהארץ ${haaretz.indexed} מתוך ${haaretz.articles}` : ""}
              . לכותרת לבדה אין מספיק הקשר כדי להשוות אותה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="כמה קרוב זה כבר אותו אירוע"
        hint="קרבה נמדדת מ־0 (אין קשר) עד 1 (אותה כתבה)"
      >
        {r && sim && chosen && loose && tight && atCut ? (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-2.5">
              <Big value={chosen.threshold.toFixed(2)} label="הסף שנבחר" />
              <Big
                value={`${atCut.pct}%`}
                label={`מ־${num(sim.pairs)} הזוגות עוברים אותו`}
                tone="good"
              />
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              הסף הוא המספר שמפריד בין &rdquo;אותו אירוע&ldquo; ל&rdquo;נושא
              קרוב&ldquo;. הוא נקבע מול
              הטבלה הזאת, אחרי שכל ערך נוסה על הקורפוס המלא.
            </p>
            <table className="w-full text-[16px]">
              <thead>
                <tr className="text-[14px] text-[var(--dk-ink-3)]">
                  <th className="pb-2 text-right font-normal">סף</th>
                  <th className="pb-2 text-right font-normal">אירועים</th>
                  <th className="pb-2 text-right font-normal">גרסאות</th>
                  <th className="pb-2 text-right font-normal">עם 3+ ערוצים</th>
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
                    <td dir="ltr" className="py-1.5 text-right font-mono font-bold">
                      {row.threshold.toFixed(2)}
                      {row.chosen ? " ←" : ""}
                    </td>
                    <td dir="ltr" className="py-1.5 text-right font-mono">
                      {row.events}
                    </td>
                    <td dir="ltr" className="py-1.5 text-right font-mono">
                      {row.versions}
                    </td>
                    <td
                      dir="ltr"
                      className={`py-1.5 text-right font-mono ${
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
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-3)]">
              כל שורה היא ערך סף שנוסה על הקורפוס המלא. ‏<b>אירועים</b> — כמה
              קבוצות של כתבות נוצרו; <b>גרסאות</b> — כמה כתבות נכנסו לתוכן;{" "}
              <b>עם 3+ ערוצים</b> — כמה מהאירועים סוקרו בשלושה ערוצים ומעלה,
              והם היחידים שאפשר להשוות עליהם ערוץ מול ערוץ.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              רף נמוך יותר ({loose.threshold.toFixed(2)}) מוסיף{" "}
              {loose.events - chosen.events} אירועים, אבל בולע סיפור מתגלגל שלם
              לתוך אירוע אחד. רף גבוה יותר ({tight.threshold.toFixed(2)}) משאיר{" "}
              {tight.three_plus} אירועים שסוקרו בשלושה ערוצים, ובלי שלושה
              ערוצים אין מה להשוות.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

/* ── 3. how often the threshold is right ────────────────────────── */

function Measured({ facts }: Props) {
  const e = facts?.evals;
  const g = e?.golden_set;
  const live = e?.precision_sweep.find((r) => r.threshold === e.live_threshold);
  const tightest = e?.precision_sweep[0];
  const liveRecall = e?.recall.by_threshold.find(
    (r) => r.threshold === e.live_threshold,
  );
  const tightRecall = e?.recall.by_threshold.find(
    (r) => tightest && r.threshold === tightest.threshold,
  );
  const emb = e?.head_to_head.embedding;
  const kw = e?.head_to_head.keyword;

  return (
    <Stage cols="grid-cols-[52%_1fr]">
      <Panel
        title={
          live
            ? `בסף החי, ‏${live.true_positives} מתוך ${live.labelled_accepted} הזוגות שהמערכת מחברת הם אותו אירוע`
            : "כמה מהחיבורים נכונים"
        }
        hint="דיוק — מהמחוברים, כמה צדקו · כיסוי — מהאירועים, כמה נמצאו"
      >
        {e && live && liveRecall && tightest && tightRecall ? (
          <div className="flex flex-col gap-4">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              הטבלה בלשונית הקודמת בוחרת סף לפי כמה אירועים נוצרים. זה לא אומר
              שהם נכונים. ‏{e.golden_set.pairs} זוגות כתבות נדגמו מהקורפוס{" "}
              <b>בלי קשר למה שהמאחזר החזיר</b>, בשש רצועות קרבה, ותויגו אחד־אחד:
              אותו אירוע, או לא.
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              <Big value={pct(live.precision ?? 0)} label="דיוק בסף החי" tone="bad" />
              <Big
                value={pct(liveRecall.recall)}
                label={`כיסוי מעל ${e.recall.floor}`}
                tone="good"
              />
            </div>
            <div className="flex flex-col gap-2.5">
              {e.precision_sweep.map((row) => (
                <BarRow
                  key={row.threshold}
                  label={`סף ${row.threshold.toFixed(2)}`}
                  n={Math.round((row.precision ?? 0) * 100)}
                  max={100}
                  unit="%"
                  tone={row.threshold === e.live_threshold ? "accent" : "bad"}
                  note={
                    row.threshold === e.live_threshold
                      ? `${row.true_positives}/${row.labelled_accepted} — הסף החי`
                      : `${row.true_positives}/${row.labelled_accepted}`
                  }
                />
              ))}
            </div>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-3)]">
              כל שורה: מתוך הזוגות שעוברים את הסף, כמה אחוזים באמת אותו אירוע.
              ‏0% = כולם שגויים, ‏100% = כולם נכונים. ‏
              {pct(live.precision ?? 0)} בסף החי, בטווח{" "}
              <span dir="ltr">
                {pct(live.ci_low)}–{pct(live.ci_high)}
              </span>{" "}
              ב־95% ביטחון.
            </p>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              הסף נשאר על {e.live_threshold.toFixed(2)}. הידוק ל־
              {tightest.threshold.toFixed(2)} מעלה את הדיוק ל־
              {pct(tightest.precision ?? 0)} ומפיל את הכיסוי מ־
              {pct(liveRecall.recall)} ל־{pct(tightRecall.recall)}: הוא מוריד
              יותר מחצי מהשגיאות, ומוותר על{" "}
              {(10 * (1 - tightRecall.recall / liveRecall.recall)).toFixed(0)} מכל
              עשרה אירועים שהיו נמצאים. אירוע שלא נמצא לא מושווה בין ערוצים,
              וזה כל מה שהמסך הזה קיים בשבילו.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="השיטה המדויקת יותר היא זו שהוחלפה">
        {e && g && emb && kw ? (
          <div className="flex flex-col gap-3.5">
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              אותן {g.pairs} שאלות, שתי שיטות. חיפוש מילולי לא טועה כאן אף פעם —
              והוא לא מוצא את רוב האירועים.
            </p>
            <div className="flex flex-col gap-2.5">
              <BarRow
                label="מילים · דיוק"
                n={Math.round((kw.precision ?? 0) * 100)}
                max={100}
                unit="%"
                tone="good"
                note={`${kw.true_positives}/${kw.labelled_accepted}`}
              />
              <BarRow
                label="מילים · כיסוי"
                n={Math.round((kw.recall_on_sample ?? 0) * 100)}
                max={100}
                unit="%"
                tone="bad"
                note={`${kw.true_positives}/${kw.positives}`}
              />
              <BarRow
                label="משמעות · דיוק"
                n={Math.round((emb.precision ?? 0) * 100)}
                max={100}
                unit="%"
                tone="bad"
                note={`${emb.true_positives}/${emb.labelled_accepted}`}
              />
              <BarRow
                label="משמעות · כיסוי"
                n={Math.round((emb.recall_on_sample ?? 0) * 100)}
                max={100}
                unit="%"
                tone="good"
                note={`${emb.true_positives}/${emb.positives}`}
              />
            </div>
            <p className="text-[18px] leading-relaxed text-[var(--dk-ink-2)]">
              הבחירה היא בין מסך שמראה מעט השוואות נכונות למסך שמראה הרבה
              השוואות שחלקן שגויות. נבחרה השנייה, מפני ש־
              {kw.zero_overlap_positives ?? 0} מהאירועים כאן לא חולקים אף מילה
              ולשיטה הראשונה אין דרך להגיע אליהם בכלל.
            </p>

            <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-3.5 py-2.5">
              <div className="flex items-center gap-2.5">
                <Chip tone={g.human_reviewed ? "good" : "warn"}>
                  {g.agreement
                    ? `${g.agreement.reviewed} מתוך ${g.pairs} נסקרו על ידי אדם`
                    : "לא נסקר"}
                </Chip>
                {g.agreement && (
                  <span className="text-[15px] text-[var(--dk-ink-2)]">
                    הסכמה עם המודל {pct(g.agreement.rate)} (
                    {g.agreement.agreed}/{g.agreement.reviewed})
                  </span>
                )}
              </div>
              {g.agreement && (
                <p className="mt-1.5 text-[15px] leading-snug text-[var(--dk-ink-3)]">
                  שאר התיוגים נעשו על ידי מודל שפה. כל{" "}
                  {g.agreement.flipped_to_not_same} ההכרעות שהסוקר הפך נטו
                  לאותו כיוון — ל&rdquo;לא אותו אירוע&ldquo; — כך שהמספרים
                  משמאל הם ככל הנראה הגבול העליון, לא הערכת חסר.
                </p>
              )}
            </div>

            <Caveat>
              הכיסוי נמדד רק מעל קרבה {e.recall.floor}. מתחת לזה נמצאו{" "}
              {e.recall.below_region.same_found} אירועים ב־
              {e.recall.below_region.labelled} תיוגים על פני{" "}
              {num(e.recall.below_region.population)} זוגות — חסם של{" "}
              {pct(e.recall.below_region.rate_upper_95)}, לא מדידה.
            </Caveat>
            <Caveat>
              נמדד זוג מול זוג. האשכול עצמו בונה קבוצות בסבב אחד חמדני, ולכן
              דיוק על זוגות אינו דיוק על אירועים.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
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
