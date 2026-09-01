import Link from "next/link";
import { Calendar, FileText, Flame, Globe, Tags, TrendingUp } from "lucide-react";
import {
  getCategories,
  getEventDeviationProfile,
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
import { SourceAxesChart } from "@/components/SourceAxesChart";
import { EventDeviationChart } from "@/components/EventDeviationChart";
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

  const deviationMetric =
    sp.metric === "dominance" ? "dominance" : "audience_mean";

  let stats, trend, sourceBreakdown, sources, categories, deviation;
  try {
    [stats, trend, sourceBreakdown, sources, categories, deviation] = await Promise.all([
      getStats(filters),
      getPolarityTrend(filters),
      getPolarityBySource({
        category: filters.category,
        start_date: filters.start_date,
        end_date: filters.end_date,
      }),
      getSources(),
      getCategories(),
      // Never lets the whole dashboard fail: this is the newest endpoint, and
      // Vercel can be a deploy ahead of Render.
      getEventDeviationProfile(deviationMetric, filters.category).catch(() => null),
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

            <section id="within-event" className="card scroll-mt-24 p-5">
              <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">
                  אותו אירוע, מקורות שונים
                </h2>
                <div className="flex gap-1 text-xs">
                  {[
                    { key: "audience_mean", label: "תגובות הקהל" },
                    { key: "dominance", label: "טקסט הכתבה" },
                  ].map((option) => (
                    <Link
                      key={option.key}
                      href={{ query: { ...sp, metric: option.key } }}
                      scroll={false}
                      className={
                        deviationMetric === option.key
                          ? "rounded-md bg-[var(--purple)] px-2 py-0.5 font-semibold text-white"
                          : "rounded-md px-2 py-0.5 text-slate-500 hover:bg-[var(--border)] dark:text-slate-400"
                      }
                    >
                      {option.label}
                    </Link>
                  ))}
                </div>
              </div>
              <p className="mb-4 text-xs text-slate-400 dark:text-slate-500">
                הפילוח שלמעלה מודד בעיקר אילו סיפורים כל מקור בוחר לסקר. כאן הסיפור מוחזק
                קבוע: רק אירועים שסוקרו ביותר ממקור אחד, וכל מקור מושווה לחציון של אותו אירוע.
              </p>
              {deviation ? (
                <EventDeviationChart profile={deviation} />
              ) : (
                <p className="text-sm text-slate-400 dark:text-slate-500">
                  ההשוואה בתוך אירועים אינה זמינה כרגע.
                </p>
              )}
            </section>

            <section id="axes" className="card scroll-mt-24 p-5">
              <h2 className="mb-1 text-base font-semibold text-slate-800 dark:text-slate-200">
                קריאה שנייה — שפת נושא מול שפת עוינות
              </h2>
              <p className="mb-4 text-xs text-slate-400 dark:text-slate-500">
                מקור שבו שני הטורים דומים מנהל ויכוח על העניין עצמו באותה מידה שהוא מנהל
                אותו נגד הצד השני. פער לטובת שפת עוינות מצביע על ההפך.
              </p>
              <SourceAxesChart data={sourceBreakdown} />
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
