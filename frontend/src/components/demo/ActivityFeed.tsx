"use client";

import { findAgent } from "./roster";
import type { AgentInfo, FeedItem, ReasoningLevel } from "./types";

const MAX_VISIBLE = 9;

function rowClasses(level: ReasoningLevel): string {
  switch (level) {
    case "decision":
      return "border-[var(--dk-accent)]/35 bg-[var(--dk-accent-dim)]";
    case "warn":
      return "border-[var(--dk-warn)]/35 bg-[var(--dk-warn)]/10";
    default:
      return "border-[var(--dk-border)] bg-[var(--dk-surface-2)]/60";
  }
}

interface ActivityFeedProps {
  feed: FeedItem[];
  agents: AgentInfo[];
}

export function ActivityFeed({ feed, agents }: ActivityFeedProps) {
  return (
    <section className="dk-card flex h-full flex-col overflow-hidden p-4">
      <h2 className="mb-3 flex items-center gap-2 text-lg font-bold text-[var(--dk-ink-2)]">
        <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--dk-good)]" />
        זרם חשיבה חי
      </h2>
      <ol className="flex flex-1 flex-col gap-2 overflow-hidden">
        {feed.slice(0, MAX_VISIBLE).map((item, idx) => {
          const agent = findAgent(agents, item.agent);
          return (
            <li
              key={item.id}
              className={`dk-fade-up flex items-start gap-2.5 rounded-xl border px-3 py-2 ${rowClasses(item.level)}`}
            >
              <span className="mt-0.5 text-xl leading-none">
                {agent?.emoji ?? "🤖"}
              </span>
              <span
                className={`${idx === 0 ? "" : "dk-clamp-2 "}text-[15px] leading-snug ${
                  item.level === "decision"
                    ? "font-semibold text-[var(--dk-ink)]"
                    : item.level === "warn"
                      ? "text-[var(--dk-warn)]"
                      : "text-[var(--dk-ink-2)]"
                }`}
              >
                {item.text_he}
              </span>
            </li>
          );
        })}
        {feed.length === 0 && (
          <li className="dk-breathe mt-6 text-center text-[var(--dk-ink-3)]">
            הסוכנים עוד לא התחילו לדבר…
          </li>
        )}
      </ol>
    </section>
  );
}
