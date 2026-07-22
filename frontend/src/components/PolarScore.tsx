import { polarLevel, polarLevelLabel } from "@/lib/format";

export function PolarScore({
  value,
  label,
  large,
}: {
  value: number | null | undefined;
  label?: string;
  large?: boolean;
}) {
  const level = polarLevel(value);
  const className =
    level === "high"
      ? "score-high"
      : level === "mid"
        ? "score-mid"
        : level === "low"
          ? "score-low"
          : "score-none";

  const display =
    value === null || value === undefined ? "—" : (value * 100).toFixed(1) + "%";

  return (
    <div className="flex flex-col gap-1">
      {label && <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</span>}
      <span
        className={`inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-1 font-semibold ${className} ${large ? "text-base px-3 py-1.5" : "text-sm"}`}
        aria-label={`${display} — ${polarLevelLabel(value)}`}
      >
        {display}
        {large && <span className="text-xs font-normal opacity-80">{polarLevelLabel(value)}</span>}
      </span>
    </div>
  );
}
