"use client";

import { useState } from "react";
import type { EconomyStage, Facts } from "./facts";
import {
  Caveat,
  Chip,
  CodeRef,
  Panel,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "tiers", label_he: "שני שלבים משלמים" },
  { id: "sent", label_he: "מה נשלח למודל" },
  { id: "bill", label_he: "החשבון" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: the token economy.
 *
 * The interesting number is not the total; a few cents impresses nobody. What
 * the module argues is the shape of the bill — which tier each stage belongs
 * to, that a third of the prompt spend is instruction text re-sent on every
 * call, that a fifth of the tokens are half the money, and that the strawman
 * this architecture avoids is two orders of magnitude away because calling a
 * model per item pays the fixed overhead 39,670 times.
 */
export function EconomyModule({ facts }: Props) {
  const [tab, setTab] = useState("tiers");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "tiers" && <Tiers facts={facts} />}
      {tab === "sent" && <Sent facts={facts} />}
      {tab === "bill" && <Bill facts={facts} />}
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

function Missing() {
  return (
    <p className="text-[15px] text-[var(--dk-ink-3)]">
      אין קובץ מדידות — הדיאגרמות מוצגות בלי המספרים.
    </p>
  );
}

/* ── 1. the tiers ───────────────────────────────────────────────── */

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

function Tiers({ facts }: Props) {
  const e = facts?.economy;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[32%_1fr] gap-3">
      <div className="flex min-h-0 flex-col gap-3">
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
      <Panel title="ההנחיה הקבועה נשלחת שוב בכל קריאה">
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
            <p className="text-[15px] leading-snug text-[var(--dk-ink-2)]">
              התכלת היא התוכן, ורק באחת מהשתיים הוא מאוחזר. המסגור מקבל את
              הכתבה שלו. ההשוואה מקבלת{" "}
              {e.constants.contrast_versions} גרסאות שהאחזור בחר מתוך{" "}
              {num(facts?.retrieval.corpus.indexed ?? 0)} — <b>RAG</b>, כי אין
              דרך לענות מכתבה אחת מה ייחודי בגרסה הזאת.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel
        title="החיתוך חסך יותר טוקנים מכל מה ששולם"
        hint={e ? `שער ההמרה נמדד: ${e.rate.chars_per_token.toFixed(2)} תווים לטוקן` : undefined}
      >
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
              השער נמדד: {num(e.rate.prompt_chars)} תווים ששוחזרו חלקי{" "}
              {num(e.rate.prompt_tokens)} טוקנים שחויבו. בצד הפלט הוא{" "}
              {e.rate.output_chars_per_token.toFixed(2)} — פער של{" "}
              {pct(e.rate.gap, 1)}, כי המטמון שומר את התשובה אחרי פענוח.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

/* ── 3. the bill ────────────────────────────────────────────────── */

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
                מטוקן קלט, ולכן הבלם הוא תקרת הפלט (
                <span dir="ltr">
                  {e.constants.framing_max_tokens}/{e.constants.contrast_max_tokens}
                </span>
                ) ולא אורך הפתיח.
              </p>
            </div>
            <Caveat>
              הסכום שולם פעם אחת, בזמן ההכנה. בזמן התצוגה יש{" "}
              {e.cache.showtime_calls} קריאות מודל: המסך מנגן{" "}
              {e.cache.entries} תשובות שמורות. מה שזה קונה הוא ריצה בלי רשת
              ואותה תוצאה בכל לולאה, לא כסף — בהנחת יום של{" "}
              {e.cache.show_hours} שעות ולולאה כל {e.cache.loop_minutes} דקות
              ({e.cache.loops} לולאות) המטמון חוסך {usd(e.cache.day_usd)}.
            </Caveat>
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
            <Caveat>
              החשבון הזה הוא שכבת הסוכנים בלבד. מחוצה לו:{" "}
              {e.excluded
                .filter((x) => x.usd !== null)
                .map((x) => `${x.label_he} ~${usd(x.usd as number)}`)
                .join(" · ")}
              . מסווג הקטגוריות לבדו גדול משכבת הסוכנים כולה, כי הוא רץ על{" "}
              <b>כל</b> כתבה ולא רק על אירועים חוצי־ערוצים.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}
