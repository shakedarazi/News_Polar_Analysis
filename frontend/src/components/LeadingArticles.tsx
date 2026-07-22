"use client";

import { useState } from "react";
import type { LeadingArticle } from "@/lib/types";
import { formatDate, polarLevel, polarLevelLabel, sourceLabel } from "@/lib/format";
import { SourceBadge } from "./SourceBadge";
import { ArticleThumbnail } from "./ArticleThumbnail";
import { EmptyState } from "./EmptyState";
import { ArticleDetailModal } from "./ArticleDetailModal";
import { CompactBiasBadge } from "./PoliticalBiasMeter";

const LEVEL_CLASS: Record<string, string> = {
  high: "score-high",
  mid: "score-mid",
  low: "score-low",
  none: "score-none",
};

export function LeadingArticles({ articles }: { articles: LeadingArticle[] }) {
  const [openId, setOpenId] = useState<string | null>(null);

  if (articles.length === 0) {
    return (
      <EmptyState message="לא נמצאו כתבות עם תגובות שנותחו התואמות לסינון שנבחר." />
    );
  }

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {articles.slice(0, 6).map((article) => {
          const level = polarLevel(article.audience_p85);
          return (
            <button
              key={article.article_id}
              type="button"
              onClick={() => setOpenId(article.article_id)}
              className="card card-hover flex gap-4 p-4 text-right"
            >
              <ArticleThumbnail seed={article.article_id} className="h-20 w-20" />
              <div className="min-w-0 flex-1">
                <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                  <SourceBadge source={article.source} />
                  {article.primary_category && (
                    <span className="rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:text-slate-300">
                      {article.primary_category}
                    </span>
                  )}
                </div>
                <h3 className="line-clamp-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                  {article.title || "ללא כותרת"}
                </h3>
                <p className="mt-2 flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 font-semibold ${LEVEL_CLASS[level]}`}
                  >
                    {polarLevelLabel(article.audience_p85)}
                  </span>
                  <span>{sourceLabel(article.source)}</span>
                  <span aria-hidden>·</span>
                  <span>{formatDate(article.first_seen_at)}</span>
                  {article.bias_label && (
                    <CompactBiasBadge
                      label={article.bias_label}
                      score={article.bias_score}
                      confidence={article.bias_confidence}
                    />
                  )}
                </p>
              </div>
            </button>
          );
        })}
      </div>
      <ArticleDetailModal articleId={openId} onClose={() => setOpenId(null)} />
    </>
  );
}
