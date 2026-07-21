const SOURCE_LABELS: Record<string, string> = {
  ynet: "ynet",
  haaretz: "הארץ",
  mako: "mako",
  news12: "חדשות 12",
  reshet13: "רשת 13",
  channel14: "ערוץ 14",
};

export function sourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}

export function formatScore(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("he-IL", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("he-IL").format(value);
}

export function polarLevel(value: number | null | undefined): "low" | "mid" | "high" | "none" {
  if (value === null || value === undefined) return "none";
  if (value >= 0.15) return "high";
  if (value >= 0.05) return "mid";
  return "low";
}

export function polarLevelLabel(value: number | null | undefined): string {
  const level = polarLevel(value);
  return { high: "קיטוב גבוה", mid: "קיטוב בינוני", low: "קיטוב נמוך", none: "אין נתונים" }[
    level
  ];
}

export function formatShortDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("he-IL", { day: "2-digit", month: "2-digit" }).format(
    new Date(value),
  );
}

const PLACEHOLDER_GRADIENTS: [string, string][] = [
  ["#4F46E5", "#8B7CFF"],
  ["#071A2D", "#4F46E5"],
  ["#102A43", "#6C63FF"],
  ["#6C63FF", "#2DBE7F"],
  ["#102A43", "#8B7CFF"],
];

export function placeholderGradient(seed: string): [string, string] {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return PLACEHOLDER_GRADIENTS[hash % PLACEHOLDER_GRADIENTS.length];
}

export const CATEGORY_LABELS = [
  "פוליטיקה",
  "ביטחון",
  "כלכלה",
  "חברה",
  "משפט",
  "זהות/דת",
  "בינלאומי",
] as const;
