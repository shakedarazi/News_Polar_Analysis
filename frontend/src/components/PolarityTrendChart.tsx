"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PolarityTrendPoint } from "@/lib/types";
import { formatShortDate } from "@/lib/format";
import { EmptyState } from "./EmptyState";

export function PolarityTrendChart({ data }: { data: PolarityTrendPoint[] }) {
  const points = data.filter((d): d is PolarityTrendPoint & { avg_polarity: number } =>
    d.avg_polarity !== null,
  );

  if (points.length < 2) {
    return (
      <EmptyState message="אין מספיק נתונים להצגת מגמה — נדרשות כתבות עם תגובות שנותחו לפחות בשני ימים שונים." />
    );
  }

  const avgPolarity =
    points.reduce((sum, p) => sum + p.avg_polarity, 0) / points.length;

  const chartData = data.map((d) => ({
    date: d.date,
    avg_polarity: d.avg_polarity !== null ? Number((d.avg_polarity * 100).toFixed(2)) : null,
    article_count: d.article_count,
  }));

  return (
    <div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="polarityFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6C63FF" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#6C63FF" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              tickFormatter={(v) => formatShortDate(v)}
              tick={{ fontSize: 12 }}
            />
            <YAxis tick={{ fontSize: 12 }} unit="%" width={44} />
            <ReferenceLine
              y={Number((avgPolarity * 100).toFixed(2))}
              stroke="#A8B0BB"
              strokeDasharray="4 4"
              label={{ value: "ממוצע התקופה", fontSize: 11, fill: "#64748b" }}
            />
            <Tooltip
              labelFormatter={(v) => formatShortDate(String(v))}
              formatter={(value, name) => {
                if (name === "avg_polarity") return [`${value}%`, "קיטוב ממוצע"];
                if (name === "article_count") return [value, "כתבות שנותחו"];
                return [value, name];
              }}
            />
            <Area
              type="monotone"
              dataKey="avg_polarity"
              stroke="#6C63FF"
              strokeWidth={2.5}
              fill="url(#polarityFill)"
              dot={{ r: 3, fill: "#6C63FF" }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-slate-400">
        קיטוב = ממוצע משוקלל של עוצמת התגובות הפוליטיות/רגשיות לפי מילון, מקובץ לפי תאריך
        פרסום הכתבה. זהו מדד עוצמה (0 ומעלה), לא סיווג חיובי/שלילי.
      </p>
    </div>
  );
}
