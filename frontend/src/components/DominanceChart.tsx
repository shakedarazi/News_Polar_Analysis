"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { WindowFeature } from "@/lib/types";

export function DominanceChart({ windows }: { windows: WindowFeature[] }) {
  const data = windows.map((w) => ({
    idx: w.sentence_idx + 1,
    dominance: w.dominance !== null ? Number((w.dominance * 100).toFixed(1)) : null,
    active: w.active,
  }));

  return (
    <div className="card p-5">
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="idx"
              tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
              label={{ value: "משפט", position: "insideBottom", offset: -4, fill: "var(--text-secondary)" }}
            />
            <YAxis tick={{ fontSize: 12, fill: "var(--text-secondary)" }} unit="%" />
            <Tooltip
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: "var(--text-primary)",
              }}
              labelStyle={{ color: "var(--text-primary)" }}
              formatter={(value, name) => {
                if (name === "dominance") return [`${value}%`, "דומיננטיות"];
                return [value, "קטגוריות פעילות"];
              }}
              labelFormatter={(l) => `משפט ${l}`}
            />
            <Line
              type="monotone"
              dataKey="dominance"
              stroke="#c2410c"
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
        דומיננטיות = ריכוז הקטגוריה הדומיננטית במשפט (מילון 7 קטגוריות)
      </p>
    </div>
  );
}
