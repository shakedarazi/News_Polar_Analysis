"use client";

import { findAgent } from "./roster";
import type { AgentInfo, DemoState } from "./types";

function formatTokens(n: number): string {
  return n.toLocaleString("he-IL");
}

interface TokenEconomyProps {
  tokens: DemoState["tokens"];
  agents: AgentInfo[];
}

export function TokenEconomy({ tokens, agents }: TokenEconomyProps) {
  const lastAgent = tokens.lastAgent
    ? findAgent(agents, tokens.lastAgent)
    : undefined;

  return (
    <section className="dk-card flex h-full flex-col p-4">
      <h2 className="mb-2 text-lg font-bold text-[var(--dk-ink-2)]">
        כלכלת אסימונים
      </h2>
      <div className="flex flex-1 items-center justify-around gap-3">
        <div className="text-center">
          <div
            key={`t-${tokens.pulse}`}
            className="dk-pop text-4xl font-bold tracking-tight"
          >
            {formatTokens(tokens.totalTokens)}
          </div>
          <div className="mt-1 text-sm text-[var(--dk-ink-2)]">
            אסימונים סה״כ
          </div>
        </div>
        <div className="h-12 w-px bg-[var(--dk-border)]" aria-hidden />
        <div className="text-center" dir="ltr">
          <div
            key={`c-${tokens.pulse}`}
            className="dk-pop text-4xl font-bold tracking-tight text-[var(--dk-accent)]"
          >
            ${tokens.totalCostUsd.toFixed(4)}
          </div>
          <div className="mt-1 text-sm text-[var(--dk-ink-2)]" dir="rtl">
            עלות כוללת
          </div>
        </div>
        <div className="h-12 w-px bg-[var(--dk-border)]" aria-hidden />
        <div className="text-center">
          <div className="text-3xl leading-tight">
            {lastAgent ? lastAgent.emoji : "—"}
          </div>
          <div className="mt-1 text-sm text-[var(--dk-ink-2)]">
            {lastAgent ? `קריאה אחרונה: ${lastAgent.name_he}` : "אין קריאות"}
          </div>
        </div>
      </div>
    </section>
  );
}
