"use client";

import { useEffect, useMemo, useRef } from "react";
import { agentColor, KIND_COLORS, STATE_LABELS_HE } from "./roster";
import type {
  AgentInfo,
  AgentLiveStatus,
  AgentStateId,
  Beam,
} from "./types";

const VIEW_W = 1000;
const VIEW_H = 640;
const CX = VIEW_W / 2;
const CY = 300;
const RADIUS = 205;
const NODE_R = 56;
const BEAM_LIFETIME_MS = 2_000;

interface NodePos {
  x: number;
  y: number;
}

function pentagonPositions(count: number): NodePos[] {
  return Array.from({ length: count }, (_, i) => {
    const angle = ((-90 + (i * 360) / Math.max(count, 1)) * Math.PI) / 180;
    return {
      x: CX + RADIUS * Math.cos(angle),
      y: CY + RADIUS * Math.sin(angle),
    };
  });
}

function glowClass(state: AgentStateId): string {
  switch (state) {
    case "working":
      return "dk-node-glow-working";
    case "debating":
      return "dk-node-glow-debating";
    case "error":
      return "dk-node-glow-error";
    default:
      return "";
  }
}

function glowColor(state: AgentStateId, base: string): string {
  switch (state) {
    case "debating":
      return "#fb923c";
    case "error":
      return "#f87171";
    case "working":
      return base;
    default:
      return base;
  }
}

