"use client";

import { useState } from "react";
import type { ArticleSummary } from "@/lib/types";
import { formatDate, formatNumber } from "@/lib/format";
import { PolarScore } from "./PolarScore";
import { SourceBadge } from "./SourceBadge";
import { EmptyState } from "./EmptyState";
import { ArticleDetailModal } from "./ArticleDetailModal";

export function ArticlesTable({ articles }: { articles: ArticleSummary[] }) {
  const [openId, setOpenId] = useState<string | null>(null);

  if (!articles.length) {
    return (
      <div className="card">
        <EmptyState message="לא נמצאו כתבות התואמות לסינון שנבחר." />
      </div>
    );
  }

  return (
    <>
      <div className="card overflow-hidden">
        <div className="hidden overflow-x-auto md:block">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              <tr>
                <th className="px-4 py-3 text-right font-semibold">מקור</th>
                <th className="px-4 py-3 text-right font-semibold">כותרת</th>
                <th className="px-4 py-3 text-right font-semibold">קטגוריה</th>
                <th className="px-4 py-3 text-right font-semibold">תגובות</th>
                <th className="px-4 py-3 text-right font-semibold">פולריות ממוצעת</th>
                <th className="px-4 py-3 text-right font-semibold">פולריות גבוהה (85%)</th>
                <th className="px-4 py-3 text-right font-semibold">תאריך</th>
              </tr>
            </thead>
            <tbody>
              {articles.map((a) => (
                <tr key={a.article_id} className="border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800">
                  <td className="px-4 py-3">
                    <SourceBadge source={a.source} />
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => setOpenId(a.article_id)}
                      className="text-right font-medium text-slate-900 dark:text-slate-100 hover:text-[var(--primary-light)] line-clamp-2"
                    >
                      {a.title || "ללא כותרת"}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{a.primary_category || "—"}</td>
                  <td className="px-4 py-3">{formatNumber(a.num_comments ?? 0)}</td>
                  <td className="px-4 py-3">
                    <PolarScore value={a.audience_mean} />
                  </td>
                  <td className="px-4 py-3">
                    <PolarScore value={a.audience_p85} />
                  </td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400 whitespace-nowrap">
                    {formatDate(a.first_seen_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="divide-y divide-slate-100 md:hidden">
          {articles.map((a) => (
            <button
              key={a.article_id}
              type="button"
              onClick={() => setOpenId(a.article_id)}
              className="block w-full p-4 text-right hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <SourceBadge source={a.source} />
                <span className="text-xs text-slate-400 dark:text-slate-500">{formatDate(a.first_seen_at)}</span>
              </div>
              <h3 className="font-semibold text-slate-900 dark:text-slate-100 line-clamp-2">{a.title}</h3>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <PolarScore value={a.audience_mean} label="ממוצע" />
                <PolarScore value={a.audience_p85} label="85%" />
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  {formatNumber(a.num_comments ?? 0)} תגובות
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>
      <ArticleDetailModal articleId={openId} onClose={() => setOpenId(null)} />
    </>
  );
}
