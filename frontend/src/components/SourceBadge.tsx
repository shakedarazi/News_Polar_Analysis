import { sourceLabel } from "@/lib/format";
import { SourceLogo } from "./SourceLogo";

const COLORS: Record<string, string> = {
  ynet: "bg-red-100 text-red-800",
  haaretz: "bg-slate-100 text-slate-800",
  mako: "bg-green-100 text-green-800",
  news12: "bg-blue-100 text-blue-800",
  reshet13: "bg-purple-100 text-purple-800",
  channel14: "bg-orange-100 text-orange-800",
};

export function SourceBadge({ source }: { source: string }) {
  const color = COLORS[source] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-semibold ${color}`}>
      <SourceLogo source={source} size={16} />
      {sourceLabel(source)}
    </span>
  );
}
