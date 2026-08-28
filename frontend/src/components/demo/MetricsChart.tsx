"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import type { MetricEvent } from "./types";

const ACCENT = "#22d3ee";

interface ChartDatum {
  name: string;
  accuracy: number;
}

interface PointLabelProps {
  x?: number | string;
  y?: number | string;
  value?: number | string;
}

/** big percent label above each point (kiosk: readable from 2–3m) */
function PointLabel({ x, y, value }: PointLabelProps) {
  const px = typeof x === "number" ? x : Number(x ?? 0);
  const py = typeof y === "number" ? y : Number(y ?? 0);
  return (
    <text
      x={px}
      y={py - 14}
      textAnchor="middle"
      fontSize={22}
      fontWeight={700}
      fill="var(--dk-ink)"
    >
      {Math.round(Number(value ?? 0))}%
    </text>
  );
}

interface MetricsChartProps {
  metrics: MetricEvent[];
  learned: number;
}

export function MetricsChart({ metrics, learned }: MetricsChartProps) {
  const data: ChartDatum[] = metrics.map((m) => ({
    name: m.label_he,
    accuracy: Math.round((m.accuracy ?? 0) * 100),
  }));

  return (
    <section className="dk-card flex h-full flex-col p-4">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-lg font-bold text-[var(--dk-ink-2)]">
          דיוק לפי סבב
        </h2>
        <div className="flex items-center gap-1.5 text-sm text-[var(--dk-ink-2)]">
          <span className="text-base">🧠</span>
          <span
            key={learned}
            className="dk-pop text-lg font-bold text-[var(--dk-ink)]"
          >
            {learned}
          </span>
          דוגמאות בזיכרון
        </div>
      </div>
      {data.length === 0 ? (
        <div className="dk-breathe flex flex-1 items-center justify-center text-[var(--dk-ink-3)]">
          הסבב הראשון עדיין רץ…
        </div>
      ) : (
        <div
          key={data.length}
          className="dk-scale-in min-h-0 flex-1"
          dir="ltr"
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data}
              margin={{ top: 34, right: 24, bottom: 0, left: 24 }}
            >
              <CartesianGrid
                vertical={false}
                stroke="rgba(148,163,184,0.12)"
                strokeWidth={1}
              />
              <XAxis
                dataKey="name"
                axisLine={{ stroke: "rgba(148,163,184,0.25)" }}
                tickLine={false}
                tick={{
                  fill: "var(--dk-ink-2)",
                  fontSize: 15,
                  fontWeight: 600,
                }}
                interval={0}
              />
              <YAxis domain={[0, 100]} hide />
              <Area
                type="monotone"
                dataKey="accuracy"
                stroke={ACCENT}
                strokeWidth={2}
                fill={ACCENT}
                fillOpacity={0.1}
                isAnimationActive={false}
                dot={{
                  r: 5,
                  fill: ACCENT,
                  stroke: "var(--dk-surface)",
                  strokeWidth: 2,
                }}
              >
                <LabelList dataKey="accuracy" content={<PointLabel />} />
              </Area>
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
