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
import { sourceLabel } from "@/lib/format";
import { EmptyState } from "./EmptyState";
import { LOGO_COLOR, LOGO_TEXT } from "./SourceLogo";

const ISSUE_COLOR = "#5B8DEF";
const AFFECTIVE_COLOR = "#B06AB3";

type AxisTickProps = {
  x?: string | number;
  y?: string | number;
  payload?: { value: string };
};

function SourceAxisTick(props: AxisTickProps) {
  const x = Number(props.x ?? 0);
  const y = Number(props.y ?? 0);
  const source = props.payload?.value ?? "";
  const color = LOGO_COLOR[source] ?? "#64748B";
  const logoText = LOGO_TEXT[source] ?? source.slice(0, 2).toUpperCase();
  return (
    <g transform={`translate(${x},${y})`}>
      <circle cx={-118} cy={0} r={10} fill={color} />
      <text x={-118} y={0} dy={3} textAnchor="middle" fontSize={9} fontWeight={700} fill="#fff">
        {logoText}
      </text>
      <text x={-8} y={0} dy={4} textAnchor="end" fontSize={12} fill="var(--text-secondary)">
        {sourceLabel(source)}
      </text>
    </g>
  );
}

/**
 * The research polarization lexicon's two axes, per source.
 *
 * Deliberately grouped bars, not stacked: the two axes count overlapping word
 * lists and a comment can be on both, so a stack would draw a total that means
 * nothing. Deliberately not the low/mid/high colour scale either - those
 * thresholds are cut on `audience_mean`, which counts a different word list
 * (docs/adr/0004).
 */
export function SourceAxesChart({ data }: { data: SourcePolarityBreakdown[] }) {
  // typeof rather than a null check: an API old enough to predate these columns
  // omits the keys entirely, and `undefined` passes `!== null` and then renders
  // NaN. Vercel and Render deploy independently, so that pairing is a state the
  // running site actually reaches.
  const rows = data.flatMap((d) => {
    if (
      typeof d.avg_issue !== "number" ||
      typeof d.avg_affective !== "number" ||
      !d.polarization_count
    ) {
      return [];
    }
    return [
      {
        name: d.source,
        issue: Number((d.avg_issue * 100).toFixed(2)),
        affective: Number((d.avg_affective * 100).toFixed(2)),
        measured: d.polarization_count,
        analyzed: d.analyzed_count,
      },
    ];
  });

  if (rows.length === 0) {
    return <EmptyState message="הקריאה השנייה עוד לא חושבה עבור המקורות בתקופה שנבחרה." />;
  }

  const partial = rows.filter((r) => r.measured < r.analyzed);
  const height = Math.max(180, rows.length * 72);

  return (
    <div>
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            barSize={14}
            barCategoryGap="30%"
            margin={{ top: 8, right: 16, left: 8, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis
              type="number"
              tickFormatter={(value) => `${value}%`}
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
              cursor={{ fill: "var(--border)", fillOpacity: 0.25 }}
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: "var(--text-primary)",
              }}
              labelStyle={{ color: "var(--text-primary)" }}
              labelFormatter={(value) => sourceLabel(String(value))}
              formatter={(value, name, item) => {
                const payload = item.payload as { measured: number; analyzed: number };
                const label = name === "issue" ? "שפת נושא" : "שפת עוינות";
                return [`${value}% (מתוך ${payload.measured} כתבות שנמדדו)`, label];
              }}
            />
            <Legend
              formatter={(value) => (value === "issue" ? "שפת נושא" : "שפת עוינות")}
              wrapperStyle={{ color: "var(--text-secondary)" }}
            />
            <Bar dataKey="issue" fill={ISSUE_COLOR} radius={[0, 3, 3, 0]} />
            <Bar dataKey="affective" fill={AFFECTIVE_COLOR} radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
        קריאה שנייה של אותן תגובות, לפי מילון המחקר (סימחון). ״שפת נושא״ סופרת מילים
        ששייכות למחלוקת עצמה, ״שפת עוינות״ סופרת מילים שמכוונות אל הצד השני. תגובה
        יכולה להיספר בשני הצירים, ולכן הם מוצגים זה לצד זה ולא מחוברים לסכום. אלה לא
        אותם מספרים כמו הפילוח למעלה — שם נספרת רשימת מילים אחרת, ולכן גם הסף שמפריד
        בין ״נמוך״ ל״גבוה״ שם לא חל כאן.
        {partial.length > 0 && (
          <>
            {" "}
            עבור {partial.map((r) => sourceLabel(r.name)).join(", ")} הקריאה השנייה עדיין
            לא חושבה לכל הכתבות שנותחו, כך שהממוצע מבוסס על חלק מהן.
          </>
        )}
      </p>
    </div>
  );
}
