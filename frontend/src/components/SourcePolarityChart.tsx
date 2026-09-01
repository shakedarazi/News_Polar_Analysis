"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SourcePolarityBreakdown } from "@/lib/types";
import { polarityStackPercents, sourceLabel } from "@/lib/format";
import { EmptyState } from "./EmptyState";
import { isSmallSample, makeSourceAxisTick, SMALL_SAMPLE_MIN } from "./SourceAxisTick";

export function SourcePolarityChart({ data }: { data: SourcePolarityBreakdown[] }) {
  if (data.length === 0) {
    return (
      <EmptyState message="לא קיימים נתוני קיטוב עבור המקורות בתקופה שנבחרה." />
    );
  }

  const rows = data.map((d) => {
    const shares = polarityStackPercents(d.low_count, d.mid_count, d.high_count, d.analyzed_count);
    return {
      name: d.source,
      total: d.article_count,
      analyzed: d.analyzed_count,
      ...shares,
      lowCount: d.low_count,
      midCount: d.mid_count,
      highCount: d.high_count,
    };
  });

  // The bar shows shares of the analysed articles, so that — not the total
  // crawled — is the n a reader needs to judge the bar by.
  const counts = Object.fromEntries(rows.map((r) => [r.name, r.analyzed]));
  const SourceAxisTick = makeSourceAxisTick(counts);
  const smallSamples = rows.filter((r) => isSmallSample(r.analyzed));
  const height = Math.max(160, rows.length * 64);

  return (
    <div>
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            barSize={22}
            barCategoryGap="35%"
            margin={{ top: 8, right: 8, left: 8, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis
              type="number"
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              tickFormatter={(value) => `${value}%`}
              allowDecimals={false}
              tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={140}
              axisLine={false}
              tickLine={false}
              tick={SourceAxisTick}
            />
            <Tooltip
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: "var(--text-primary)",
              }}
              labelStyle={{ color: "var(--text-primary)" }}
              labelFormatter={(value) => sourceLabel(String(value))}
              formatter={(value, name, item) => {
                const payload = item.payload as {
                  analyzed: number;
                  total: number;
                  lowCount: number;
                  midCount: number;
                  highCount: number;
                };
                if (payload.analyzed === 0) {
                  return ["אין ניתוח תגובות עדיין", "קיטוב"];
                }
                const countKey =
                  name === "low" ? "lowCount" : name === "mid" ? "midCount" : "highCount";
                const label =
                  name === "low" ? "קיטוב נמוך" : name === "mid" ? "קיטוב בינוני" : "קיטוב גבוה";
                const count = payload[countKey];
                return [`${value}% (${count} מתוך ${payload.analyzed} שנותחו)`, label];
              }}
            />
            <Legend
              formatter={(value) =>
                value === "low" ? "קיטוב נמוך" : value === "mid" ? "קיטוב בינוני" : "קיטוב גבוה"
              }
              wrapperStyle={{ color: "var(--text-secondary)" }}
            />
            <Bar dataKey="low" stackId="polarity" fill="#2DBE7F" radius={[0, 0, 0, 0]} />
            <Bar dataKey="mid" stackId="polarity" fill="#A8B0BB" />
            <Bar dataKey="high" stackId="polarity" fill="#EF5350" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
        לכל מקור, אחוז הכתבות שתגובותיהן סווגו לרמת קיטוב נמוכה (מתחת ל-5%), בינונית (5%–15%)
        או גבוהה (מעל 15%) לפי ממוצע התגובות. זה לא אותו מדד כמו כתבות בולטות למטה, שמדרגות
        לפי שיא התגובות. הפילוח הוא רק מתוך כתבות שכבר יש להן ניתוח תגובות. מקור בלי ניתוח
        מופיע כשורה ריקה.
        {smallSamples.length > 0 && (
          <>
            {" "}
            הרוחב של כל עמודה זהה בלי קשר לכמות הכתבות שמאחוריה, ולכן מספר הכתבות מופיע
            ליד שם המקור. {smallSamples.map((r) => sourceLabel(r.name)).join(", ")} נמדדו על
            פחות מ־{SMALL_SAMPLE_MIN} כתבות — הפילוח שלהם יכול להתהפך מכמה כתבות בודדות.
          </>
        )}
      </p>
    </div>
  );
}
