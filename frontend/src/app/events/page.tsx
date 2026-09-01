import { Suspense } from "react";
import Link from "next/link";
import { getCategories, getEvents, getSources } from "@/lib/api";
import { EventFilters } from "@/components/EventFilters";
import { EventCard } from "@/components/EventCard";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { formatNumber } from "@/lib/format";

const PAGE_SIZE = 20;

async function EventsContent({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const sp = await searchParams;
  const limit = Number(sp.limit ?? PAGE_SIZE);

  let events, sources, categories;
  try {
    [events, sources, categories] = await Promise.all([
      getEvents({
        category: sp.category,
        source: sp.source,
        start_date: sp.start_date,
        end_date: sp.end_date,
        limit,
      }),
      getSources(),
      getCategories(),
    ]);
  } catch {
    return (
      <ErrorState
        message="לא ניתן לטעון אירועים"
        detail="ודא ש-PostgreSQL רץ ושהשרת פעיל: python pipeline/serve_api.py"
      />
    );
  }

  const buildMoreUrl = () => {
    const qs = new URLSearchParams();
    if (sp.source) qs.set("source", sp.source);
    if (sp.category) qs.set("category", sp.category);
    if (sp.start_date) qs.set("start_date", sp.start_date);
    if (sp.end_date) qs.set("end_date", sp.end_date);
    qs.set("limit", String(limit + PAGE_SIZE));
    return `/events?${qs}`;
  };

  return (
    <div className="space-y-6">
      <EventFilters sources={sources} categories={categories} />

      {events.length === 0 ? (
        <div className="card">
          <EmptyState message="לא זוהו אירועים התואמים לסינון שנבחר. אירוע מזוהה כששתי כתבות או יותר קרובות זו לזו במשמעות — לפי ייצוג סמנטי של הכותרת והפסקה הראשונה — באותו נושא ובטווח זמן קרוב." />
        </div>
      ) : (
        <>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            מציג {formatNumber(events.length)} אירועים
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            {events.map((event) => (
              <EventCard key={event.event_id} event={event} />
            ))}
          </div>
          {events.length >= limit && (
            <div className="flex justify-center">
              <Link href={buildMoreUrl()} className="card px-4 py-2 text-sm font-medium">
                טען עוד
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function EventsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">ציר זמן אירועים</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-300">
          כתבות דומות מכמה מקורות, מקובצות אוטומטית לפי נושא, סמיכות זמן פרסום ודמיון
          משמעות בין הכותרת והפסקה הראשונה — ומוצגות כאירוע יחיד עם ציר זמן. הדמיון נמדד
          על ייצוג סמנטי של הטקסט, ולא על מילים משותפות, ולכן שתי גרסאות של אותו סיפור
          מזוהות גם כשאין ביניהן אף מילה משותפת.
        </p>
      </section>
      <Suspense
        fallback={<div className="card p-8 text-center text-slate-500 dark:text-slate-400">טוען...</div>}
      >
        <EventsContent searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