function nodeOpacity(state: AgentStateId): number {
  switch (state) {
    case "idle":
      return 0.55;
    case "waiting":
      return 0.75;
    default:
      return 1;
  }
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

interface AgentMapProps {
  agents: AgentInfo[];
  agentStatus: Record<string, AgentLiveStatus>;
  beams: Beam[];
  idle: boolean;
  expireBeam: (id: number) => void;
}

export function AgentMap({
  agents,
  agentStatus,
  beams,
  idle,
  expireBeam,
}: AgentMapProps) {
  const sorted = useMemo(
    () => [...agents].sort((a, b) => a.tier - b.tier),
    [agents],
  );
  const positions = useMemo(
    () => pentagonPositions(sorted.length),
    [sorted.length],
  );
  const posById = useMemo(() => {
    const map = new Map<string, NodePos>();
    sorted.forEach((a, i) => map.set(a.id, positions[i]));
    return map;
  }, [sorted, positions]);

  /* expire beams after their animation finishes */
  const scheduled = useRef<Map<number, ReturnType<typeof setTimeout>>>(
    new Map(),
  );
  useEffect(() => {
    for (const beam of beams) {
      if (!scheduled.current.has(beam.id)) {
        scheduled.current.set(
          beam.id,
          setTimeout(() => {
            scheduled.current.delete(beam.id);
            expireBeam(beam.id);
          }, BEAM_LIFETIME_MS),
        );
      }
    }
  }, [beams, expireBeam]);
  useEffect(() => {
    const timers = scheduled.current;
    return () => {
      for (const t of timers.values()) clearTimeout(t);
      timers.clear();
    };
  }, []);

  return (
    <div className="relative h-full w-full">
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        className="h-full w-full"
        role="img"
        aria-label="מפת הסוכנים"
      >
        <defs>
          <radialGradient id="dk-node-bg" cx="50%" cy="38%" r="70%">
            <stop offset="0%" stopColor="#16213a" />
            <stop offset="100%" stopColor="#0c1322" />
          </radialGradient>
        </defs>

        {/* static web between nodes */}
        <g stroke="rgba(148,163,184,0.09)" strokeWidth={1}>
          {sorted.map((a, i) =>
            sorted.slice(i + 1).map((b, j) => (
              <line
                key={`${a.id}-${b.id}-${j}`}
                x1={positions[i].x}
                y1={positions[i].y}
                x2={posById.get(b.id)?.x}
                y2={posById.get(b.id)?.y}
              />
            )),
          )}
        </g>

        {/* message beams */}
        {beams.map((beam) => {
          const from = posById.get(beam.from);
          const to = posById.get(beam.to);
          if (!from || !to) return null;
          const color = KIND_COLORS[beam.kind] ?? "#60a5fa";
          const midX = (from.x + to.x) / 2;
          const midY = (from.y + to.y) / 2;
          const beamVars = {
            "--bx0": `${from.x}px`,
            "--by0": `${from.y}px`,
            "--bx1": `${to.x}px`,
            "--by1": `${to.y}px`,
          } as React.CSSProperties;
          return (
            <g key={beam.id}>
              <line
                className="dk-beam-line"
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke={color}
                strokeWidth={2.5}
                strokeLinecap="round"
              />
              <g className="dk-beam-dot" style={beamVars}>
                <circle r={13} fill={color} opacity={0.25} />
                <circle r={6} fill={color} />
              </g>
              {beam.summary_he && (
                <g className="dk-beam-label">
                  <text
                    x={midX}
                    y={midY - 14}
                    textAnchor="middle"
                    fontSize={17}
                    fontWeight={600}
                    fill="var(--dk-ink)"
                    stroke="rgba(5,8,15,0.85)"
                    strokeWidth={4}
                    paintOrder="stroke"
                  >
                    {truncate(beam.summary_he, 26)}
                  </text>
                  <circle cx={midX} cy={midY + 2} r={4} fill={color} />
                </g>
              )}
            </g>
          );
        })}

        {/* agent nodes */}
        {sorted.map((agent, i) => {
          const { x, y } = positions[i];
          const status = agentStatus[agent.id]?.state ?? "idle";
          const task = agentStatus[agent.id]?.task_he;
          const color = agentColor(agent);
          const glow = glowClass(status);
          return (
            <g key={agent.id} opacity={nodeOpacity(status)}>
              {/* state glow */}
              {glow ? (
                <circle
                  className={glow}
                  cx={x}
                  cy={y}
                  r={NODE_R + 12}
                  fill={glowColor(status, color)}
                  opacity={0.4}
                />
              ) : (
                <circle
                  cx={x}
                  cy={y}
                  r={NODE_R + 8}
                  fill={color}
                  opacity={status === "done" ? 0.22 : 0.08}
                />
              )}
              <circle
                cx={x}
                cy={y}
                r={NODE_R}
                fill="url(#dk-node-bg)"
                stroke={color}
                strokeWidth={status === "idle" ? 1.5 : 3}
              />
              {/* tier ring — one arc segment per tier point */}
              <g>
                {Array.from({ length: 5 }, (_, t) => {
                  const start = -90 + t * 72 + 6;
                  const end = -90 + (t + 1) * 72 - 6;
                  const r = NODE_R + 5;
                  const a0 = (start * Math.PI) / 180;
                  const a1 = (end * Math.PI) / 180;
                  return (
                    <path
                      key={t}
                      d={`M ${x + r * Math.cos(a0)} ${y + r * Math.sin(a0)} A ${r} ${r} 0 0 1 ${x + r * Math.cos(a1)} ${y + r * Math.sin(a1)}`}
                      fill="none"
                      stroke={t < agent.tier ? color : "rgba(148,163,184,0.18)"}
                      strokeWidth={3.5}
                      strokeLinecap="round"
                    />
                  );
                })}
              </g>
              <text x={x} y={y + 15} textAnchor="middle" fontSize={46}>
                {agent.emoji}
              </text>
              {/* name + role */}
              <text
                x={x}
                y={y + NODE_R + 34}
                textAnchor="middle"
                fontSize={23}
                fontWeight={700}
                fill="var(--dk-ink)"
              >
                {agent.name_he}
              </text>
              <text
                x={x}
                y={y + NODE_R + 58}
                textAnchor="middle"
                fontSize={16}
                fill="var(--dk-ink-2)"
              >
                {agent.role_he}
              </text>
              {/* status / task */}
              <text
                x={x}
                y={y + NODE_R + 80}
                textAnchor="middle"
                fontSize={14}
                fill={
                  status === "error"
                    ? "var(--dk-bad)"
                    : status === "debating"
                      ? "#fb923c"
                      : "var(--dk-ink-3)"
                }
              >
                {task ? truncate(task, 30) : STATE_LABELS_HE[status]}
              </text>
              {/* tier badge */}
              <g>
                <rect
                  x={x - 30}
                  y={y - NODE_R - 32}
                  width={60}
                  height={22}
                  rx={11}
                  fill={color}
                  opacity={0.18}
                />
                <text
                  x={x}
                  y={y - NODE_R - 16}
                  textAnchor="middle"
                  fontSize={14}
                  fontWeight={700}
                  fill="var(--dk-ink)"
                >
                  דרג {agent.tier}
                </text>
              </g>
            </g>
          );
        })}

        {/* idle center pulse */}
        {idle && (
          <g className="dk-idle-pulse">
            <text
              x={CX}
              y={CY + 8}
              textAnchor="middle"
              fontSize={26}
              fontWeight={600}
              fill="var(--dk-ink-2)"
            >
              ממתין לריצה הבאה…
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
