import type { LucideIcon } from "lucide-react";

const ACCENTS: Record<string, string> = {
  purple: "bg-[var(--purple)]/10 text-[var(--purple)]",
  indigo: "bg-[var(--indigo)]/10 text-[var(--indigo)]",
  positive: "bg-[var(--positive)]/10 text-[var(--positive)]",
  navy: "bg-[var(--navy)]/10 text-[var(--navy)]",
};

export function StatsCard({
  icon: Icon,
  label,
  value,
  hint,
  accent = "purple",
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  hint?: string;
  accent?: keyof typeof ACCENTS;
}) {
  return (
    <div className="card card-hover flex items-start justify-between gap-4 p-5">
      <div>
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900">{value}</p>
        {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
      </div>
      <div
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${ACCENTS[accent]}`}
        aria-hidden
      >
        <Icon className="h-5 w-5" />
      </div>
    </div>
  );
}
