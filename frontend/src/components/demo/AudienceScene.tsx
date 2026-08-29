"use client";

import type { AudienceGapEvent } from "./types";

const fmt = (v: number | null, digits = 3): string =>
  v === null || v === undefined ? "—" : v.toFixed(digits);

interface AudienceSceneProps {
  audience: AudienceGapEvent[];
}

/**
 * Scene 6 — the same event, and what each outlet's readers did with it.
 *
 * `hijacked` is the moment worth stopping on: the article's dominant lexicon
 * topic and the comment thread's dominant topic are different, which means the
 * readers took the story somewhere the newsroom did not.
 */
export function AudienceScene({ audience }: AudienceSceneProps) {
  if (audience.length === 0) {
    return (
      <section className="dk-card flex h-full items-center justify-center">
        <p className="dk-breathe text-xl text-[var(--dk-ink-3)]">
          נטענים פרופילי התגובות…
        </p>
      </section>
    );
  }

  const maxP85 = Math.max(...audience.map((a) => a.audience_p85 ?? 0), 0.01);

  return (
    <section className="dk-card dk-scale-in flex h-full min-h-0 flex-col gap-3 overflow-hidden p-5">
      <div className="flex items-center gap-3 rounded-xl border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)] px-4 py-2.5 text-[14px] leading-snug">
        <span className="text-xl" aria-hidden>
          👥
        </span>
        <span>
          אותו אירוע בדיוק, ושלושה קהלים. הנושא של התגובות נספר באותו מילון של
          הכתבות — כך אפשר לומר <b>שהקוראים דיברו על משהו אחר</b> ולא רק להתרשם.
        </span>
      </div>

      <div
        className="grid min-h-0 flex-1 gap-3 overflow-hidden"
        style={{
          gridTemplateColumns: `repeat(${Math.min(audience.length, 4)}, minmax(0, 1fr))`,
        }}
      >
        {audience.map((a, i) => (
          <article
            key={a.article_id}
            className={`dk-fade-up flex min-h-0 flex-col gap-2 overflow-hidden rounded-xl border p-4 ${
              a.hijacked
                ? "border-[var(--dk-accent)]/50 bg-[var(--dk-accent-dim)]/40"
                : "border-[var(--dk-border)] bg-[var(--dk-surface-2)]/70"
            }`}
            style={{ animationDelay: `${i * 0.18}s` }}
          >
            <div className="flex items-center gap-2">
              <span className="rounded-full border border-[var(--dk-border)] px-2.5 py-0.5 text-[14px] font-bold">
                {a.source_he}
              </span>
              <span className="text-[13px] text-[var(--dk-ink-3)]">
                {a.num_comments ?? 0} תגובות
              </span>
            </div>

            <div className="flex items-center justify-center gap-2 rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface)]/60 px-3 py-2 text-[14px]">
              <span className="font-semibold">{a.article_topic_he ?? "—"}</span>
              <span
                className={
                  a.hijacked
                    ? "text-[var(--dk-accent)]"
                    : "text-[var(--dk-ink-3)]"
                }
                aria-hidden
              >
                ←
              </span>
              <span
                className={`font-semibold ${a.hijacked ? "text-[var(--dk-accent)]" : ""}`}
              >
                {a.comment_topic_he ?? "—"}
              </span>
            </div>
            <div className="text-center text-[12px] text-[var(--dk-ink-3)]">
              נושא הכתבה ← נושא התגובות
              {a.hijacked && (
                <b className="text-[var(--dk-accent)]"> · הקהל חטף את הסיפור</b>
              )}
            </div>

            <div className="flex items-end gap-3 border-t border-[var(--dk-border)] pt-2">
              <div className="flex-1">
                <div className="text-[12px] text-[var(--dk-ink-3)]">
                  קיטוב הזנב הקולני (p85)
                </div>
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-[var(--dk-accent-dim)]">
                  <span
                    className="dk-bar-fill block h-full rounded-full bg-[var(--dk-accent)]"
                    style={{
                      width: `${((a.audience_p85 ?? 0) / maxP85) * 100}%`,
                    }}
                  />
                </div>
              </div>
              <span className="text-[16px] font-bold" dir="ltr">
                {fmt(a.audience_p85)}
              </span>
            </div>

            {a.top_comment && (
              <div className="mt-auto min-h-0 overflow-hidden border-t border-[var(--dk-border)] pt-2">
                <div className="text-[12px] font-semibold text-[var(--dk-ink-3)]">
                  התגובה המדורגת ביותר · {a.top_comment.like_count} לייקים
                </div>
                <p className="text-[14px] leading-snug text-[var(--dk-ink-2)]">
                  &quot;{a.top_comment.text.slice(0, 180)}&quot;
                </p>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
