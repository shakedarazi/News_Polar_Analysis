import Link from "next/link";
import { notFound } from "next/navigation";
import { ExternalLink, ArrowRight } from "lucide-react";
import { getArticle } from "@/lib/api";
import { formatDate, formatNumber, POLAR_MEAN_METRIC, POLAR_PEAK_METRIC, sourceLabel } from "@/lib/format";
import { SourceBadge } from "@/components/SourceBadge";
import { PolarScore } from "@/components/PolarScore";
import { DominanceChart } from "@/components/DominanceChart";
import { CommentsList } from "@/components/CommentsList";
import { AiSummaryCard } from "@/components/AiSummaryCard";
import { PoliticalBiasMeter } from "@/components/PoliticalBiasMeter";
import { AnalysisStatusBar } from "@/components/AnalysisStatusBar";

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
            <span className="rounded-md bg-indigo-50 dark:bg-indigo-950 px-2 py-0.5 text-xs font-semibold text-indigo-800 dark:text-indigo-300">
              {article.primary_category}
            </span>
          )}
          <span className="text-xs text-slate-400 dark:text-slate-500">{formatDate(article.first_seen_at)}</span>
        </div>
        <h1 className="text-2xl font-bold leading-snug text-slate-900 dark:text-slate-100 sm:text-3xl">
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
          <p className="mt-4 rounded-lg bg-slate-50 dark:bg-slate-800 p-3 text-sm text-slate-600 dark:text-slate-300">
            <strong className="text-slate-800 dark:text-slate-200">נימוק קטגוריה (AI):</strong>{" "}
            {article.category_rationale}
          </p>
        )}
        <p className="mt-4 text-sm leading-relaxed text-slate-600 dark:text-slate-300">{excerpt}</p>
      </header>

      <AiSummaryCard articleId={article.article_id} hasContent={article.text.trim().length > 0} />
      <PoliticalBiasMeter articleId={article.article_id} hasContent={article.text.trim().length > 0} />

      <AnalysisStatusBar
        hasWindows={article.windows.length > 0}
        hasAudienceAnalysis={!!agg}
        firstSeenAt={article.first_seen_at}
      />

      {agg && (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="card p-4">
            <PolarScore value={agg.audience_mean} label={POLAR_MEAN_METRIC} large />
            <p className="mt-1 text-[11px] text-slate-400 dark:text-slate-500">
              רשימת המילים של המערכת
            </p>
          </div>
          <div className="card p-4">
            <PolarScore value={agg.audience_p85} label={POLAR_PEAK_METRIC} variant="peak" large />
          </div>
          <div className="card p-4">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">מחלוקת בקהל</p>
            <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
              {agg.controversy_mean !== null
                ? (agg.controversy_mean * 100).toFixed(1) + "%"
                : "—"}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">תגובות שנותחו</p>
            <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
              {formatNumber(agg.num_comments)}
            </p>
          </div>
        </section>
      )}

      {/* The research lexicon's reading of the same comments. Kept in its own
          section, and deliberately not rendered with PolarScore: that
          component's colour scale is calibrated on the other list's
          distribution, and reusing it here would imply the two numbers sit on
          one axis. They do not — see docs/adr/0004. */}
      {agg && agg.audience_issue_mean !== null && agg.audience_affective_mean !== null && (
        <section className="card p-5">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            קריאה שנייה — מילון הקיטוב המחקרי
          </h2>
          <p className="mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            אותן תגובות, נספרות מול מילון אחר: ההתאמה העברית ל־Simchon, Brady &amp; Van Bavel
            (2022), שהתפצל לשני צירים. שתי הרשימות חולקות 15% מהמילים שלהן, ולכן המספרים כאן
            אינם גרסה מדויקת יותר של הקיטוב שלמעלה — הם מדידה נפרדת, ואינם נסכמים איתו.
          </p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                שפת נושא — על מה הוויכוח
              </p>
              <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
                {(agg.audience_issue_mean * 100).toFixed(2)}%
              </p>
              <p className="mt-1 text-[11px] text-slate-400 dark:text-slate-500">
                0% = אף מילה מהציר הזה · 100% = כל מילה בתגובה
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                שפת עוינות — נגד מי
              </p>
              <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
                {(agg.audience_affective_mean * 100).toFixed(2)}%
              </p>
              <p className="mt-1 text-[11px] text-slate-400 dark:text-slate-500">
                0% = אף מילה מהציר הזה · 100% = כל מילה בתגובה
              </p>
            </div>
          </div>
        </section>
      )}

      {article.windows.length > 0 && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">דומיננטיות לפי משפט בכתבה</h2>
          <DominanceChart windows={article.windows} />
        </section>
      )}

      <section>
        <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">תגובות מובילות בפולריות</h2>
        <CommentsList comments={article.comments} />
      </section>
    </div>
  );
}
