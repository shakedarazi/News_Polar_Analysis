"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { LIVE_POLL_INTERVAL_MS } from "@/lib/liveConfig";

function elapsedLabel(lastUpdated: number, now: number): string {
  const seconds = Math.max(0, Math.round((now - lastUpdated) / 1000));
  if (seconds < 5) return "עודכן זה עתה";
  if (seconds < 60) return `עודכן לאחרונה לפני ${seconds} שניות`;
  const minutes = Math.round(seconds / 60);
  return `עודכן לאחרונה לפני ${minutes} דקות`;
}

/**
 * Drives "live" updates for the dashboard's server-rendered sections (stats,
 * charts, topics, leading articles in app/page.tsx) via Next's router.refresh()
 * — which re-runs the page's server-side data fetch in place, no full page
 * reload and no client state loss. Polls on LIVE_POLL_INTERVAL_MS and exposes
 * a manual refresh button + "LIVE" indicator + elapsed-time label.
 */
export function LiveIndicator() {
  const router = useRouter();
  const [lastUpdated, setLastUpdated] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(() => {
    setRefreshing(true);
    router.refresh();
    setLastUpdated(Date.now());
    // router.refresh() has no completion callback; a short fixed spin gives
    // clear visual feedback without depending on exact server timing.
    window.setTimeout(() => setRefreshing(false), 600);
  }, [router]);

  useEffect(() => {
    const pollId = window.setInterval(refresh, LIVE_POLL_INTERVAL_MS);
    return () => window.clearInterval(pollId);
  }, [refresh]);

  useEffect(() => {
    const tickId = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(tickId);
  }, []);

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
      <span className="relative flex h-2 w-2" aria-hidden>
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--positive)] opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--positive)]" />
      </span>
      <span className="font-bold tracking-wide text-[var(--positive)]">LIVE</span>
      <span>{elapsedLabel(lastUpdated, now)}</span>
      <button
        type="button"
        onClick={refresh}
        aria-label="רענן נתונים"
        className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-300"
      >
        <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} aria-hidden />
      </button>
    </div>
  );
}
