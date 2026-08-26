import Link from "next/link";
import { Calendar, FileText, Flame, Globe, Tags, TrendingUp } from "lucide-react";
import {
  getCategories,
  getPolarityBySource,
  getPolarityTrend,
  getSources,
  getStats,
} from "@/lib/api";
import { formatNumber, formatPercent, polarLevelLabel } from "@/lib/format";
import { HeroSection } from "@/components/HeroSection";
import { FilterSidebar } from "@/components/FilterSidebar";
import { StatsCard } from "@/components/StatsCard";
import { PolarityTrendChart } from "@/components/PolarityTrendChart";
import { SourcePolarityChart } from "@/components/SourcePolarityChart";
import { SourcesGrid } from "@/components/SourcesGrid";
import { TopicsCloud } from "@/components/TopicsCloud";
import { LeadingArticles } from "@/components/LeadingArticles";
import { ErrorState } from "@/components/ErrorState";
import { TrendingWidget } from "@/components/TrendingWidget";
import { LiveIndicator } from "@/components/LiveIndicator";

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const sp = await searchParams;
  const filters = {
    source: sp.source,
    category: sp.category,
    start_date: sp.start_date,
    end_date: sp.end_date,
  };

  let stats, trend, sourceBreakdown, sources, categories;
  try {
    [stats, trend, sourceBreakdown, sources, categories] = await Promise.all([
      getStats(filters),
      getPolarityTrend(filters),
      getPolarityBySource({
        category: filters.category,
        start_date: filters.start_date,
        end_date: filters.end_date,
      }),
      getSources(),
      getCategories(),
    ]);
  } catch {
    return (
      <div>
        <HeroSection />
        <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
          <ErrorState
            message="לא ניתן להתחבר ל-API"
            detail="ודא ש-PostgreSQL רץ ושהשרת פעיל: python pipeline/serve_api.py"
          />
        </div>
      </div>
    );
  }

  return (
    <div>
      <HeroSection />

      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
          <FilterSidebar sources={sources} categories={categories} dateRange={stats.date_range} />

          <div className="min-w-0 flex-1 space-y-10">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="sr-only">מדדי סיכום</h2>
              <LiveIndicator />
            </div>

            <section
              className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5"
              aria-label="מדדי סיכום"
            >
              <StatsCard
                icon={FileText}
                label="סה״כ כתבות"
                value={formatNumber(stats.total_articles)}
                accent="indigo"
              />
              <StatsCard
                icon={Globe}
                label="מקורות חדשות"
                value={formatNumber(stats.by_source.length)}
                hint="אתרי חדשות מובילים בסינון הנוכחי"
                accent="purple"
              />
              <StatsCard
                icon={Tags}
                label="נושאים מרכזיים"
                value={formatNumber(stats.by_category.length)}
                hint="קטגוריות תוכן מסווגות"
                accent="navy"
              />
              <StatsCard
                icon={TrendingUp}
                label="מדד קיטוב ממוצע"
                value={formatPercent(stats.avg_audience_mean)}
                hint={polarLevelLabel(stats.avg_audience_mean)}
                accent="positive"
              />
              <StatsCard
                icon={Calendar}
                label="אירועים פעילים"
                value={formatNumber(stats.active_events_count)}
                hint="אירועים שהסיקור עליהם עדיין נמשך"
                accent="purple"
              />
            </section>

            <section id="trend" className="card scroll-mt-24 p-5">
              <h2 className="mb-4 text-base font-semibold text-slate-800 dark:text-slate-200">
                מגמת קיטוב לאורך זמן
              </h2>
              <PolarityTrendChart data={trend} />
            </section>

            <section id="compare" className="card scroll-mt-24 p-5">
              <h2 className="mb-4 text-base font-semibold text-slate-800 dark:text-slate-200">
                פילוח קיטוב לפי אתרי חדשות
              </h2>
              <SourcePolarityChart data={sourceBreakdown} />
            </section>

            <section id="sources" className="scroll-mt-24">
              <h2 className="mb-4 text-base font-semibold text-slate-800 dark:text-slate-200">מקורות חדשות</h2>
              <SourcesGrid sources={stats.by_source} />
            </section>

            <section id="topics" className="card scroll-mt-24 p-5">
              <h2 className="mb-1 text-base font-semibold text-slate-800 dark:text-slate-200">נושאים מרכזיים</h2>
              <p className="mb-2 text-xs text-slate-400 dark:text-slate-500">
                מבוסס על קטגוריות התוכן שסווגו אוטומטית לכל כתבה. לחיצה על נושא מסננת את
                הדשבורד לפיו.
              </p>
              <TopicsCloud categories={stats.by_category} currentParams={sp} />
            </section>

            <section id="leading" className="scroll-mt-24">
              <div className="mb-4 flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <Flame className="h-5 w-5 text-[var(--purple)]" aria-hidden />
                  <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">כתבות בולטות</h2>
                </div>
                <Link
                  href="/articles"
                  className="text-sm font-medium text-[var(--indigo)] hover:underline"
                >
                  כל הכתבות ←
                </Link>
              </div>
              <p className="mb-4 -mt-2 text-xs text-slate-400 dark:text-slate-500">
                מדורגות לפי קיטוב בשיא התגובות (אחוזון 85).
                שיא חריף אומר שזנב התגובות חם, גם אם רוב הקהל רגוע.
              </p>
              <LeadingArticles articles={stats.hottest_articles} />
            </section>
          </div>

          <TrendingWidget />
        </div>
      </div>
    </div>
  );
}
