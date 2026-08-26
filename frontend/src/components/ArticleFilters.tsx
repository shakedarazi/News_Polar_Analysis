"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useState } from "react";
import { RotateCcw, Search, X } from "lucide-react";
import type { CategoryStat, SourceStat } from "@/lib/types";
import { sourceLabel } from "@/lib/format";

export function ArticleFilters({
  sources,
  categories,
}: {
  sources: SourceStat[];
  categories: CategoryStat[];
}) {
  const router = useRouter();
  const params = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");

  const update = useCallback(
    (key: string, value: string) => {
      const next = new URLSearchParams(params.toString());
      if (value) next.set(key, value);
      else next.delete(key);
      next.delete("offset");
      router.push(`/articles?${next.toString()}`);
    },
    [params, router],
  );

  const hasFilters = Boolean(
    params.get("source") ||
      params.get("category") ||
      params.get("min_polar") ||
      params.get("start_date") ||
      params.get("end_date") ||
      params.get("q"),
  );

  return (
    <div className="card flex flex-wrap items-end gap-4 p-4">
      <label className="flex min-w-[180px] flex-1 flex-col gap-1 text-sm">
        <span className="font-medium text-slate-600 dark:text-slate-300">חיפוש חופשי</span>
        <div className="relative">
          <Search
            className="pointer-events-none absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2 text-slate-400"
            aria-hidden
          />
          <input
            type="search"
            placeholder="לדוגמה: איראן, נתניהו, עסקת חטופים..."
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pr-9 pl-8 dark:border-slate-700 dark:bg-slate-900"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") update("q", q);
            }}
            onBlur={() => update("q", q)}
            aria-label="חיפוש חופשי בכותרת ובתוכן הכתבה"
          />
          {q && (
            <button
              type="button"
              onClick={() => {
                setQ("");
                update("q", "");
              }}
              aria-label="נקה חיפוש"
              className="absolute top-1/2 left-2 -translate-y-1/2 rounded p-0.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
            >
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          )}
        </div>
      </label>
      <label className="flex min-w-[130px] flex-col gap-1 text-sm">
        <span className="font-medium text-slate-600 dark:text-slate-300">מקור</span>
        <select
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2"
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
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2"
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
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2"
          defaultValue={params.get("start_date") ?? ""}
          onChange={(e) => update("start_date", e.target.value)}
          aria-label="מתאריך"
        />
      </label>
      <label className="flex min-w-[130px] flex-col gap-1 text-sm">
        <span className="font-medium text-slate-600 dark:text-slate-300">עד תאריך</span>
        <input
          type="date"
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2"
          defaultValue={params.get("end_date") ?? ""}
          onChange={(e) => update("end_date", e.target.value)}
          aria-label="עד תאריך"
        />
      </label>
      <label className="flex min-w-[130px] flex-col gap-1 text-sm">
        <span className="font-medium text-slate-600 dark:text-slate-300">קיטוב ממוצע מינימלי</span>
        <input
          type="number"
          min={0}
          max={1}
          step={0.01}
          placeholder="0.00"
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2"
          defaultValue={params.get("min_polar") ?? ""}
          onBlur={(e) => update("min_polar", e.target.value)}
        />
      </label>
      {hasFilters && (
        <button
          type="button"
          onClick={() => {
            setQ("");
            router.push("/articles");
          }}
          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-[var(--indigo)] hover:bg-[var(--accent-soft)]"
        >
          <RotateCcw className="h-4 w-4" aria-hidden />
          אפס פילטרים
        </button>
      )}
    </div>
  );
}
