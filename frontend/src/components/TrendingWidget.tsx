"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ChevronDown,
  ChevronUp,
  Flame,
  Minus,
  RefreshCw,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
import { getTrendingClient } from "@/lib/api";
import { LIVE_POLL_INTERVAL_MS } from "@/lib/liveConfig";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import type { TrendingTopic } from "@/lib/types";

function Sparkline({ points }: { points: { date: string; count: number }[] }) {
  if (points.length < 2) return null;
  const values = points.map((p) => p.count);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const w = 56;
  const h = 18;
  const step = w / (points.length - 1);
  const coords = values
    .map((v, i) => `${(i * step).toFixed(1)},${(h - ((v - min) / range) * h).toFixed(1)}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} className="shrink-0" aria-hidden>
      <polyline
        points={coords}
        fill="none"
        stroke="var(--purple)"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function TrendBadge({ topic }: { topic: TrendingTopic }) {
  if (topic.direction === "new") {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs font-semibold text-[var(--purple)]">
        <Sparkles className="h-3 w-3" aria-hidden />
        חדש
      </span>
    );
  }
  const pct = topic.growth_pct ?? 0;
  if (topic.direction === "up") {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs font-semibold text-[var(--positive)]">
        <TrendingUp className="h-3 w-3" aria-hidden />+{pct.toFixed(0)}%
      </span>
    );
  }
  if (topic.direction === "down") {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs font-semibold text-[var(--negative)]">
        <TrendingDown className="h-3 w-3" aria-hidden />
        {pct.toFixed(0)}%
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-0.5 text-xs font-medium text-slate-400 dark:text-slate-500">
      <Minus className="h-3 w-3" aria-hidden />
      {pct.toFixed(0)}%
    </span>
  );
}

function TrendingList({ topics }: { topics: TrendingTopic[] }) {
  if (topics.length === 0) {
    return <EmptyState message="אין עדיין מספיק נתונים כדי להציג נושאים חמים." />;
  }
  return (
    <ul className="space-y-1">
      {topics.map((t) => (
        <li key={t.topic}>
          <Link
            href={`/?category=${encodeURIComponent(t.topic)}#topics`}
            className="flex items-center gap-2.5 rounded-xl px-2 py-2 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[11px] font-bold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
              {t.rank}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                {t.topic}
              </span>
              <span className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
                {t.current_count} כתבות · {t.unique_sources} מקורות
              </span>
            </span>
            <Sparkline points={t.sparkline} />
            <TrendBadge topic={t} />
          </Link>
        </li>
      ))}
    </ul>
  );
}

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; topics: TrendingTopic[] };

function useTrending() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = useCallback(async (isRefresh: boolean) => {
    if (isRefresh) setRefreshing(true);
    else setState({ kind: "loading" });
    try {
      const topics = await getTrendingClient();
      setState({ kind: "ready", topics });
      setLastUpdated(new Date());
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "שגיאה לא ידועה",
      });
    } finally {
      if (isRefresh) setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // Live updates: no WebSocket/SSE infra exists in this system, so
    // trending topics refresh on a shared poll interval (see liveConfig.ts).
    const id = window.setInterval(() => load(true), LIVE_POLL_INTERVAL_MS);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { state, refreshing, lastUpdated, refresh: () => load(true) };
}

function WidgetHeader({
  refreshing,
  onRefresh,
  collapsed,
  onToggleCollapsed,
}: {
  refreshing: boolean;
  onRefresh: () => void;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
        <Flame className="h-4 w-4 text-[var(--negative)]" aria-hidden />
        חם עכשיו
      </span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          aria-label="רענן נושאים חמים"
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-300"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden />
        </button>
        {onToggleCollapsed && (
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? "הרחב" : "כווץ"}
            aria-expanded={!collapsed}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-300"
          >
            {collapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          </button>
        )}
      </div>
    </div>
  );
}

function WidgetBody({ state }: { state: State }) {
  if (state.kind === "loading") {
    return (
      <div className="space-y-2 py-2" role="status" aria-label="טוען נושאים חמים">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-9 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
        ))}
      </div>
    );
  }
  if (state.kind === "error") {
    return <ErrorState message="לא ניתן לטעון נושאים חמים" detail={state.message} />;
  }
  return <TrendingList topics={state.topics} />;
}

export function TrendingWidget() {
  const { state, refreshing, lastUpdated, refresh } = useTrending();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const updatedLabel = lastUpdated
    ? `עודכן ${lastUpdated.toLocaleTimeString("he-IL", { hour: "2-digit", minute: "2-digit" })}`
    : null;

  return (
    <>
      {/* Desktop/tablet: sticky collapsible sidebar on the left (RTL: last flex child) */}
      <aside className="hidden w-full shrink-0 md:block md:w-64 md:sticky md:top-20 md:self-start">
        <div className="card p-4">
          <WidgetHeader
            refreshing={refreshing}
            onRefresh={refresh}
            collapsed={collapsed}
            onToggleCollapsed={() => setCollapsed((v) => !v)}
          />
          {!collapsed && (
            <div className="mt-3">
              <WidgetBody state={state} />
              {updatedLabel && (
                <p className="mt-2 text-center text-[11px] text-slate-400 dark:text-slate-500">
                  {updatedLabel}
                </p>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* Mobile: floating button + bottom sheet */}
      <div className="md:hidden">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          aria-label="חם עכשיו"
          className="btn-primary fixed bottom-5 left-5 z-30 flex h-12 w-12 items-center justify-center rounded-full shadow-lg"
        >
          <Flame className="h-5 w-5" aria-hidden />
        </button>

        {mobileOpen && (
          <div
            className="fixed inset-0 z-40 flex items-end bg-slate-900/50"
            role="dialog"
            aria-modal="true"
            aria-label="חם עכשיו"
            onClick={() => setMobileOpen(false)}
          >
            <div
              className="max-h-[75vh] w-full overflow-y-auto rounded-t-2xl bg-[var(--card)] p-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
                  <Flame className="h-4 w-4 text-[var(--negative)]" aria-hidden />
                  חם עכשיו
                </span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={refresh}
                    disabled={refreshing}
                    aria-label="רענן נושאים חמים"
                    className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-300"
                  >
                    <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden />
                  </button>
                  <button
                    type="button"
                    onClick={() => setMobileOpen(false)}
                    aria-label="סגור"
                    className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                  >
                    <X className="h-4 w-4" aria-hidden />
                  </button>
                </div>
              </div>
              <div className="mt-2">
                <WidgetBody state={state} />
                {updatedLabel && (
                  <p className="mt-2 text-center text-[11px] text-slate-400 dark:text-slate-500">
                    {updatedLabel}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
