"use client";

import { useState } from "react";
import type { EconomyStage, Facts } from "./facts";
import {
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
  { id: "where", label_he: "איפה בכלל נדרש מודל" },
  { id: "sent", label_he: "מה נשלח בפועל" },
  { id: "rate", label_he: "כמה עולה תו בעברית" },
  { id: "bill", label_he: "החשבון" },
  { id: "cache", label_he: "המטמון" },
  { id: "limits", label_he: "מה החשבון לא כולל" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the token economy — what the model layer cost, and where no model
 * was used at all.
 *
 * The interesting number here is not the total; a few cents impresses nobody
 * and proves nothing. What the module argues is the shape of the bill: eight
 * of ten stages never call a model, more than a third of the prompt spend is
 * instruction text re-sent on every call, a fifth of the tokens are half the
 * money, and the strawman this architecture avoids is two orders of magnitude
 * away — not because the model is expensive, but because calling it per item
 * pays the fixed overhead 39,670 times.
 */
export function EconomyModule({ facts }: Props) {
  const [tab, setTab] = useState("where");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "where" && <Where facts={facts} />}
      {tab === "sent" && <Sent facts={facts} />}
      {tab === "rate" && <Rate facts={facts} />}
      {tab === "bill" && <Bill facts={facts} />}
      {tab === "cache" && <CacheTab facts={facts} />}
      {tab === "limits" && <Limits facts={facts} />}
    </div>
  );
}

/* ── formatting ─────────────────────────────────────────────────── */

function num(x: number): string {
  return x.toLocaleString("en-US");
}

function pct(x: number, digits = 0): string {
  return `${(x * 100).toFixed(digits)}%`;
}

/** Dollars, with enough digits that a per-call price is not rounded to zero. */
function usd(x: number): string {
  if (x === 0) return "$0";
  if (x >= 1) return `$${x.toFixed(2)}`;
  const digits = x >= 0.001 ? 4 : 6;
  return `$${x.toFixed(digits).replace(/0+$/, "").replace(/\.$/, "")}`;
}

