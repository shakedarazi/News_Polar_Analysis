import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { getEventDeviation, getEventDetail } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/format";
import { EventTimeline } from "@/components/EventTimeline";
import { EventVersionComparison } from "@/components/EventVersionComparison";

export default async function EventPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let event;
  try {
    event = await getEventDetail(id);
  } catch {
    notFound();
  }

  // Never fails the page: this endpoint is newer than the event detail one,
  // and Vercel can be a deploy ahead of Render.
  const deviation = await getEventDeviation(id).catch(() => null);

  const biasEntries = event.bias_distribution ? Object.entries(event.bias_distribution) : [];

  return (
    <div className="mx-auto max-w-4xl space-y-8 px-4 py-8 sm:px-6">
      <Link
        href="/events"
        className="inline-flex items-center gap-1 text-sm font-medium text-[var(--primary-light)] hover:underline"
      >
        <ArrowRight className="h-4 w-4" />
        חזרה לציר הזמן
      </Link>

      <header className="card p-6">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {event.primary_category && (
            <span className="rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300">
              {event.primary_category}
            </span>
          )}
          <span className="text-xs text-slate-400 dark:text-slate-500">
            {formatDate(event.first_seen_at)} — {formatDate(event.last_seen_at)}
          </span>
        </div>
        <h1 className="text-2xl font-bold leading-snug text-slate-900 dark:text-slate-100 sm:text-3xl">
          {event.title || "ללא כותרת"}
        </h1>

        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">כתבות באירוע</p>
            <p className="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
              {event.article_count}
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">מקורות מסקרים</p>
            <p className="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
              {event.source_count}
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">קיטוב ממוצע</p>
            <p className="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
              {formatPercent(event.avg_audience_mean)}
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">סנטימנט דומיננטי</p>
            <p className="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
              {event.dominant_sentiment ?? "אין נתונים"}
            </p>
          </div>
        </div>

        {biasEntries.length > 0 && (
          <div className="mt-4 border-t border-[var(--border)] pt-4">
            <p className="mb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
              התפלגות נטייה פוליטית בכתבות האירוע
            </p>
            <div className="flex flex-wrap gap-2">
              {biasEntries.map(([label, count]) => (
                <span
                  key={label}
                  className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                >
                  {label}: {count}
                </span>
              ))}
            </div>
          </div>
        )}
      </header>

      {deviation && event.source_count > 1 && (
        <section className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            איך כל מקור נבדל באירוע הזה
          </h2>
          <p className="mb-4 mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            פולריות התגובות בכל גרסה, מול חציון האירוע. כיוון שכל המקורות כאן מסקרים את
            אותו אירוע, ההבדל ביניהם אינו בחירת הסיפור אלא הסיקור עצמו.
          </p>
          <EventVersionComparison data={deviation} />
        </section>
      )}

      <section>
        <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
          ציר זמן הסיקור
        </h2>
        <EventTimeline items={event.timeline} />
      </section>
    </div>
  );
}
