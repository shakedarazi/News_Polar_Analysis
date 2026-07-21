"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Filter, RotateCcw } from "lucide-react";
import type { CategoryStat, DateRange, SourceStat } from "@/lib/types";
import { sourceLabel } from "@/lib/format";

function toDateInputValue(value: string | null | undefined): string {
  if (!value) return "";
  return value.slice(0, 10);
}

export function FilterSidebar({
  sources,
  categories,
  dateRange,
}: {
  sources: SourceStat[];
  categories: CategoryStat[];
  dateRange: DateRange;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const [open, setOpen] = useState(false);

  const [source, setSource] = useState(params.get("source") ?? "");
  const [category, setCategory] = useState(params.get("category") ?? "");
  const [startDate, setStartDate] = useState(params.get("start_date") ?? "");
  const [endDate, setEndDate] = useState(params.get("end_date") ?? "");

  const minDate = toDateInputValue(dateRange.min);
  const maxDate = toDateInputValue(dateRange.max);

  const applyFilters = () => {
    const next = new URLSearchParams();
    if (source) next.set("source", source);
    if (category) next.set("category", category);
    if (startDate) next.set("start_date", startDate);
    if (endDate) next.set("end_date", endDate);
    router.push(`/${next.toString() ? `?${next.toString()}#trend` : ""}`);
  };

  const resetFilters = () => {
    setSource("");
    setCategory("");
    setStartDate("");
    setEndDate("");
    router.push("/");
  };

  const hasActiveFilters = Boolean(source || category || startDate || endDate);

  const body = (
    <div className="space-y-5">
      <fieldset className="space-y-2">
        <legend className="text-xs font-semibold text-white/60">טווח תאריכים</legend>
        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-1 text-xs text-white/70">
            <span>מתאריך</span>
            <input
              type="date"
              value={startDate}
              min={minDate}
              max={maxDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="rounded-lg border border-white/15 bg-white/5 px-2 py-1.5 text-sm text-white [color-scheme:dark]"
              aria-label="תאריך התחלה"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-white/70">
            <span>עד תאריך</span>
            <input
              type="date"
              value={endDate}
              min={minDate}
              max={maxDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="rounded-lg border border-white/15 bg-white/5 px-2 py-1.5 text-sm text-white [color-scheme:dark]"
              aria-label="תאריך סיום"
            />
          </label>
        </div>
      </fieldset>

      <label className="flex flex-col gap-1.5 text-xs font-semibold text-white/60">
        מקורות חדשות
        <select
          value={source}
          onChange={(e) => setSource(e.target.value)}
          className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm font-normal text-white"
        >
          <option value="" className="text-black">
            הכל
          </option>
          {sources.map((s) => (
            <option key={s.source} value={s.source} className="text-black">
              {sourceLabel(s.source)} ({s.article_count})
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1.5 text-xs font-semibold text-white/60">
        קטגוריות נושא
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm font-normal text-white"
        >
          <option value="" className="text-black">
            הכל
          </option>
          {categories.map((c) => (
            <option key={c.category} value={c.category} className="text-black">
              {c.category} ({c.article_count})
            </option>
          ))}
        </select>
      </label>

      <div className="flex flex-col gap-2 pt-2">
        <button
          type="button"
          onClick={applyFilters}
          className="btn-primary flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold"
        >
          <Filter className="h-4 w-4" aria-hidden />
          החל סינון
        </button>
        <button
          type="button"
          onClick={resetFilters}
          className="btn-outline flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold"
        >
          <RotateCcw className="h-4 w-4" aria-hidden />
          אפס פילטרים
        </button>
      </div>
    </div>
  );

  return (
    <aside className="lg:sticky lg:top-20 lg:self-start">
      <div className="rounded-2xl bg-[var(--navy)] p-5 text-white shadow-lg lg:w-72">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between gap-2 lg:pointer-events-none lg:mb-5"
          aria-expanded={open}
        >
          <span className="flex items-center gap-2 text-base font-bold">
            <Filter className="h-4 w-4 text-[var(--purple-light)]" aria-hidden />
            סינון נתונים
            {hasActiveFilters && (
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--purple-light)]" aria-hidden />
            )}
          </span>
          <span className="text-xs text-white/50 lg:hidden">{open ? "סגור" : "פתח"}</span>
        </button>
        <div className={`${open ? "mt-4 block" : "hidden"} lg:block`}>{body}</div>
      </div>
    </aside>
  );
}
