import type { CommentItem } from "@/lib/types";
import { formatNumber } from "@/lib/format";
import { PolarScore } from "./PolarScore";

export function CommentsList({ comments }: { comments: CommentItem[] }) {
  if (!comments.length) {
    return <div className="card p-8 text-center text-slate-500 dark:text-slate-400">אין תגובות לכתבה זו</div>;
  }

  return (
    <div className="space-y-3">
      {comments.map((c) => (
        <article key={c.comment_id} className="card p-4">
          <div className="mb-2 flex flex-wrap items-center gap-3">
            <PolarScore value={c.polar_ratio} label="עוצמת תגובה" />
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {formatNumber(c.like_count)} לייקים
              {c.author ? ` · ${c.author}` : ""}
            </span>
          </div>
          <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{c.text}</p>
        </article>
      ))}
    </div>
  );
}
