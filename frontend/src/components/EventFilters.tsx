"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { RotateCcw } from "lucide-react";
import type { CategoryStat, SourceStat } from "@/lib/types";
import { sourceLabel } from "@/lib/format";

export function EventFilters({
  sources,
  categories,
}: {
  sources: SourceStat[];
  categories: CategoryStat[];
}) {
  const router = useRouter();
  const params = useSearchParams();

  const update = useCallback(
    (key: string, value: string) => {
      const next = new URLSearchParams(params.toString());
      if (value) next.set(key, value);
      else next.delete(key);
      next.delete("limit");
      router.push(`/events?${next.toString()}`);
    },
    [params, router],
  );

  const hasFilters = Boolean(
    params.get("source") || params.get("category") || params.get("start_date") || params.get("end_date"),
  );

  return (
    <div className="card flex flex-wrap items-end gap-4 p-4">
      <label className="flex min-w-[130px] flex-col gap-1 text-sm">
        <span className="font-medium text-slate-600 dark:text-slate-300">מקור</span>
        <select
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
          value={params.get("source") ?? ""}
          onChange={(e) => update("source", e.target.value)}
        >
          <option value="">הכל</option>
          {sources.map((s) => (
            <option key={s.source} value={s.source}>
              {sourceLabel(s.source)} ({s.article_count})
            </option>
          ))}
        </select>
      </label>
      <label className="flex min-w-[130px] flex-col gap-1 text-sm">
        <span className="font-medium text-slate-600 dark:text-slate-300">קטגוריה</span>
        <select
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
          value={params.get("category") ?? ""}
          onChange={(e) => update("category", e.target.value)}
        >
          <option value="">הכל</option>
          {categories.map((c) => (
            <option key={c.category} value={c.category}>
              {c.category} ({c.article_count})
            </option>
          ))}
        </select>
      </label>
      <label className="flex min-w-[130px] flex-col gap-1 text-sm">
        <span className="font-medium text-slate-600 dark:text-slate-300">מתאריך</span>
        <input
          type="date"
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
          defaultValue={params.get("start_date") ?? ""}
          onChange={(e) => update("start_date", e.target.value)}
          aria-label="מתאריך"
        />
      </label>
      <label className="flex min-w-[130px] flex-col gap-1 text-sm">
        <span className="font-medium text-slate-600 dark:text-slate-300">עד תאריך</span>
        <input
          type="date"
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
          defaultValue={params.get("end_date") ?? ""}
          onChange={(e) => update("end_date", e.target.value)}
          aria-label="עד תאריך"
        />
      </label>
      {hasFilters && (
        <button
          type="button"
          onClick={() => router.push("/events")}
          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-[var(--indigo)] hover:bg-[var(--accent-soft)]"
        >
          <RotateCcw className="h-4 w-4" aria-hidden />
          אפס פילטרים
        </button>
      )}
    </div>
  );
}