function Big({
  value,
  label,
  tone = "accent",
}: {
  value: string;
  label: string;
  tone?: "accent" | "bad" | "good" | "warn" | "muted";
}) {
  const colors = {
    accent: "text-[var(--dk-accent)]",
    bad: "text-[var(--dk-bad)]",
    good: "text-[var(--dk-good)]",
    warn: "text-[var(--dk-warn)]",
    muted: "text-[var(--dk-ink-2)]",
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

/**
 * A two-tone proportion bar.
 *
 * In RTL the first flex child lands on the RIGHT, so neither segment is
 * labelled by side — each carries its own caption inside it.
 */
function SplitBar({
  parts,
}: {
  parts: { label: string; value: number; tone: "accent" | "bad" | "muted" }[];
}) {
  const total = parts.reduce((s, p) => s + p.value, 0) || 1;
  const colors = {
    accent: "bg-[var(--dk-accent)]/85",
    bad: "bg-[var(--dk-bad)]/80",
    muted: "bg-[var(--dk-ink-3)]/60",
  };
  return (
    <div className="flex h-11 overflow-hidden rounded-lg border border-[var(--dk-border)]">
      {parts.map((p) => (
        <div
          key={p.label}
          className={`flex items-center justify-center ${colors[p.tone]}`}
          style={{ width: `${(p.value / total) * 100}%` }}
        >
          <span className="truncate px-1.5 text-[13px] font-semibold text-[var(--dk-bg)]">
            {p.label}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ── 1. where a model is needed at all ──────────────────────────── */

const KIND_LABEL: Record<EconomyStage["kind"], string> = {
  free: "קוד דטרמיניסטי",
  local: "מודל מקומי",
  paid: "קריאת API בתשלום",
};

function StageRow({ stage, model }: { stage: EconomyStage; model: string }) {
  const tone =
    stage.kind === "paid" ? "bad" : stage.kind === "local" ? "warn" : "good";
  return (
    <li className="flex items-center gap-3 border-b border-[var(--dk-border)]/45 py-1.5 last:border-0">
      <span className="w-[104px] shrink-0 text-[15.5px] font-bold">
        {stage.label_he}
      </span>
      <span className="flex w-[124px] shrink-0 items-baseline gap-1.5">
        <span dir="ltr" className="font-mono text-[14px] text-[var(--dk-ink-2)]">
          {num(stage.n)}
        </span>
        <span className="text-[12px] text-[var(--dk-ink-3)]">{stage.unit_he}</span>
      </span>
      <span className="flex-1 text-[13.5px] leading-snug text-[var(--dk-ink-2)]">
        {stage.detail_he}
      </span>
      <span className="w-[86px] shrink-0 text-end">
        <Chip tone={tone}>{stage.kind === "paid" ? usd(stage.usd) : "0 טוקנים"}</Chip>
      </span>
      <span className="w-[100px] shrink-0 text-[12.5px] text-[var(--dk-ink-3)]">
        {stage.kind === "paid" ? model : KIND_LABEL[stage.kind]}
      </span>
    </li>
  );
}

function Where({ facts }: Props) {
  const e = facts?.economy;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[30%_1fr] gap-3">
      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="השאלה שקובעת">
          <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
            לפני &quot;כמה זה עלה&quot; יש שאלה זולה יותר: לאיזה שלב בכלל אין
            תשובה דטרמיניסטית. ספירת מילים מהמילון, חיתוך חלונות, שקלול תגובות,
            דמיון קוסינוס, bootstrap — לכולם יש תשובה מדויקת בקוד, ולכן אין להם
            סיבה לעבור דרך מודל.
          </p>
          <p className="mt-2 text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
            שתי שאלות נשארות: <b>מי מוצג כמבצע ולמי מיוחסת אחריות</b>, ו־
            <b>מה ייחודי בגרסה הזאת ביחס לאחרות</b>. רק הן משלמות.
          </p>
          {e && (
            <div className="mt-3 grid grid-cols-2 gap-2">
              <Big
                value={`${e.stages.filter((s) => s.kind === "paid").length}/${e.stages.length}`}
                label="שלבים שמשלמים טוקנים"
                tone="bad"
              />
              <Big value={usd(e.bill.usd)} label="כל שכבת המודל, פעם אחת" tone="good" />
            </div>
          )}
        </Panel>
        <Panel title="מודל שלא עולה כסף">
          {e ? (
            <>
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                שלב הווקטורים הוא רשת נוירונים לכל דבר — אבל היא רצה על המחשב
                הזה, בלי API ובלי מחיר לקריאה. {num(e.stages.find((s) => s.kind === "local")?.n ?? 0)}{" "}
                וקטורים נבנו, והחשבון עליהם הוא חשמל וזמן, לא טוקנים.
              </p>
              <div className="mt-2">
                <CodeRef path={e.constants.embed_model} />
              </div>
            </>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>

      <Panel
        title="עשרת השלבים, ומה כל אחד עולה"
        hint="הספירות נלקחות מהאריחים הקודמים — לא נספרות כאן מחדש"
      >
        {e ? (
          <ol className="flex flex-col">
            {e.stages.map((s) => (
              <StageRow key={s.key} stage={s} model={e.constants.model} />
            ))}
          </ol>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

/* ── 2. what was actually sent ──────────────────────────────────── */

function Sent({ facts }: Props) {
  const e = facts?.economy;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[42%_1fr] gap-3">
      <Panel title="הרכב הפרומפט" hint="תווים, כפי ששוחזרו מהמטמון">
        {e ? (
          <div className="flex flex-col gap-3">
            <div>
              <div className="mb-1 flex items-baseline justify-between text-[15px]">
                <span className="font-bold">חילוץ מסגור</span>
                <span className="text-[13.5px] text-[var(--dk-ink-3)]">
                  {e.prompt.framing.calls} קריאות · חציון{" "}
                  {num(Math.round(e.prompt.framing.user_median))} תווי תוכן
                </span>
              </div>
              <SplitBar
                parts={[
                  {
                    label: `הנחיה קבועה ${e.prompt.framing.system_chars}`,
                    value: e.prompt.framing.system_chars,
                    tone: "bad",
                  },
                  {
                    label: `כותרת ופתיח ${Math.round(e.prompt.framing.user_median)}`,
                    value: e.prompt.framing.user_median,
                    tone: "accent",
                  },
                ]}
              />
            </div>
            <div>
              <div className="mb-1 flex items-baseline justify-between text-[15px]">
                <span className="font-bold">ניתוח קונטרסטיבי</span>
                <span className="text-[13.5px] text-[var(--dk-ink-3)]">
                  {e.prompt.contrast.calls} קריאות ·{" "}
                  {e.prompt.contrast.versions
                    .map((v) => `${v.events} אירועים ב־${v.versions} גרסאות`)
                    .join(" · ")}
                </span>
              </div>
              <SplitBar
                parts={[
                  {
                    label: `הנחיה קבועה ${e.prompt.contrast.system_chars}`,
                    value: e.prompt.contrast.system_chars,
                    tone: "bad",
                  },
                  {
                    label: `הגרסאות ${Math.round(e.prompt.contrast.user_median)}`,
                    value: e.prompt.contrast.user_median,
                    tone: "accent",
                  },
                ]}
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              ההנחיה זהה בכל קריאה ובכל זאת נשלחת מחדש בכל אחת מהן:{" "}
              {num(e.prompt.system_chars_total)} תווים, שהם{" "}
              <b>{pct(e.prompt.system_share_of_prompt)}</b> מתווי הקלט —
              וממילא גם מהטוקנים ששולמו עליהם. בקריאת מסגור זו כמעט מחצית
              מההודעה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="גבול החיתוך — הפתיח ולא הכתבה">
        {e ? (
          <div className="flex flex-col gap-2.5">
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              המודל מקבל כותרת ואת {e.constants.lead_chars} התווים הראשונים
              בלבד. זו לא קמצנות: המסגור נקבע בפתיח, והמאמת בודק את הביטויים
              מול אותו חלון בדיוק — מה שלא נשלח גם לא יכול להיות מאומת.
            </p>
            <div className="grid grid-cols-3 gap-2">
              <Big
                value={num(Math.round(e.truncation.median_chars))}
                label="חציון אורך כתבה בגרסאות שנשלחו"
                tone="muted"
              />
              <Big
                value={pct(e.truncation.median_share_sent)}
                label="מהכתבה החציונית באמת נשלח"
                tone="accent"
              />
              <Big
                value={`${e.truncation.over_cap}/${e.truncation.versions}`}
                label="גרסאות שנחתכו בפועל"
                tone="warn"
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              {num(e.truncation.dropped_chars)} תווים לא נשלחו. לפי שער
              ההמרה שנמדד כאן זה כ־{num(e.truncation.dropped_tokens)} טוקנים —
              החיתוך מנע יותר ממחצית מחשבון הקלט: {num(e.bill.prompt_tokens)}{" "}
              במקום {num(e.truncation.would_be_prompt_tokens)}.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone="good">נחסך {usd(e.truncation.dropped_usd)}</Chip>
              <Chip tone="neutral">
                <span dir="ltr">EXTRACT_LEAD_CHARS = {e.constants.lead_chars}</span>
              </Chip>
              <Chip tone="neutral">
                <span dir="ltr">
                  contrast lead = {e.constants.contrast_lead_chars}
                </span>
              </Chip>
            </div>
            <Caveat>
              הקריאה הקונטרסטיבית אורזת כמה גרסאות בהודעה אחת, ולכן חותכת כל
              אחת ב־{e.constants.contrast_lead_chars} תווים ולא ב־
              {e.constants.lead_chars}. המאמת עדיין בודק מול{" "}
              {e.constants.lead_chars} — חלון רחב יותר, כך שציטוט לעולם לא
              נפסל על טקסט שהמודל כן קיבל.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

/* ── 3. the exchange rate ───────────────────────────────────────── */

function Rate({ facts }: Props) {
  const e = facts?.economy;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[38%_1fr] gap-3">
      <Panel title="שער ההמרה, נמדד ולא נזכר">
        {e ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              קובץ השימוש מחזיק את מספר הטוקנים האמיתי שחויב, וכל הפרומפטים
              שוחזרו מהמטמון ומאותה תמונת מצב. חלוקה של האחד בשני נותנת את
              השער של הקורפוס הזה — לא כלל אצבע.
            </p>
            <div className="grid grid-cols-2 gap-2">
              <Big value={e.rate.chars_per_token.toFixed(2)} label="תווים לטוקן — צד הקלט" />
              <Big
                value={e.rate.output_chars_per_token.toFixed(2)}
                label="תווים לטוקן — צד הפלט"
                tone="muted"
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              שתי מדידות בלתי תלויות, פער של {pct(e.rate.gap, 1)}. הפער ידוע:
              במטמון נשמרת התשובה <b>לאחר פענוח</b>, בלי גדרות קוד ובלי
              רווחים מיותרים, ולכן היא מעט קצרה מהתשובה שחויבה. לכן שני
              המספרים מוצגים בנפרד ולא ממוצעים לאחד.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="מה זה אומר בפועל">
          {e ? (
            <div className="flex flex-col gap-2">
              {e.rate.examples.map((x) => (
                <div
                  key={x.label_he}
                  className="flex items-center gap-3 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-3 py-2"
                >
                  <span className="flex-1 text-[15.5px]">{x.label_he}</span>
                  <span
                    dir="ltr"
                    className="w-[110px] text-left font-mono text-[14.5px] text-[var(--dk-ink-2)]"
                  >
                    {num(x.chars)} chars
                  </span>
                  <span className="text-[var(--dk-ink-3)]">←</span>
                  <span
                    dir="ltr"
                    className="w-[96px] text-left font-mono text-[16px] font-bold text-[var(--dk-accent)]"
                  >
                    ~{num(x.tokens)} tok
                  </span>
                </div>
              ))}
              <div className="mt-1 grid grid-cols-2 gap-2">
                <div className="rounded-xl border border-[var(--dk-border)] p-2.5">
                  <div className="text-[14px] text-[var(--dk-ink-3)]">
                    סך תווי הקלט ששוחזרו
                  </div>
                  <div dir="ltr" className="font-mono text-[19px] font-bold">
                    {num(e.rate.prompt_chars)}
                  </div>
                </div>
                <div className="rounded-xl border border-[var(--dk-border)] p-2.5">
                  <div className="text-[14px] text-[var(--dk-ink-3)]">
                    טוקני הקלט שחויבו בפועל
                  </div>
                  <div dir="ltr" className="font-mono text-[19px] font-bold">
                    {num(e.rate.prompt_tokens)}
                  </div>
                </div>
              </div>
              <Caveat>
                השער נמדד על עברית של חדשות, כולל תקורת פורמט השיחה. הוא לא
                תקף לשפה אחרת, ולא למודל אחר — הוא תיאור של הקורפוס הזה מול
                המחירון של {e.constants.model}.
              </Caveat>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
        <Panel title="שלושת הברזים" hint="כל אחד מהם נמדד, לא נאמד">
          {e ? (
            <ol className="flex flex-col gap-2">
              <Lever
                n={1}
                title="ההנחיה הקבועה"
                tokens={`${num(e.prompt.system_tokens)} טוקנים שולמו`}
                body={`אותו טקסט, ${e.bill.calls} פעמים. זה ${pct(
                  e.prompt.system_share_of_prompt,
                )} מהקלט — והברז היחיד מהשלושה שנשאר פתוח.`}
                tone="bad"
              />
              <Lever
                n={2}
                title={`החיתוך ב־${e.constants.lead_chars} תווים`}
                tokens={`${num(e.truncation.dropped_tokens)} טוקנים נחסכו`}
                body={`יותר ממה ששולם בפועל: בלי החיתוך חשבון הקלט היה ${num(
                  e.truncation.would_be_prompt_tokens,
                )} במקום ${num(e.bill.prompt_tokens)}.`}
                tone="good"
              />
              <Lever
                n={3}
                title="תקרות הפלט"
                tokens={`${e.bill.completion_per_call} טוקנים לקריאה בממוצע`}
                body={`התקרות (${e.constants.framing_max_tokens} ו־${e.constants.contrast_max_tokens}) גבוהות מהממוצע בפועל, ולכן הן רשת ביטחון ולא בלם. ובכל זאת: הפלט הוא ${pct(
                  e.bill.completion_bill_share,
                )} מהחשבון.`}
                tone="warn"
              />
            </ol>
          ) : (
            <Missing />
          )}
        </Panel>
      </div>
    </div>
  );
}


/** One measured cost lever: what it is, what it moved, and in which direction. */
function Lever({
  n,
  title,
  tokens,
  body,
  tone,
}: {
  n: number;
  title: string;
  tokens: string;
  body: string;
  tone: "good" | "bad" | "warn";
}) {
  return (
    <li className="flex items-start gap-3 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/40 px-3 py-2">
      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--dk-border)] font-mono text-[13px] text-[var(--dk-ink-3)]">
        {n}
      </span>
      <div className="flex-1">
        <div className="flex items-baseline gap-2">
          <span className="text-[15.5px] font-bold">{title}</span>
          <Chip tone={tone}>{tokens}</Chip>
        </div>
        <p className="mt-0.5 text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
          {body}
        </p>
      </div>
    </li>
  );
}

/* ── 4. the bill ────────────────────────────────────────────────── */

function Bill({ facts }: Props) {
  const e = facts?.economy;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[44%_1fr] gap-3">
      <Panel title="החשבון כולו">
        {e ? (
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-3 gap-2">
              <Big value={num(e.bill.calls)} label="קריאות מודל, אי פעם" tone="muted" />
              <Big value={num(e.bill.total_tokens)} label="טוקנים בסך הכל" tone="muted" />
              <Big value={usd(e.bill.usd)} label="עלות כוללת" tone="good" />
            </div>
            <div>
              <div className="mb-1 text-[15px] font-bold">
                היכן הכסף — לא היכן הטוקנים
              </div>
              <SplitBar
                parts={[
                  {
                    label: `קלט ${pct(1 - e.bill.completion_token_share)}`,
                    value: e.bill.prompt_tokens,
                    tone: "muted",
                  },
                  {
                    label: `פלט ${pct(e.bill.completion_token_share)}`,
                    value: e.bill.completion_tokens,
                    tone: "accent",
                  },
                ]}
              />
              <div className="mt-1.5">
                <SplitBar
                  parts={[
                    {
                      label: `קלט ${usd(e.bill.prompt_usd)}`,
                      value: e.bill.prompt_usd,
                      tone: "muted",
                    },
                    {
                      label: `פלט ${usd(e.bill.completion_usd)}`,
                      value: e.bill.completion_usd,
                      tone: "accent",
                    },
                  ]}
                />
              </div>
              <p className="mt-2 text-[15px] leading-snug text-[var(--dk-ink-2)]">
                הפלט הוא {pct(e.bill.completion_token_share)} מהטוקנים ו־
                <b>{pct(e.bill.completion_bill_share)}</b> מהחשבון, כי טוקן
                פלט עולה פי {(e.bill.price_completion_per_m / e.bill.price_prompt_per_m).toFixed(0)}.
                לכן תקרת הפלט (
                <span dir="ltr">
                  {e.constants.framing_max_tokens}/{e.constants.contrast_max_tokens}
                </span>
                ) היא הבלם האמיתי, לא אורך הפתיח.
              </p>
            </div>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="לפי סוג קריאה" hint="פיצול נגזר — ראו את ההערה">
        {e ? (
          <div className="flex flex-col gap-2">
            {e.split.map((s) => (
              <div
                key={s.key}
                className="flex items-center gap-3 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-3 py-2"
              >
                <span className="w-[128px] shrink-0 text-[15.5px] font-bold">
                  {s.label_he}
                </span>
                <span
                  dir="ltr"
                  className="w-[76px] shrink-0 text-left font-mono text-[14px] text-[var(--dk-ink-2)]"
                >
                  {s.calls} calls
                </span>
                <span
                  dir="ltr"
                  className="flex-1 text-left font-mono text-[13.5px] text-[var(--dk-ink-3)]"
                >
                  {num(s.prompt_tokens)} in · {num(s.completion_tokens)} out
                </span>
                <span dir="ltr" className="w-[84px] text-left font-mono text-[15px]">
                  {usd(s.usd)}
                </span>
                <span
                  dir="ltr"
                  className="w-[96px] text-left font-mono text-[14px] text-[var(--dk-accent)]"
                >
                  {usd(s.per_call_usd)}
                </span>
              </div>
            ))}
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              {e.split[0]?.calls} קריאות מסגור ו־{e.split[1]?.calls} קריאות
              קונטרסט עולות כמעט אותו דבר: הקריאה הקונטרסטיבית מקבלת כמה
              גרסאות ומחזירה משפט וציטוט לכל אחת, ולכן היא יקרה פי{" "}
              {(
                (e.split[1]?.per_call_usd ?? 0) / (e.split[0]?.per_call_usd || 1)
              ).toFixed(1)}{" "}
              מקריאת מסגור.
            </p>
            <div className="grid grid-cols-4 gap-2">
              {e.per_unit.map((u) => (
                <div
                  key={u.label_he}
                  className="rounded-xl border border-[var(--dk-border)] p-2 text-center"
                >
                  <div dir="ltr" className="font-mono text-[15px] font-bold">
                    {usd(u.usd)}
                  </div>
                  <div className="text-[12.5px] leading-tight text-[var(--dk-ink-2)]">
                    {u.label_he}
                  </div>
                  <div dir="ltr" className="text-[11.5px] text-[var(--dk-ink-3)]">
                    n={num(u.n)}
                  </div>
                </div>
              ))}
            </div>
            <Caveat>
              קובץ השימוש מחזיק סכום אחד, לא פיצול. טוקני הקלט חולקו לפי
              התווים שנמדדו בכל סוג קריאה, וטוקני הפלט לפי אורך התשובות
              השמורות — כלומר בהנחה שאותו שער חל על שני הסוגים. הסכום מדוד,
              החלוקה נגזרת.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

/* ── 5. the cache ───────────────────────────────────────────────── */

function CacheTab({ facts }: Props) {
  const e = facts?.economy;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[40%_1fr] gap-3">
      <Panel title="מה המטמון באמת קונה">
        {e ? (
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-2">
              <Big
                value={`${e.cache.entries}/${e.bill.calls}`}
                label="פריטים במטמון מול קריאות ששולמו"
                tone="good"
              />
              <Big value={String(e.cache.showtime_calls)} label="קריאות מודל בזמן התצוגה" tone="good" />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              לולאה נרטיבית אחת מציגה {e.cache.calls_per_loop} תשובות מודל.
              יום תצוגה של {e.cache.show_hours} שעות, לולאה כל{" "}
              {e.cache.loop_minutes} דקות, הוא {e.cache.loops} לולאות — ובלי
              מטמון {usd(e.cache.day_usd)}.
            </p>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              כלומר המטמון כמעט לא חוסך כסף. מה שהוא קונה זה שני דברים שאי
              אפשר לקנות בכסף על הרצפה של תערוכה: <b>ריצה בלי רשת</b>, ו־
              <b>אותה תוצאה בדיוק בכל לולאה</b>. מודל בטמפרטורה{" "}
              {e.constants.temperature} עדיין יכול להשתנות בין גרסאות; קובץ לא.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="איפה יושב המטמון">
        {e ? (
          <div className="flex flex-col gap-2.5">
            <div className="flex items-stretch gap-2">
              <Node
                title="framing_cache.json"
                mono
                wide
                sub={`${e.cache.framing} תשובות · מפתח: article_id`}
              />
              <Node
                title="contrast_cache.json"
                mono
                wide
                sub={`${e.cache.contrast} תשובות · מפתח: event_id`}
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              המפתח הוא הזהות של הפריט, לא גיבוב של הפרומפט. זו החלטה עם
              מחיר: שינוי בניסוח ההנחיה <b>לא</b> מבטל את המטמון, ולכן הכנה
              חוזרת אחרי עריכת פרומפט מחייבת מחיקה ידנית. בתמורה, המטמון שורד
              שינויי קוד ביום התצוגה.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone={e.bill.covered ? "good" : "warn"}>
                {e.bill.covered
                  ? "כל קריאה ששולמה נשמרה"
                  : "יש קריאות ששולמו בלי פריט במטמון"}
              </Chip>
              <CodeRef path="demo/data/llm_usage.json" />
            </div>
            <MetricCard
              name="עלות ההכנה"
              field="llm_usage.json"
              formula="usd = (in × 0.15 + out × 0.60) / 1e6"
              range="מצטבר על פני ריצות הכנה"
              reads={[
                { value: "showtime", means: "אפס — התצוגה קוראת קובץ, לא API" },
                {
                  value: "prepare",
                  means: "מה שבניית המטמון עלתה; זה המספר הכנה היחיד שיש",
                },
              ]}
              measured={
                <span dir="ltr">
                  {num(e.bill.calls)} calls · {num(e.bill.total_tokens)} tok ·{" "}
                  {usd(e.bill.usd)}
                </span>
              }
            />
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

/* ── 6. the strawman, and the exclusions ────────────────────────── */

function Limits({ facts }: Props) {
  const e = facts?.economy;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <Panel title="אילו הכל היה עובר במודל" hint="אומדן, על בסיס השער שנמדד">
        {e ? (
          <div className="flex flex-col gap-2.5">
            <div className="grid grid-cols-2 gap-2">
              <Big value={usd(e.bill.usd)} label="הארכיטקטורה שנבנתה" tone="good" />
              <Big value={usd(e.strawman.usd)} label={`אותו קורפוס, הכל מודל — פי ${e.strawman.ratio}`} tone="bad" />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              האומדן: קריאה אחת לכל כתבה ולכל תגובה —{" "}
              {num(e.strawman.calls)} קריאות. והנה הנקודה: המודל לא יקר. מה
              שיקר זה לשלם את ההנחיה הקבועה {num(e.strawman.calls)} פעמים —{" "}
              <b>{pct(e.strawman.system_share)}</b> מתווי הקלט באומדן הזה הם
              אותה הנחיה שחוזרת.
            </p>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              בקצב של תמונת המצב ({e.strawman.days} ימים,{" "}
              {num(e.strawman.articles)} כתבות): כ־{usd(e.strawman.month_usd)}{" "}
              בחודש מול {usd(e.strawman.agents_month_usd)} לשכבת הסוכנים.
            </p>
            <Caveat>
              שני אומדנים לאותו קש: הסצנה הנרטיבית משתמשת בהנחה עגולה של{" "}
              {e.strawman.scene.prompt_per_article}+
              {e.strawman.scene.completion_per_article} טוקנים לכתבה על{" "}
              {num(e.strawman.scene.articles)} כתבות ומגיעה ל־
              {usd(e.strawman.scene.usd)}. הלוח הזה סופר גם את{" "}
              {num(e.strawman.comments)} התגובות ומשתמש בשער שנמדד, ולכן
              גדול ממנה בהרבה. שניהם אומדנים, ואף אחד מהם לא רץ.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="מה החשבון הזה לא כולל">
        {e ? (
          <div className="flex flex-col gap-2">
            {e.excluded.map((x) => (
              <div
                key={x.key}
                className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/40 px-3 py-2"
              >
                <div className="flex items-baseline gap-2">
                  <span className="text-[15.5px] font-bold">{x.label_he}</span>
                  {x.usd !== null && (
                    <Chip tone="warn">
                      <span dir="ltr">~{usd(x.usd)}</span>
                    </Chip>
                  )}
                  {x.n !== null && x.unit_he && (
                    <span className="text-[13px] text-[var(--dk-ink-3)]">
                      {num(x.n)} {x.unit_he}
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
                  {x.detail_he}
                </p>
              </div>
            ))}
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              השורה הראשונה היא ההודאה החשובה: הצרכן הגדול ביותר של טוקנים
              במערכת אינו שכבת הסוכנים אלא מסווג הקטגוריות הצנוע — לא כי הוא
              מתוחכם, אלא כי הוא רץ על <b>כל</b> כתבה במקום רק על אירועים
              חוצי־ערוצים.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
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
