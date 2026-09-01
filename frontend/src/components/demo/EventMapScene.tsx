"use client";

import type { Facts } from "./explain/facts";
import type { EventMapEvent } from "./types";

interface EventMapSceneProps {
  eventMap: EventMapEvent | null;
  facts: Facts | null;
}

/**
 * Scene 4 — the one place the AI is load-bearing.
 *
 * Two outlets covering the same event in Hebrew share almost no headline
 * words, so a keyword search finds nothing while the embedding finds the other
 * versions. Both numbers are computed live by the backend, and the headlines
 * are on screen so the audience can check the claim themselves.
 *
 * One story is an anecdote, and a story chosen for the demo is a chosen
 * anecdote. The strip along the bottom carries the two corpus-wide numbers the
 * retrieval module measures — how often keyword search finds a version at all,
 * and how often an accepted pair really is the same event — so what the
 * audience sees is a worked example of a measured claim rather than the claim
 * itself. Missing facts drop the strip, never the scene.
 */
export function EventMapScene({ eventMap, facts }: EventMapSceneProps) {
  if (!eventMap) {
    return (
      <section className="dk-card flex h-full items-center justify-center">
        <p className="dk-breathe text-xl text-[var(--dk-ink-3)]">
          הספרנית מחפשת מי עוד סיקר את הסיפור הזה…
        </p>
      </section>
    );
  }

  return (
    <section className="dk-card dk-scale-in flex h-full min-h-0 flex-col gap-4 overflow-hidden p-6">
      <div className="flex items-center gap-3 rounded-xl border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)] px-4 py-3 text-[15px] leading-snug">
        <span className="text-2xl" aria-hidden>
          🧭
        </span>
        <span>
          <b>השאלה:</b> מי עוד סיקר בדיוק את האירוע הזה? בלי התשובה אין מה
          להשוות — השוואה בין ערוצים על כתבות שונות מודדת <b>אילו סיפורים</b>{" "}
          כל אחד בוחר, לא איך הוא ממסגר אותם.
        </span>
      </div>

      <div>
        <div className="text-sm font-semibold text-[var(--dk-ink-3)]">
          נקודת המוצא — גרסה אחת {eventMap.topic_he && `· ${eventMap.topic_he}`}
        </div>
        <h3 className="text-2xl font-bold leading-snug">
          {eventMap.seed_title}
        </h3>
      </div>

      {/* the comparison this whole demo rests on */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-[var(--dk-bad)]/40 bg-[var(--dk-surface-2)]/70 px-4 py-3">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[var(--dk-bad)]" dir="ltr">
              {eventMap.keyword_found}/{eventMap.total}
            </span>
            <span className="text-[15px] font-semibold text-[var(--dk-ink-2)]">
              חיפוש מילולי על הכותרות
            </span>
          </div>
          <p className="text-[13px] leading-snug text-[var(--dk-ink-3)]">
            חפיפת מילים בין הכותרות (Jaccard ≥ 0.25) — בעברית זה כמעט אף פעם
            לא קורה
          </p>
        </div>
        <div className="rounded-xl border border-[var(--dk-good)]/40 bg-[var(--dk-surface-2)]/70 px-4 py-3">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[var(--dk-good)]" dir="ltr">
              {eventMap.semantic_found}/{eventMap.total}
            </span>
            <span className="text-[15px] font-semibold text-[var(--dk-ink-2)]">
              אחזור סמנטי (embeddings)
            </span>
          </div>
          <p className="text-[13px] leading-snug text-[var(--dk-ink-3)]">
            דמיון וקטורי על משמעות, לא על מילים — רץ כאן ועכשיו מול המאגר
          </p>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2">
        <div className="text-sm font-semibold text-[var(--dk-ink-3)]">
          מה שנמצא — אותו אירוע, מערכות אחרות
        </div>
        {eventMap.versions.map((v, i) => (
          <div
            key={v.title + i}
            className="dk-fade-up flex items-center gap-3 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/70 px-4 py-3"
            style={{ animationDelay: `${i * 0.15}s` }}
          >
            <span className="shrink-0 rounded-full border border-[var(--dk-border)] px-2.5 py-0.5 text-[14px] font-semibold text-[var(--dk-ink-2)]">
              {v.source_he}
            </span>
            <span className="dk-truncate flex-1 text-[16px]">{v.title}</span>
            <span className="shrink-0 text-left" dir="ltr">
              <span className="block text-[15px] font-bold text-[var(--dk-good)]">
                {v.score.toFixed(2)}
              </span>
              <span className="block text-[12px] text-[var(--dk-ink-3)]">
                דמיון סמנטי
              </span>
            </span>
            <span className="shrink-0 border-r border-[var(--dk-border)] pr-3 text-left" dir="ltr">
              <span className="block text-[15px] font-bold text-[var(--dk-bad)]">
                {v.keyword_overlap.toFixed(2)}
              </span>
              <span className="block text-[12px] text-[var(--dk-ink-3)]">
                חפיפת מילים
              </span>
            </span>
          </div>
        ))}
      </div>

      <Measured facts={facts} />
    </section>
  );
}

/** The corpus behind the one story on screen — or nothing, if facts are out. */
function Measured({ facts }: { facts: Facts | null }) {
  const keyword = facts?.retrieval?.keyword;
  const evals = facts?.evals;
  if (!keyword && !evals) return null;

  // precision is null when no labelled pair reaches the threshold; a band with
  // nothing in it has no rate, and inventing one is the failure this measures.
  const live = evals?.precision_sweep.find(
    (row) => row.threshold === evals.live_threshold && row.precision !== null,
  );

  return (
    <div className="flex shrink-0 flex-wrap items-baseline gap-x-5 gap-y-1 border-t border-[var(--dk-border)] pt-3 text-[13px] leading-snug text-[var(--dk-ink-3)]">
      <span className="font-semibold text-[var(--dk-ink-2)]">
        לא רק הסיפור הזה:
      </span>
      {keyword && (
        <span>
          על כל הסנאפשוט חיפוש מילולי מוצא{" "}
          <b className="text-[var(--dk-ink-2)]" dir="ltr">
            {keyword.found}/{keyword.total}
          </b>{" "}
          מהגרסאות
        </span>
      )}
      {live && evals && (
        <span>
          ומתוך מה שהאחזור מקבל בסף{" "}
          <b dir="ltr">{evals.live_threshold}</b>,{" "}
          <b className="text-[var(--dk-ink-2)]" dir="ltr">
            {Math.round((live.precision ?? 0) * 100)}%
          </b>{" "}
          באמת אותו אירוע — נמדד מול {evals.golden_set.pairs} זוגות מתויגים
        </span>
      )}
    </div>
  );
}
