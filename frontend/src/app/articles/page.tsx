import { Suspense } from "react";
import Link from "next/link";
import { getArticles, getCategories, getSources } from "@/lib/api";
import { ArticlesTable } from "@/components/ArticlesTable";
import { ArticleFilters } from "@/components/ArticleFilters";
import { formatNumber } from "@/lib/format";

const PAGE_SIZE = 30;

async function ArticlesContent({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const sp = await searchParams;
  const offset = Number(sp.offset ?? 0);
  const minPolar = sp.min_polar ? Number(sp.min_polar) : undefined;

  const [data, sources, categories] = await Promise.all([
    getArticles({
      source: sp.source,
      category: sp.category,
      min_audience_mean: minPolar,
      start_date: sp.start_date,
      end_date: sp.end_date,
      limit: PAGE_SIZE,
      offset,
    }),
    getSources(),
    getCategories(),
  ]);

  const totalPages = Math.ceil(data.total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const buildPageUrl = (page: number) => {
    const qs = new URLSearchParams();
    if (sp.source) qs.set("source", sp.source);
    if (sp.category) qs.set("category", sp.category);
    if (sp.min_polar) qs.set("min_polar", sp.min_polar);
    if (sp.start_date) qs.set("start_date", sp.start_date);
    if (sp.end_date) qs.set("end_date", sp.end_date);
    qs.set("offset", String((page - 1) * PAGE_SIZE));
    return `/articles?${qs}`;
  };

  return (
    <div className="space-y-6">
      <ArticleFilters sources={sources} categories={categories} />
      <p className="text-sm text-slate-500">
        מציג {formatNumber(data.items.length)} מתוך {formatNumber(data.total)} כתבות
      </p>
      <ArticlesTable articles={data.items} />
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          {currentPage > 1 && (
            <Link href={buildPageUrl(currentPage - 1)} className="card px-4 py-2 text-sm">
              הקודם
            </Link>
          )}
          <span className="text-sm text-slate-600">
            עמוד {currentPage} מתוך {totalPages}
          </span>
          {currentPage < totalPages && (
            <Link href={buildPageUrl(currentPage + 1)} className="card px-4 py-2 text-sm">
              הבא
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

export default function ArticlesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900">כתבות</h1>
        <p className="mt-1 text-slate-600">חיפוש וסינון לפי מקור, קטגוריה ומדד פולריות</p>
      </section>
      <Suspense fallback={<div className="card p-8 text-center text-slate-500">טוען...</div>}>
        <ArticlesContent searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
