import Link from "next/link";
import { notFound } from "next/navigation";
import { ExternalLink, ArrowRight } from "lucide-react";
import { getArticle } from "@/lib/api";
import { formatDate, formatNumber, sourceLabel } from "@/lib/format";
import { SourceBadge } from "@/components/SourceBadge";
import { PolarScore } from "@/components/PolarScore";
import { DominanceChart } from "@/components/DominanceChart";
import { CommentsList } from "@/components/CommentsList";
import { AiSummaryCard } from "@/components/AiSummaryCard";

export default async function ArticlePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let article;
  try {
    article = await getArticle(id);
  } catch {
    notFound();
  }

  const agg = article.aggregation;
  const excerpt = article.text.slice(0, 400) + (article.text.length > 400 ? "…" : "");

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6">
      <Link
        href="/articles"
        className="inline-flex items-center gap-1 text-sm font-medium text-[var(--primary-light)] hover:underline"
      >
        <ArrowRight className="h-4 w-4" />
        חזרה לרשימת כתבות
      </Link>

      <header className="card p-6">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <SourceBadge source={article.source} />
          {article.primary_category && (
            <span className="rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-800">
              {article.primary_category}
            </span>
          )}
          <span className="text-xs text-slate-400">{formatDate(article.first_seen_at)}</span>
        </div>
        <h1 className="text-2xl font-bold leading-snug text-slate-900 sm:text-3xl">
          {article.title || "ללא כותרת"}
        </h1>
        <a
          href={article.canonical_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-[var(--primary-light)] hover:underline"
        >
          לכתבה המקורית ב-{sourceLabel(article.source)}
          <ExternalLink className="h-4 w-4" />
        </a>
        {article.category_rationale && (
          <p className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
            <strong className="text-slate-800">נימוק קטגוריה (AI):</strong>{" "}
            {article.category_rationale}
          </p>
        )}
        <p className="mt-4 text-sm leading-relaxed text-slate-600">{excerpt}</p>
      </header>

      <AiSummaryCard articleId={article.article_id} hasContent={article.text.trim().length > 0} />

      {agg ? (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="card p-4">
            <PolarScore value={agg.audience_mean} label="פולריות ממוצעת בקהל" large />
          </div>
          <div className="card p-4">
            <PolarScore value={agg.audience_p85} label="פולריות גבוהה (85%)" large />
          </div>
          <div className="card p-4">
            <p className="text-xs font-medium text-slate-500">מחלוקת בקהל</p>
            <p className="mt-2 text-2xl font-bold text-slate-900">
              {agg.controversy_mean !== null
                ? (agg.controversy_mean * 100).toFixed(1) + "%"
                : "—"}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-medium text-slate-500">תגובות שנותחו</p>
            <p className="mt-2 text-2xl font-bold text-slate-900">
              {formatNumber(agg.num_comments)}
            </p>
          </div>
        </section>
      ) : (
        <div className="card p-6 text-center text-slate-500">
          טרם בוצע ניתוח פולריות לכתבה זו
        </div>
      )}

      {article.windows.length > 0 && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-slate-900">דומיננטיות לפי משפט בכתבה</h2>
          <DominanceChart windows={article.windows} />
        </section>
      )}

      <section>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">תגובות מובילות בפולריות</h2>
        <CommentsList comments={article.comments} />
      </section>
    </div>
  );
}
