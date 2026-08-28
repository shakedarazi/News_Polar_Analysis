"use client";

import type { RetrievalEvent } from "./types";

interface RetrievalSceneProps {
  retrieval: RetrievalEvent | null;
}

/**
 * Scene 4 — the librarian's showcase: real semantic neighbors for a real
 * article, and why a small precise context beats streaming the whole text.
 */
export function RetrievalScene({ retrieval }: RetrievalSceneProps) {
  if (!retrieval) {
    return (
      <section className="dk-card flex h-full items-center justify-center">
        <p className="dk-breathe text-xl text-[var(--dk-ink-3)]">
          הספרנית מחשבת דמיון וקטורי מול המאגר…
        </p>
      </section>
    );
  }

  const maxScore = Math.max(...retrieval.neighbors.map((n) => n.score), 0.01);

  return (
    <section className="dk-card dk-scale-in flex h-full min-h-0 flex-col gap-4 overflow-hidden p-6">
      {/* the idea, spelled out — precedents, not a replacement */}
      <div className="flex items-center gap-3 rounded-xl border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)] px-4 py-3 text-[15px] leading-snug">
        <span className="text-2xl" aria-hidden>
          ⚖️
        </span>
        <span>
          <b>הרעיון:</b> הכתבה החדשה היא השאילתה — היא לא מוחלפת. הכתבות
          הדומות שנשלפו כבר <b>תויגו בעבר</b>, והתיוג שלהן משמש תקדים: כמו
          שופט שמצטט פסיקה קודמת במקום להכריע מאפס. אם רוב השכנים הקרובים
          תויגו &quot;ביטחון&quot; — זה עוגן עובדתי לסיווג, לא ניחוש של מודל.
        </span>
      </div>

      <div>
        <div className="text-sm font-semibold text-[var(--dk-ink-3)]">
          שאילתה — הכתבה הנוכחית
        </div>
        <h3 className="dk-truncate text-2xl font-bold">{retrieval.title}</h3>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2">
        <div className="text-sm font-semibold text-[var(--dk-ink-3)]">
          תקדימים: הכתבות הדומות ביותר במאגר · התיוג ההיסטורי שלהן · דמיון
          סמנטי (0–1)
        </div>
        {retrieval.neighbors.map((n, i) => (
          <div
            key={i}
            className="dk-fade-up flex items-center gap-3 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/70 px-4 py-2.5"
            style={{ animationDelay: `${i * 0.12}s` }}
          >
            <span className="dk-truncate flex-1 text-[16px]">{n.title}</span>
            <span className="shrink-0 rounded-full bg-[var(--dk-accent-dim)] px-3 py-0.5 text-[14px] font-bold text-[var(--dk-accent)]">
              {n.category}
            </span>
            <span className="flex w-[130px] shrink-0 items-center gap-2">
              <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--dk-accent-dim)]">
                <span
                  className="dk-bar-fill block h-full rounded-full bg-[var(--dk-accent)]"
                  style={{ width: `${(n.score / maxScore) * 100}%` }}
                />
              </span>
              <span
                className="w-10 text-[13px] font-semibold text-[var(--dk-ink-2)]"
                dir="ltr"
              >
                {n.score.toFixed(2)}
              </span>
            </span>
          </div>
        ))}
      </div>

      {/* the point of the scene: precise context saves tokens */}
      <div className="flex items-center justify-center gap-6 rounded-xl border border-[var(--dk-accent)]/30 bg-[var(--dk-accent-dim)] px-6 py-3">
        <div className="text-center">
          <div className="text-2xl font-bold text-[var(--dk-ink-2)] line-through decoration-[var(--dk-bad)]/70">
            ‎~{retrieval.tokens_full_est.toLocaleString("he-IL")}
          </div>
          <div className="text-[13px] text-[var(--dk-ink-3)]">
            טוקנים — הכתבה המלאה למודל
          </div>
        </div>
        <span className="text-2xl text-[var(--dk-accent)]" aria-hidden>
          ←
        </span>
        <div className="text-center">
          <div className="text-2xl font-bold text-[var(--dk-accent)]">
            ‎~{retrieval.tokens_context_est.toLocaleString("he-IL")}
          </div>
          <div className="text-[13px] text-[var(--dk-ink-3)]">
            טוקנים — כותרת + שכנים בלבד
          </div>
        </div>
        <div className="mr-4 border-r border-[var(--dk-border)] pr-4 text-[13px] leading-snug text-[var(--dk-ink-2)]">
          {retrieval.note_he}
        </div>
      </div>
    </section>
  );
}
