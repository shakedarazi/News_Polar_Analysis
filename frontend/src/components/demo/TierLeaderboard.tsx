"use client";

import { useMemo } from "react";
import { agentColor } from "./roster";
import type { AgentInfo } from "./types";

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

interface TierLeaderboardProps {
  agents: AgentInfo[];
  activeAgent: string | null;
}

export function TierLeaderboard({ agents, activeAgent }: TierLeaderboardProps) {
  const sorted = useMemo(
    () => [...agents].sort((a, b) => b.tier - a.tier),
    [agents],
  );

  return (
    <section className="dk-card flex h-full flex-col p-4">
      <h2 className="mb-2 text-lg font-bold text-[var(--dk-ink-2)]">
        דרגות הנחיל
      </h2>
      <ol className="flex flex-1 flex-col justify-between gap-1">
        {sorted.map((agent) => {
          const color = agentColor(agent);
          const active = agent.id === activeAgent;
          return (
            <li
              key={agent.id}
              className={`flex items-center gap-3 rounded-xl px-2.5 py-1 transition-all duration-300 ${
                active
                  ? "bg-[var(--dk-surface-2)] ring-1 ring-[var(--dk-accent)]/40"
                  : ""
              }`}
            >
              <span className="text-2xl leading-none">{agent.emoji}</span>
              <span className="w-16 shrink-0 text-base font-bold">
                {agent.name_he}
              </span>
              {/* 5-segment tier bar (2px surface gaps between fills) */}
              <span className="flex flex-1 gap-0.5" aria-hidden>
                {Array.from({ length: 5 }, (_, i) => (
                  <span
                    key={i}
                    className="h-2.5 flex-1 rounded-full"
                    style={{
                      background:
                        i < agent.tier ? color : "rgba(148,163,184,0.15)",
                    }}
                  />
                ))}
              </span>
              <span className="w-20 shrink-0 text-left text-[13px] text-[var(--dk-ink-2)]">
                {truncate(agent.tier_label_he, 12)}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
