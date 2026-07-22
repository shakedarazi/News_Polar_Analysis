import { sourceLabel } from "@/lib/format";
import { SourceLogo } from "./SourceLogo";

const COLORS: Record<string, string> = {
  ynet: "bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-300",
  haaretz: "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200",
  mako: "bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300",
  news12: "bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-300",
  reshet13: "bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-300",
  channel14: "bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-300",
};

export function SourceBadge({ source }: { source: string }) {
  const color = COLORS[source] ?? "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-semibold ${color}`}>
      <SourceLogo source={source} size={16} />
      {sourceLabel(source)}
    </span>
  );
}
