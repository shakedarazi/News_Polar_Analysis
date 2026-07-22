"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Bell,
  Flame,
  Radio,
  Scale,
  TrendingUp,
  X,
} from "lucide-react";
import {
  getAlertsClient,
  markAllAlertsReadClient,
  markAlertReadClient,
} from "@/lib/api";
import { LIVE_POLL_INTERVAL_MS } from "@/lib/liveConfig";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import type { AlertItem, AlertType } from "@/lib/types";
import { formatDate } from "@/lib/format";

const TYPE_ICON: Record<AlertType, typeof TrendingUp> = {
  topic_spike: TrendingUp,
  source_activity: Radio,
  sentiment_shift: AlertTriangle,
  event_polarization: Scale,
  new_event: Flame,
};

const SEVERITY_CLASS: Record<AlertItem["severity"], string> = {
  high: "text-[var(--negative)] bg-[var(--negative)]/10",
  medium: "text-[var(--warning)] bg-[var(--warning)]/10",
  low: "text-slate-500 bg-slate-100 dark:text-slate-400 dark:bg-slate-800",
};

const SEVERITY_LABEL: Record<AlertItem["severity"], string> = {
  high: "חומרה גבוהה",
  medium: "חומרה בינונית",
  low: "חומרה נמוכה",
};

const TYPE_LABEL: Record<AlertType, string> = {
  topic_spike: "עלייה בנושא",
  source_activity: "פעילות מקור",
  sentiment_shift: "שינוי בקיטוב",
  event_polarization: "מחלוקת פוליטית",
  new_event: "אירוע מתפתח",
};

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; items: AlertItem[]; unreadCount: number };

function useAlerts() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [typeFilter, setTypeFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await getAlertsClient({
        alert_type: typeFilter || undefined,
        severity: severityFilter || undefined,
      });
      setState({ kind: "ready", items: data.items, unreadCount: data.unread_count });
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "שגיאה לא ידועה",
      });
    }
  }, [typeFilter, severityFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    // Live updates: no WebSocket/SSE infra exists in this system, so new
    // alerts (and their unread count) are picked up on a shared poll
    // interval (see liveConfig.ts) rather than only on mount/manual action.
    const id = window.setInterval(load, LIVE_POLL_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [load]);

  const markRead = useCallback(
    async (alertId: string) => {
      try {
        await markAlertReadClient(alertId);
        await load();
      } catch {
        /* keep showing current state — non-critical action */
      }
    },
    [load],
  );

  const markAllRead = useCallback(async () => {
    try {
      await markAllAlertsReadClient();
      await load();
    } catch {
      /* keep showing current state — non-critical action */
    }
  }, [load]);

  return { state, typeFilter, setTypeFilter, severityFilter, setSeverityFilter, markRead, markAllRead };
}

