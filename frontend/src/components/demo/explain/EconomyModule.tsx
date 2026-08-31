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
  { id: "where", label_he: "שני שלבים משלמים" },
  { id: "sent", label_he: "מה נשלח למודל" },
  { id: "rate", label_he: "תווים לטוקן" },
  { id: "bill", label_he: "החשבון" },
  { id: "cache", label_he: "מה המטמון קונה" },
  { id: "limits", label_he: "מה לא נספר" },
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
  free: "תשובה אחת בקוד",
  local: "מודל שרץ כאן",
  paid: "קריאה בתשלום",
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
        <Panel title="‏8 מתוך 10 שלבים לא קוראים למודל">
          <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
            מודל שפה אינו דטרמיניסטי. איפה שיש תשובה מחושבת — עונה הקוד.
          </p>
          <p className="mt-2 text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
            נשארו שתי שאלות פרשניות: <b>מי המבצע בכותרת</b>, ו<b>מה ייחודי
            בגרסה הזאת</b>. רק הן משלמות.
          </p>
          {e && (
            <div className="mt-3 grid grid-cols-2 gap-2">
              <Big
                value={`${e.stages.filter((s) => s.kind === "paid").length}/${e.stages.length}`}
                label="שלבים שקוראים למודל"
                tone="bad"
              />
              <Big value={usd(e.bill.usd)} label="כל שכבת המודל, פעם אחת" tone="good" />
            </div>
          )}
        </Panel>
        <Panel title="מודל נוסף רץ כאן, בלי חשבון">
          {e ? (
            <>
              <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
                {num(e.stages.find((s) => s.kind === "local")?.n ?? 0)}{" "}
                וקטורים נבנו כאן, במחשב. רשת נוירונים בלי API, ולכן בלי חשבון.
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
        title="שתי שורות בלבד נושאות מחיר"
        hint="הספירות מגיעות מהמדידה, לא מהטבלה הזאת"
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
      <Panel title="ההנחיה הקבועה נשלחת שוב בכל קריאה" hint="תווים ששוחזרו מהקריאות ששולמו">
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
              {num(e.prompt.system_chars_total)} תווים —{" "}
              <b>{pct(e.prompt.system_share_of_prompt)}</b> מהקלט — הם אותה
              הנחיה, שנשלחת מחדש בכל קריאה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="החיתוך חסך יותר טוקנים מכל מה ששולם">
        {e ? (
          <div className="flex flex-col gap-2.5">
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              המודל רואה כותרת ו־{e.constants.lead_chars} תווים. המסגור נקבע
              בפתיח.
            </p>
            <div className="grid grid-cols-3 gap-2">
              <Big
                value={num(Math.round(e.truncation.median_chars))}
                label="אורך כתבה חציוני"
                tone="muted"
              />
              <Big
                value={pct(e.truncation.median_share_sent)}
                label="נשלח מהכתבה החציונית"
                tone="accent"
              />
              <Big
                value={`${e.truncation.over_cap}/${e.truncation.versions}`}
                label="גרסאות שנחתכו"
                tone="warn"
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              {num(e.truncation.dropped_chars)} תווים לא נשלחו מעולם — כ־
              {num(e.truncation.dropped_tokens)} טוקנים. חשבון הקלט יצא{" "}
              {num(e.bill.prompt_tokens)} במקום{" "}
              {num(e.truncation.would_be_prompt_tokens)}.
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
              קריאת ההשוואה אורזת כמה גרסאות בהודעה אחת, ולכן חותכת כל אחת
              ב־{e.constants.contrast_lead_chars}. המאמת בודק מול{" "}
              {e.constants.lead_chars} — חלון רחב יותר, ולכן ציטוט לא נפסל על
              טקסט שהמודל קיבל.
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
      <Panel title="השער נמדד, לא הונח">
        {e ? (
          <div className="flex flex-col gap-3">
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              תווים ששוחזרו, חלקי טוקנים שחויבו. השער של הקורפוס הזה, לא כלל
              אצבע.
            </p>
            <div className="grid grid-cols-2 gap-2">
              <Big value={e.rate.chars_per_token.toFixed(2)} label="תווים לטוקן בקלט" />
              <Big
                value={e.rate.output_chars_per_token.toFixed(2)}
                label="תווים לטוקן בפלט"
                tone="muted"
              />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              פער של {pct(e.rate.gap, 1)} בין קלט לפלט: המטמון שומר את התשובה{" "}
              <b>אחרי פענוח</b>, קצרה מעט מזו שחויבה. לכן שני המספרים נשארים
              בנפרד.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel title="שלוש דוגמאות בשער הזה">
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
                    תווי קלט ששוחזרו
                  </div>
                  <div dir="ltr" className="font-mono text-[19px] font-bold">
                    {num(e.rate.prompt_chars)}
                  </div>
                </div>
                <div className="rounded-xl border border-[var(--dk-border)] p-2.5">
                  <div className="text-[14px] text-[var(--dk-ink-3)]">
                    טוקני קלט שחויבו
                  </div>
                  <div dir="ltr" className="font-mono text-[19px] font-bold">
                    {num(e.rate.prompt_tokens)}
                  </div>
                </div>
              </div>
              <Caveat>
                נמדד על עברית עיתונאית מול {e.constants.model}, וכולל את תקורת
                פורמט השיחה. לא תקף לשפה אחרת ולא למודל אחר.
              </Caveat>
            </div>
          ) : (
            <Missing />
          )}
        </Panel>
        <Panel title="שלושה ברזים, אחד עדיין פתוח" hint="כל אחד מהם נמדד, לא נאמד">
          {e ? (
            <ol className="flex flex-col gap-2">
              <Lever
                n={1}
                title="ההנחיה הקבועה"
                tokens={`${num(e.prompt.system_tokens)} טוקנים שולמו`}
                body={`אותו טקסט, ${e.bill.calls} פעמים. ${pct(
                  e.prompt.system_share_of_prompt,
                )} מהקלט.`}
                tone="bad"
              />
              <Lever
                n={2}
                title={`החיתוך ב־${e.constants.lead_chars} תווים`}
                tokens={`${num(e.truncation.dropped_tokens)} טוקנים נחסכו`}
                body={`בלי החיתוך: ${num(
                  e.truncation.would_be_prompt_tokens,
                )} טוקנים במקום ${num(e.bill.prompt_tokens)}.`}
                tone="good"
              />
              <Lever
                n={3}
                title="תקרות הפלט"
                tokens={`${e.bill.completion_per_call} טוקנים לקריאה בממוצע`}
                body={`${e.constants.framing_max_tokens} ו־${e.constants.contrast_max_tokens} — רשת ביטחון, לא בלם. הפלט הוא ${pct(
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
      <Panel title="הפלט הוא הצד היקר של החשבון">
        {e ? (
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-3 gap-2">
              <Big value={num(e.bill.calls)} label="כל קריאות המודל" tone="muted" />
              <Big value={num(e.bill.total_tokens)} label="טוקנים, קלט ופלט" tone="muted" />
              <Big value={usd(e.bill.usd)} label="עלות כוללת" tone="good" />
            </div>
            <div>
              <div className="mb-1 text-[15px] font-bold">
                אותו חשבון: פעם בטוקנים, פעם בכסף
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
                <b>{pct(e.bill.completion_bill_share)}</b> מהחשבון. טוקן פלט
                עולה פי{" "}
                {(e.bill.price_completion_per_m / e.bill.price_prompt_per_m).toFixed(0)}{" "}
                מטוקן קלט.
              </p>
            </div>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="שני סוגי הקריאות עולים כמעט אותו סכום" hint="הסכום מדוד, החלוקה נגזרת">
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
              השוואה עולות כמעט אותו סכום. ההשוואה אורזת כמה גרסאות, ולכן יקרה
              פי{" "}
              {(
                (e.split[1]?.per_call_usd ?? 0) / (e.split[0]?.per_call_usd || 1)
              ).toFixed(1)}{" "}
              לקריאה.
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
              קובץ השימוש מחזיק סכום אחד. הקלט חולק לפי התווים שנמדדו בכל סוג
              קריאה, הפלט לפי אורך התשובות השמורות. הסכום מדוד, החלוקה נגזרת.
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
      <Panel
        title="המטמון כמעט לא חוסך כסף"
        hint={
          e
            ? `בהנחת יום של ${e.cache.show_hours} שעות ולולאה כל ${e.cache.loop_minutes} דקות`
            : undefined
        }
      >
        {e ? (
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-2">
              <Big
                value={`${e.cache.entries}/${e.bill.calls}`}
                label="תשובות שמורות מכל הקריאות"
                tone="good"
              />
              <Big value={String(e.cache.showtime_calls)} label="קריאות מודל בזמן התצוגה" tone="good" />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              {usd(e.cache.day_usd)} — כל מה שיום תצוגה היה עולה בלי מטמון.{" "}
              {e.cache.loops} לולאות, {e.cache.calls_per_loop} תשובות בכל אחת.
            </p>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              מה שהוא כן קונה: <b>ריצה בלי רשת</b>, ו<b>אותה תוצאה בכל לולאה</b>.
              מודל בטמפרטורה {e.constants.temperature} עדיין יכול להשתנות. קובץ
              לא משתנה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="המפתח הוא זהות הפריט, לא נוסח ההנחיה">
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
              המפתח הוא מזהה הכתבה או האירוע, לא נוסח ההנחיה. שינוי בהנחיה{" "}
              <b>לא</b> מבטל את המטמון — מוחקים אותו ידנית.
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
                { value: "showtime", means: "אפס. התצוגה קוראת קובץ, לא API" },
                {
                  value: "prepare",
                  means: "מה שבניית המטמון עלתה. זה כל החשבון",
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
      <Panel title="מה שיקר הוא ההנחיה, לא המודל" hint="אומדן לפי השער שנמדד">
        {e ? (
          <div className="flex flex-col gap-2.5">
            <div className="grid grid-cols-2 gap-2">
              <Big value={usd(e.bill.usd)} label="הארכיטקטורה שנבנתה" tone="good" />
              <Big value={usd(e.strawman.usd)} label={`אותו קורפוס דרך מודל · פי ${e.strawman.ratio}`} tone="bad" />
            </div>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              {num(e.strawman.calls)} קריאות באומדן, אחת לכל כתבה ולכל תגובה.{" "}
              <b>{pct(e.strawman.system_share)}</b> מהקלט בהן הוא אותה הנחיה.
              המודל לא יקר. יקר לשלם אותה הנחיה {num(e.strawman.calls)} פעמים.
            </p>
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              בקצב תמונת המצב ({e.strawman.days} ימים,{" "}
              {num(e.strawman.articles)} כתבות) זה כ־{usd(e.strawman.month_usd)}{" "}
              בחודש, מול {usd(e.strawman.agents_month_usd)} לשכבת הסוכנים.
            </p>
            <Caveat>
              שני אומדנים לאותו תרחיש. הסצנה סופרת כתבות בלבד ({usd(e.strawman.scene.usd)}{" "}
              על {num(e.strawman.scene.articles)} כתבות,{" "}
              {e.strawman.scene.prompt_per_article}+
              {e.strawman.scene.completion_per_article} טוקנים לכתבה). כאן
              נספרות גם {num(e.strawman.comments)} התגובות. אף אחד מהם לא רץ.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="ההוצאה הגדולה במערכת היא מסווג הקטגוריות">
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
              מסווג הקטגוריות צורך יותר טוקנים משכבת הסוכנים כולה — הוא רץ על{" "}
              <b>כל</b> כתבה.
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
