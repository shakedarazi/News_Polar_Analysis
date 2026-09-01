"use client";

import type { ReactNode } from "react";

/**
 * Shared building blocks for the explainer modules.
 *
 * These are static-diagram primitives on purpose. The live scenes animate
 * because they are showing something happening; an explainer is showing
 * something that is *true*, and motion there reads as decoration. The only
 * movement is the presenter's own navigation between panels.
 */

/* ── layout ─────────────────────────────────────────────────────── */

/**
 * The panels of one tab: sized to their own content, centred as a block.
 *
 * Stretching every card to the full wall height left a dead band inside each
 * one — a panel with 220px of content held 590px of nothing. A card that ends
 * where its content ends reads as composed instead of unfinished.
 *
 * `cols` must be a literal Tailwind class (`grid-cols-[46%_1fr]`), not a
 * template string, or the class never reaches the stylesheet.
 */
export function Stage({
  cols,
  children,
}: {
  cols: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-0 flex-1 items-center overflow-hidden">
      <div className={`grid max-h-full w-full ${cols} gap-3`}>{children}</div>
    </div>
  );
}

export function Panel({
  title,
  hint,
  children,
  className = "",
}: {
  title?: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`dk-card flex min-h-0 flex-col gap-3 p-4 ${className}`}
    >
      {title && (
        <header className="flex shrink-0 items-baseline gap-3">
          <h3 className="text-[19px] font-bold text-[var(--dk-ink)]">{title}</h3>
          {hint && (
            <span className="text-[15px] text-[var(--dk-ink-3)]">{hint}</span>
          )}
        </header>
      )}
      {/* Panels stretch to the grid row, so an unfilled panel would leave a
          dead band at the bottom of a wall screen. Centring the body reads as
          a deliberate block instead of content that ran out. */}
      <div className="flex min-h-0 flex-1 flex-col justify-center">
        {children}
      </div>
    </section>
  );
}

/** A pointer to the file the panel is describing — the presenter can open it. */
export function CodeRef({ path }: { path: string }) {
  return (
    <code
      dir="ltr"
      className="rounded-md bg-[var(--dk-surface-2)] px-2 py-0.5 font-mono text-[13px] text-[var(--dk-ink-3)]"
    >
      {path}
    </code>
  );
}

