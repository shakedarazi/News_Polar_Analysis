"use client";

import { useEffect, useState } from "react";
import { agentColor, findAgent } from "./roster";
import type { AgentInfo, DebateSession } from "./types";

const CLOSE_AFTER_END_MS = 4_000;
/** safety: never let a stuck debate cover the screen forever */
const MAX_OPEN_MS = 90_000;

/** progressive text reveal, ~2 chars per frame tick */
function TypewriterText({ text }: { text: string }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    setShown(0);
    const interval = setInterval(() => {
      setShown((n) => {
        if (n >= text.length) {
          clearInterval(interval);
          return n;
        }
        return n + 2;
      });
    }, 28);
    return () => clearInterval(interval);
  }, [text]);
  return <>{text.slice(0, shown)}</>;
}

interface DebateOverlayProps {
  debate: DebateSession;
  agents: AgentInfo[];
  onClose: () => void;
}

export function DebateOverlay({ debate, agents, onClose }: DebateOverlayProps) {
  const ended = debate.end !== null;

  useEffect(() => {
    const t = setTimeout(onClose, ended ? CLOSE_AFTER_END_MS : MAX_OPEN_MS);
    return () => clearTimeout(t);
  }, [ended, onClose]);

  const [first, second] = debate.start.participants;

  return (
    <div className="dk-dim-in absolute inset-0 z-20 flex items-center justify-center bg-[#05080f]/55">
      <div className="dk-card dk-scale-in relative flex max-h-[86%] w-[62%] max-w-[760px] flex-col overflow-hidden border-[#fb923c]/30 p-6">
        <div className="mb-1 flex items-center gap-2 text-sm font-bold text-[#fb923c]">
          <span className="h-2 w-2 animate-pulse rounded-full bg-[#fb923c]" />
          עימות עמיתים · {debate.start.reason_he}
        </div>
        <h3 className="dk-truncate mb-4 text-2xl font-bold">
          {debate.start.title}
        </h3>

        <div className="flex flex-col gap-3 overflow-hidden">
          {debate.turns.slice(-4).map((turn, i, arr) => {
            const agent = findAgent(agents, turn.agent);
            const isFirst = turn.agent === first;
            const color = agentColor(agent);
            const isLast = i === arr.length - 1;
            const absoluteIdx = debate.turns.length - arr.length + i;
            return (
              <div
                key={`${turn.debate_id}-${absoluteIdx}`}
                className={`dk-fade-up flex max-w-[85%] items-start gap-2.5 ${
                  isFirst ? "self-start" : "self-end flex-row-reverse"
                }`}
              >
                <span className="mt-1 text-2xl leading-none">
                  {agent?.emoji ?? "🤖"}
                </span>
                <div
                  className="rounded-2xl border px-4 py-2.5 text-[17px] leading-relaxed"
                  style={{
                    borderColor: `${color}55`,
                    background: `${color}14`,
                  }}
                >
                  <div
                    className="mb-0.5 text-[13px] font-bold"
                    style={{ color }}
                  >
                    {agent?.name_he ?? turn.agent}
                  </div>
                  {isLast && !ended ? (
                    <TypewriterText text={turn.text_he} />
                  ) : (
                    turn.text_he
                  )}
                </div>
              </div>
            );
          })}
          {debate.turns.length === 0 && (
            <div className="dk-breathe py-6 text-center text-[var(--dk-ink-2)]">
              {findAgent(agents, first)?.name_he ?? first} ו
              {findAgent(agents, second ?? "")?.name_he ?? second} נערכים
              לעימות…
            </div>
          )}
        </div>

        {debate.end && (
          <div className="mt-5 flex items-center justify-center gap-4">
            <div
              className={`dk-stamp rounded-lg border-4 px-6 py-2 text-2xl font-black tracking-wide ${
                debate.end.changed
                  ? "border-[#fb923c] text-[#fb923c]"
                  : "border-[var(--dk-good)] text-[var(--dk-good)]"
              }`}
            >
              {debate.end.changed ? "שונה" : "אושר"} ·{" "}
              {debate.end.final_category}
            </div>
            <div className="max-w-[45%] text-[15px] leading-snug text-[var(--dk-ink-2)]">
              {debate.end.verdict_he}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
