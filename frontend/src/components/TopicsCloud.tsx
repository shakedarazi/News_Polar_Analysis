import Link from "next/link";
import type { CategoryStat } from "@/lib/types";
import { EmptyState } from "./EmptyState";

export function TopicsCloud({
  categories,
  currentParams,
}: {
  categories: CategoryStat[];
  currentParams: Record<string, string | undefined>;
}) {
  if (categories.length === 0) {
    return <EmptyState message="לא קיימות עדיין כתבות מסווגות לנושאים." />;
  }

  const max = Math.max(...categories.map((c) => c.article_count));
  const min = Math.min(...categories.map((c) => c.article_count));
  const scale = (count: number) => {
    if (max === min) return 1.25;
    const ratio = (count - min) / (max - min);
    return 0.9 + ratio * 1.1; // rem range ~0.9–2.0
  };

  const buildHref = (category: string) => {
    const qs = new URLSearchParams();
    for (const [key, value] of Object.entries(currentParams)) {
      if (value && key !== "category") qs.set(key, value);
    }
    const isActive = currentParams.category === category;
    if (!isActive) qs.set("category", category);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return `/${suffix}#topics`;
  };

  return (
    <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-3 p-4">
      {categories.map((c) => {
        const active = currentParams.category === c.category;
        return (
          <Link
            key={c.category}
            href={buildHref(c.category)}
            style={{ fontSize: `${scale(c.article_count)}rem` }}
            className={`font-bold transition hover:text-[var(--purple)] ${
              active ? "text-[var(--purple)] underline" : "text-[var(--navy-2)]"
            }`}
            title={`${c.article_count} כתבות`}
          >
            {c.category}
          </Link>
        );
      })}
    </div>
  );
}
