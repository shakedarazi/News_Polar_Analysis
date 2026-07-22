"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { X, ExternalLink, Maximize2 } from "lucide-react";
import { getArticleBiasClient, getArticleClient } from "@/lib/api";
import { formatDate, formatNumber, sourceLabel } from "@/lib/format";
import type { ArticleBias, ArticleDetail } from "@/lib/types";
import { SourceBadge } from "./SourceBadge";
import { PolarScore } from "./PolarScore";
import { CommentsList } from "./CommentsList";
import { LoadingSkeleton } from "./LoadingSkeleton";
import { ErrorState } from "./ErrorState";
import { CompactBiasBadge } from "./PoliticalBiasMeter";

export function ArticleDetailModal({
  articleId,
  onClose,
}: {
  articleId: string | null;
  onClose: () => void;
}) {
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [bias, setBias] = useState<ArticleBias | null>(null);

  useEffect(() => {
    if (!articleId) return;
    let cancelled = false;
    setArticle(null);
    setError(false);
    setLoading(true);
    setBias(null);
    getArticleClient(articleId)
      .then((data) => {
        if (!cancelled) setArticle(data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    // Read-only: shows the compact badge only if a bias estimate already
    // exists (e.g. generated from a previous visit to the full article page)
    // — the modal never triggers on-demand AI generation itself.
    getArticleBiasClient(articleId)
      .then((data) => {
        if (!cancelled) setBias(data);
      })
      .catch(() => {
        /* silently omit the badge on failure — non-critical, compact context */
      });
    return () => {
      cancelled = true;
    };
  }, [articleId]);

  useEffect(() => {
    if (!articleId) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [articleId, onClose]);

  if (!articleId) return null;

  const agg = article?.aggregation;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 pt-10 sm:pt-16"
      role="dialog"
      aria-modal="true"
      aria-label="פרטי כתבה"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl bg-white dark:bg-slate-900 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 p-4">
          <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">פרטי כתבה</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="סגור חלונית"
            className="rounded-lg p-1.5 text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-700 dark:hover:text-slate-200"
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>

        <div className="max-h-[75vh] overflow-y-auto p-5">
          {loading && (
            <div className="space-y-3">
              <LoadingSkeleton className="h-6 w-2/3" />
              <LoadingSkeleton className="h-24" />
              <LoadingSkeleton className="h-32" />
            </div>
          )}

          {!loading && error && (
            <ErrorState message="לא ניתן לטעון את פרטי הכתבה" />
          )}

          {!loading && !error && article && (
            <div className="space-y-5">
              <div>
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <SourceBadge source={article.source} />
                  {article.primary_category && (
                    <span className="rounded-md bg-indigo-50 dark:bg-indigo-950 px-2 py-0.5 text-xs font-semibold text-indigo-800 dark:text-indigo-300">
                      {article.primary_category}
                    </span>
                  )}
                  <span className="text-xs text-slate-400 dark:text-slate-500">
                    {formatDate(article.first_seen_at)}
                  </span>
                  {bias?.status === "ready" && (
                    <CompactBiasBadge
                      label={bias.label}
                      score={bias.score}
                      confidence={bias.confidence}
                    />
                  )}
                </div>
                <h2 className="text-lg font-bold leading-snug text-slate-900 dark:text-slate-100">
                  {article.title || "ללא כותרת"}
                </h2>
                <a
                  href={article.canonical_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-[var(--indigo)] hover:underline"
                >
                  לכתבה המקורית ב-{sourceLabel(article.source)}
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                </a>
                <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                  {article.text.slice(0, 400)}
                  {article.text.length > 400 ? "…" : ""}
                </p>
              </div>

              {agg ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-xl bg-slate-50 dark:bg-slate-800 p-3">
                    <PolarScore value={agg.audience_mean} label="קיטוב ממוצע" />
                  </div>
                  <div className="rounded-xl bg-slate-50 dark:bg-slate-800 p-3">
                    <PolarScore value={agg.audience_p85} label="קיטוב גבוה (85%)" />
                  </div>
                  <div className="rounded-xl bg-slate-50 dark:bg-slate-800 p-3">
                    <p className="text-xs font-medium text-slate-500 dark:text-slate-400">מחלוקת בקהל</p>
                    <p className="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
                      {agg.controversy_mean !== null
                        ? `${(agg.controversy_mean * 100).toFixed(1)}%`
                        : "—"}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 dark:bg-slate-800 p-3">
                    <p className="text-xs font-medium text-slate-500 dark:text-slate-400">תגובות שנותחו</p>
                    <p className="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
                      {formatNumber(agg.num_comments)}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl bg-slate-50 dark:bg-slate-800 p-4 text-center text-sm text-slate-500 dark:text-slate-400">
                  טרם בוצע ניתוח פולריות לכתבה זו
                </div>
              )}

              {article.comments.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
                    תגובות מובילות בפולריות
                  </h3>
                  <CommentsList comments={article.comments.slice(0, 5)} />
                </div>
              )}

              <Link
                href={`/articles/${article.article_id}`}
                className="flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 py-2.5 text-sm font-medium text-[var(--indigo)] hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <Maximize2 className="h-4 w-4" aria-hidden />
                לעמוד המלא (כולל גרף דומיננטיות)
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
