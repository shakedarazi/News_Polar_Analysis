"use client";

import { sourceLabel } from "@/lib/format";
import { LOGO_COLOR, LOGO_TEXT } from "./SourceLogo";

/**
 * The shared y-axis tick for the per-source bar charts.
 *
 * It carries the sample size next to the outlet name because a percentage bar
 * is the same width whether it was cut from 13 articles or 291, and the count
 * used to live only in the tooltip — invisible to anyone reading the chart
 * rather than probing it. The wording matches EventDeviationChart's `n=` row
 * on purpose; two different treatments of the same caveat would read as two
 * different caveats.
 */
export const SMALL_SAMPLE_MIN = 30;

export function isSmallSample(count: number | undefined): boolean {
  return typeof count === "number" && count > 0 && count < SMALL_SAMPLE_MIN;
}

type AxisTickProps = {
  x?: string | number;
  y?: string | number;
  payload?: { value: string };
};

/** Recharts passes the tick its category value only, so the counts are closed
 * over here rather than threaded through the chart. */
export function makeSourceAxisTick(counts: Record<string, number>) {
  return function SourceAxisTick(props: AxisTickProps) {
    const x = Number(props.x ?? 0);
    const y = Number(props.y ?? 0);
    const source = props.payload?.value ?? "";
    const color = LOGO_COLOR[source] ?? "#64748B";
    const logoText = LOGO_TEXT[source] ?? source.slice(0, 2).toUpperCase();
    const count = counts[source];
    const showCount = typeof count === "number";
    const small = isSmallSample(count);

    return (
      <g transform={`translate(${x},${y})`}>
        <circle cx={-118} cy={0} r={10} fill={color} />
        <text x={-118} y={0} dy={3} textAnchor="middle" fontSize={9} fontWeight={700} fill="#fff">
          {logoText}
        </text>
        <text
          x={-8}
          y={0}
          dy={showCount ? -2 : 4}
          textAnchor="end"
          fontSize={12}
          fill="var(--text-secondary)"
        >
          {sourceLabel(source)}
        </text>
        {showCount && (
          <text x={-8} y={0} dy={12} textAnchor="end" fontSize={10} fill="var(--text-secondary)" opacity={0.65}>
            {small ? `n=${count} · מדגם קטן` : `n=${count}`}
          </text>
        )}
      </g>
    );
  };
}