function AlertRow({ alert, onMarkRead }: { alert: AlertItem; onMarkRead: (id: string) => void }) {
  const Icon = TYPE_ICON[alert.alert_type];
  return (
    <li
      className={`rounded-xl p-3 ${alert.is_read ? "" : "bg-[var(--accent-soft)]"}`}
    >
      <div className="flex items-start gap-2.5">
        <span
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${SEVERITY_CLASS[alert.severity]}`}
          aria-hidden
        >
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <p className="text-sm font-bold text-slate-900 dark:text-slate-100">{alert.title}</p>
            {!alert.is_read && (
              <span className="rounded-full bg-[var(--purple)] px-1.5 py-0.5 text-[10px] font-bold text-white">
                חדש
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            {alert.message}
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400 dark:text-slate-500">
            <span>{TYPE_LABEL[alert.alert_type]}</span>
            <span aria-hidden>·</span>
            <span>{SEVERITY_LABEL[alert.severity]}</span>
            <span aria-hidden>·</span>
            <span>{formatDate(alert.created_at)}</span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
            {alert.related_event_id ? (
              <Link
                href={`/events/${alert.related_event_id}`}
                className="font-medium text-[var(--indigo)] hover:underline"
              >
                הצג אירוע
              </Link>
            ) : (
              alert.link_path && (
                <Link href={alert.link_path} className="font-medium text-[var(--indigo)] hover:underline">
                  צפה בכתבות
                </Link>
              )
            )}
            {!alert.is_read && (
              <button
                type="button"
                onClick={() => onMarkRead(alert.alert_id)}
                className="font-medium text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
              >
                סמן כנקרא
              </button>
            )}
          </div>
        </div>
      </div>
    </li>
  );
}

function AlertsBody({
  state,
  onMarkRead,
}: {
  state: State;
  onMarkRead: (id: string) => void;
}) {
  if (state.kind === "loading") {
    return (
      <div className="space-y-2 py-2" role="status" aria-label="טוען התראות">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
        ))}
      </div>
    );
  }
  if (state.kind === "error") {
    return <ErrorState message="לא ניתן לטעון התראות" detail={state.message} />;
  }
  if (state.items.length === 0) {
    return <EmptyState message="אין התראות חדשות כרגע." />;
  }
  return (
    <ul className="max-h-[60vh] space-y-1 overflow-y-auto">
      {state.items.map((alert) => (
        <AlertRow key={alert.alert_id} alert={alert} onMarkRead={onMarkRead} />
      ))}
    </ul>
  );
}

function AlertFilters({
  typeFilter,
  setTypeFilter,
  severityFilter,
  setSeverityFilter,
}: {
  typeFilter: string;
  setTypeFilter: (v: string) => void;
  severityFilter: string;
  setSeverityFilter: (v: string) => void;
}) {
  return (
    <div className="mb-2 flex flex-wrap gap-2 text-xs">
      <select
        value={typeFilter}
        onChange={(e) => setTypeFilter(e.target.value)}
        className="rounded-lg border border-slate-200 bg-white px-2 py-1 dark:border-slate-700 dark:bg-slate-900"
        aria-label="סינון לפי סוג התראה"
      >
        <option value="">כל הסוגים</option>
        {Object.entries(TYPE_LABEL).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <select
        value={severityFilter}
        onChange={(e) => setSeverityFilter(e.target.value)}
        className="rounded-lg border border-slate-200 bg-white px-2 py-1 dark:border-slate-700 dark:bg-slate-900"
        aria-label="סינון לפי חומרה"
      >
        <option value="">כל רמות החומרה</option>
        {Object.entries(SEVERITY_LABEL).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function NotificationBell() {
  const { state, typeFilter, setTypeFilter, severityFilter, setSeverityFilter, markRead, markAllRead } =
    useAlerts();
  const [open, setOpen] = useState(false);

  const unreadCount = state.kind === "ready" ? state.unreadCount : 0;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="התראות"
        aria-expanded={open}
        className="relative rounded-lg p-2 text-white/80 hover:bg-white/10 hover:text-white"
      >
        <Bell className="h-5 w-5" aria-hidden />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -left-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--negative)] px-1 text-[10px] font-bold text-white">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          {/* Desktop dropdown */}
          <div className="absolute left-0 top-full z-40 mt-2 hidden w-96 md:block">
            <div className="card p-4 shadow-xl">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-bold text-slate-900 dark:text-slate-100">התראות</span>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={markAllRead}
                    className="text-xs font-medium text-[var(--indigo)] hover:underline"
                  >
                    סמן הכול כנקרא
                  </button>
                )}
              </div>
              <AlertFilters
                typeFilter={typeFilter}
                setTypeFilter={setTypeFilter}
                severityFilter={severityFilter}
                setSeverityFilter={setSeverityFilter}
              />
              <AlertsBody state={state} onMarkRead={markRead} />
            </div>
          </div>

          {/* Mobile full-screen sheet */}
          <div
            className="fixed inset-0 z-40 bg-slate-900/50 md:hidden"
            role="dialog"
            aria-modal="true"
            aria-label="התראות"
            onClick={() => setOpen(false)}
          >
            <div
              className="absolute inset-x-0 bottom-0 max-h-[85vh] overflow-y-auto rounded-t-2xl bg-[var(--card)] p-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-bold text-slate-900 dark:text-slate-100">התראות</span>
                <div className="flex items-center gap-3">
                  {unreadCount > 0 && (
                    <button
                      type="button"
                      onClick={markAllRead}
                      className="text-xs font-medium text-[var(--indigo)] hover:underline"
                    >
                      סמן הכול כנקרא
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setOpen(false)}
                    aria-label="סגור"
                    className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                  >
                    <X className="h-4 w-4" aria-hidden />
                  </button>
                </div>
              </div>
              <AlertFilters
                typeFilter={typeFilter}
                setTypeFilter={setTypeFilter}
                severityFilter={severityFilter}
                setSeverityFilter={setSeverityFilter}
              />
              <AlertsBody state={state} onMarkRead={markRead} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