export function Chip({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "bad" | "warn" | "accent";
}) {
  const tones: Record<string, string> = {
    neutral: "border-[var(--dk-border)] text-[var(--dk-ink-2)]",
    good: "border-[var(--dk-good)]/45 text-[var(--dk-good)] bg-[var(--dk-good)]/8",
    bad: "border-[var(--dk-bad)]/45 text-[var(--dk-bad)] bg-[var(--dk-bad)]/8",
    warn: "border-[var(--dk-warn)]/45 text-[var(--dk-warn)] bg-[var(--dk-warn)]/8",
    accent:
      "border-[var(--dk-accent)]/45 text-[var(--dk-accent)] bg-[var(--dk-accent-dim)]",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[13.5px] font-semibold ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

/* ── sub-navigation inside a module ─────────────────────────────── */

export interface TabDef {
  id: string;
  label_he: string;
}

export function SubNav({
  tabs,
  active,
  onSelect,
}: {
  tabs: TabDef[];
  active: string;
  onSelect: (id: string) => void;
}) {
  return (
    <nav className="flex shrink-0 flex-wrap gap-2">
      {tabs.map((t, i) => (
        <button
          key={t.id}
          onClick={() => onSelect(t.id)}
          className={`rounded-xl border px-4 py-2 text-[16.5px] font-semibold transition-colors ${
            active === t.id
              ? "border-[var(--dk-accent)] bg-[var(--dk-accent-dim)] text-[var(--dk-accent)]"
              : "border-[var(--dk-border)] text-[var(--dk-ink-2)] hover:text-[var(--dk-ink)]"
          }`}
        >
          <span
            className="ms-2 font-mono text-[13px] text-[var(--dk-ink-3)]"
            dir="ltr"
          >
            {i + 1}
          </span>
          {t.label_he}
        </button>
      ))}
    </nav>
  );
}

/* ── diagram primitives ─────────────────────────────────────────── */

/** One box in a flow or tree. */
export function Node({
  title,
  sub,
  tone = "neutral",
  mono = false,
  wide = false,
}: {
  title: string;
  sub?: ReactNode;
  tone?: "neutral" | "good" | "bad" | "accent" | "muted";
  mono?: boolean;
  wide?: boolean;
}) {
  const tones: Record<string, string> = {
    neutral: "border-[var(--dk-border)] bg-[var(--dk-surface-2)]",
    muted: "border-dashed border-[var(--dk-border)] opacity-55",
    good: "border-[var(--dk-good)]/45 bg-[var(--dk-good)]/8",
    bad: "border-[var(--dk-bad)]/45 bg-[var(--dk-bad)]/8",
    accent: "border-[var(--dk-accent)]/55 bg-[var(--dk-accent-dim)]",
  };
  return (
    <div
      className={`flex flex-col justify-center gap-1 rounded-xl border px-3.5 py-2.5 ${tones[tone]} ${wide ? "flex-1" : ""}`}
    >
      <div
        className={`text-[16.5px] font-bold leading-tight ${mono ? "font-mono" : ""}`}
        dir={mono ? "ltr" : undefined}
      >
        {title}
      </div>
      {sub && (
        <div className="text-[14.5px] leading-snug text-[var(--dk-ink-2)]">
          {sub}
        </div>
      )}
    </div>
  );
}

/** RTL flow arrow with an optional condition label riding on it. */
export function Arrow({ label }: { label?: string }) {
  return (
    <div className="flex shrink-0 flex-col items-center justify-center px-1.5">
      <span className="text-xl leading-none text-[var(--dk-ink-3)]" aria-hidden>
        ←
      </span>
      {label && (
        <span className="mt-0.5 whitespace-nowrap text-[12.5px] text-[var(--dk-ink-3)]">
          {label}
        </span>
      )}
    </div>
  );
}

/**
 * A fallback ladder: each rung is tried in order, and the condition on the
 * right is what has to fail before the next rung is reached.
 */
export function Ladder({
  rungs,
}: {
  rungs: {
    label: string;
    detail: ReactNode;
    fallsThroughWhen?: string;
    tone?: "neutral" | "good" | "bad" | "accent";
    mono?: boolean;
  }[];
}) {
  return (
    <ol className="flex flex-col gap-0">
      {rungs.map((r, i) => (
        <li key={r.label}>
          <div className="flex items-stretch gap-3">
            <div className="flex w-9 shrink-0 items-center justify-center">
              <span className="flex h-7 w-7 items-center justify-center rounded-full border border-[var(--dk-border)] bg-[var(--dk-surface-2)] font-mono text-[14.5px] text-[var(--dk-ink-2)]">
                {i + 1}
              </span>
            </div>
            <div className="flex-1">
              <Node title={r.label} sub={r.detail} tone={r.tone} mono={r.mono} />
            </div>
          </div>
          {r.fallsThroughWhen && (
            <div className="flex items-center gap-3 py-1">
              <div className="flex w-9 shrink-0 justify-center">
                <span className="text-lg text-[var(--dk-ink-3)]" aria-hidden>
                  ↓
                </span>
              </div>
              <span className="text-[13.5px] text-[var(--dk-warn)]">
                {r.fallsThroughWhen}
              </span>
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}

/* ── the metric card: the thing that was missing ─────────────────── */

/**
 * Every number the system puts on a screen gets one of these: what it is,
 * the formula that produces it, the range it lives in, how to read a value,
 * and what this snapshot actually measured. A number without all five is a
 * number the audience cannot check.
 */
export function MetricCard({
  name,
  field,
  formula,
  range,
  reads,
  measured,
}: {
  name: string;
  field: string;
  formula: string;
  range: string;
  reads: { value: string; means: string }[];
  measured?: ReactNode;
}) {
  return (
    <article className="flex flex-col gap-2 rounded-2xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/60 p-3">
      <header className="flex items-baseline justify-between gap-2">
        <h4 className="text-[17.5px] font-bold">{name}</h4>
        <code
          dir="ltr"
          className="font-mono text-[13px] text-[var(--dk-ink-3)]"
        >
          {field}
        </code>
      </header>

      <div
        dir="ltr"
        className="rounded-lg border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)]/40 px-3 py-2 text-center font-mono text-[16px] text-[var(--dk-accent)]"
      >
        {formula}
      </div>

      <div className="flex items-center gap-2 text-[14.5px] text-[var(--dk-ink-2)]">
        <span className="text-[var(--dk-ink-3)]">תחום:</span>
        <code dir="ltr" className="font-mono">
          {range}
        </code>
      </div>

      <dl className="flex flex-col gap-1.5">
        {reads.map((r) => (
          <div key={r.value} className="flex items-start gap-2 text-[15px]">
            <dt
              dir="ltr"
              className="mt-px w-[74px] shrink-0 text-right font-mono font-bold text-[var(--dk-ink)]"
            >
              {r.value}
            </dt>
            <dd className="leading-snug text-[var(--dk-ink-2)]">{r.means}</dd>
          </div>
        ))}
      </dl>

      {measured && (
        <footer className="mt-auto rounded-lg border border-[var(--dk-good)]/30 bg-[var(--dk-good)]/6 px-3 py-1.5 text-[14.5px] text-[var(--dk-ink-2)]">
          <span className="font-semibold text-[var(--dk-good)]">בסנאפשוט: </span>
          {measured}
        </footer>
      )}
    </article>
  );
}

/* ── tiny charts ────────────────────────────────────────────────── */

export function BarRow({
  label,
  n,
  max,
  tone = "accent",
  note,
  unit,
}: {
  label: string;
  n: number;
  max: number;
  tone?: "accent" | "good" | "bad" | "muted";
  note?: string;
  /** appended to the value, for bars whose number is not a count */
  unit?: string;
}) {
  const colors: Record<string, string> = {
    accent: "bg-[var(--dk-accent)]",
    good: "bg-[var(--dk-good)]",
    bad: "bg-[var(--dk-bad)]",
    muted: "bg-[var(--dk-ink-3)]",
  };
  const pct = max > 0 ? (n / max) * 100 : 0;
  return (
    <div className="flex items-center gap-2.5">
      <span
        dir="ltr"
        className="w-[68px] shrink-0 text-left font-mono text-[13.5px] text-[var(--dk-ink-2)]"
      >
        {label}
      </span>
      <div className="h-4 flex-1 overflow-hidden rounded-md bg-[var(--dk-surface-2)]">
        <div
          className={`h-full rounded-md ${colors[tone]}`}
          style={{ width: `${Math.max(pct, n > 0 ? 1.5 : 0)}%` }}
        />
      </div>
      <span
        dir="ltr"
        className="w-[52px] shrink-0 text-left font-mono text-[13.5px] text-[var(--dk-ink-2)]"
      >
        {n.toLocaleString("en-US")}
        {unit}
      </span>
      {note && (
        <span className="w-[112px] shrink-0 text-[13px] text-[var(--dk-ink-3)]">
          {note}
        </span>
      )}
    </div>
  );
}

/** The line a module uses to admit what it does NOT do. */
export function Caveat({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-xl border border-[var(--dk-warn)]/30 bg-[var(--dk-warn)]/6 px-3.5 py-2 text-[15px] leading-snug text-[var(--dk-ink-2)]">
      <span className="font-bold text-[var(--dk-warn)]">מגבלה: </span>
      {children}
    </p>
  );
}
