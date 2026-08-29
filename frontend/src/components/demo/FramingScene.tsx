"use client";

import type { ContrastEvent, FramingEvent, VerifierEvent } from "./types";

const VOICE_HE: Record<string, string> = {
  active: "פעיל",
  passive: "סביל",
};

interface FramingSceneProps {
  framings: FramingEvent[];
  contrast: ContrastEvent | null;
  verifier: VerifierEvent | null;
}

function Row({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex items-baseline gap-2 text-[15px]">
      <span className="shrink-0 text-[13px] font-semibold text-[var(--dk-ink-3)]">
        {label}
      </span>
      <span
        className={
          value
            ? "dk-truncate font-semibold text-[var(--dk-ink)]"
            : "text-[var(--dk-ink-3)]"
        }
      >
        {value ?? "לא מיוחס"}
      </span>
    </div>
  );
}

/**
 * Scene 5 — the same event, side by side, on the variables a word-counting
 * lexicon cannot see: who is named as the actor, to whom responsibility is
 * attributed, and whether the sentence has an actor at all.
 *
 * `loaded_terms` only ever contains terms that passed grounding; the verifier
 * strip at the bottom reports what it threw out, this event and overall.
 */
export function FramingScene({
  framings,
  contrast,
  verifier,
}: FramingSceneProps) {
  if (framings.length === 0) {
    return (
      <section className="dk-card flex h-full items-center justify-center">
        <p className="dk-breathe text-xl text-[var(--dk-ink-3)]">
          נובה מחלצת את משתני המסגור…
        </p>
      </section>
    );
  }

  const distinctive = new Map(
    (contrast?.per_source ?? []).map((c) => [c.source, c]),
  );

  return (
    <section className="dk-card dk-scale-in flex h-full min-h-0 flex-col gap-3 overflow-hidden p-5">
      <div className="flex items-center gap-3 rounded-xl border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)] px-4 py-2.5 text-[14px] leading-snug">
        <span className="text-xl" aria-hidden>
          🔍
        </span>
        <span>
          הלקסיקון סופר מילים ולכן <b>עיוור לשאלה מי עשה מה</b>. כאן מודל שפה
          מחלץ את מבצע הפעולה, את מי שאחראי, ואת הקול — על אותו אירוע בדיוק.
        </span>
      </div>

      <div
        className="grid min-h-0 flex-1 gap-3 overflow-hidden"
        style={{
          gridTemplateColumns: `repeat(${Math.min(framings.length, 4)}, minmax(0, 1fr))`,
        }}
      >
        {framings.map((f, i) => (
          <article
            key={f.article_id}
            className="dk-fade-up flex min-h-0 flex-col gap-2 overflow-hidden rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/70 p-4"
            style={{ animationDelay: `${i * 0.18}s` }}
          >
            <div className="flex items-center gap-2">
              <span className="rounded-full border border-[var(--dk-border)] px-2.5 py-0.5 text-[14px] font-bold text-[var(--dk-ink)]">
                {f.source_he}
              </span>
              {f.voice && (
                <span
                  className={`rounded-full px-2.5 py-0.5 text-[12px] font-semibold ${
                    f.voice === "passive"
                      ? "bg-[var(--dk-bad)]/10 text-[var(--dk-bad)]"
                      : "bg-[var(--dk-good)]/10 text-[var(--dk-good)]"
                  }`}
                >
                  קול {VOICE_HE[f.voice]}
                </span>
              )}
            </div>
            <h4 className="text-[15px] font-semibold leading-snug">
              {f.title}
            </h4>
            <div className="flex flex-col gap-1.5 border-t border-[var(--dk-border)] pt-2">
              <Row label="מבצע:" value={f.actor} />
              <Row label="אחריות:" value={f.responsibility} />
            </div>
            {f.loaded_terms.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {f.loaded_terms.map((t) => (
                  <span
                    key={t}
                    className="rounded-full bg-[var(--dk-accent-dim)] px-2.5 py-0.5 text-[13px] font-semibold text-[var(--dk-accent)]"
                  >
                    {t}
                  </span>
                ))}
              </div>
            )}
            {distinctive.get(f.source) && (
              <div className="mt-auto border-t border-[var(--dk-border)] pt-2">
                <div className="text-[12px] font-semibold text-[var(--dk-ink-3)]">
                  מה ייחודי בגרסה הזאת ביחס לאחרות
                </div>
                <p className="text-[14px] leading-snug text-[var(--dk-ink-2)]">
                  {distinctive.get(f.source)?.distinctive_he}
                </p>
                {distinctive.get(f.source)?.evidence_he && (
                  <p className="mt-1 border-r-2 border-[var(--dk-accent)]/50 pr-2 text-[13px] italic leading-snug text-[var(--dk-ink-3)]">
                    &quot;{distinctive.get(f.source)?.evidence_he}&quot;
                  </p>
                )}
              </div>
            )}
          </article>
        ))}
      </div>

      {contrast?.shared_he && (
        <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 px-4 py-2 text-[14px]">
          <b className="text-[var(--dk-ink-3)]">מה כולן מסכימות עליו:</b>{" "}
          {contrast.shared_he}
        </div>
      )}

      {verifier && (
        <div className="flex items-center gap-4 rounded-xl border border-[var(--dk-good)]/30 bg-[var(--dk-surface-2)]/70 px-4 py-2.5">
          <span className="text-xl" aria-hidden>
            🎓
          </span>
          <div className="text-[14px] leading-snug">
            <b>המאמת (דטרמיניסטי):</b> כל ביטוי נבדק מול אותם{" "}
            {verifier.lead_chars} התווים שהמודל קרא.{" "}
            <span dir="ltr" className="font-semibold">
              {verifier.terms_rejected}/{verifier.terms_total}
            </span>{" "}
            ביטויים ו־
            <span dir="ltr" className="font-semibold">
              {verifier.quotes_rejected}/{verifier.quotes_total}
            </span>{" "}
            ציטוטי ראיה נפסלו על כל הסנאפשוט — ומה שנפסל לא הגיע למסך הזה.
          </div>
          {verifier.rejected_quotes[0] && (
            <div className="mr-auto max-w-[30%] shrink-0 rounded-lg border border-[var(--dk-bad)]/40 px-3 py-1.5 text-[13px] leading-snug text-[var(--dk-ink-3)]">
              <span className="font-semibold text-[var(--dk-bad)]">נפסל: </span>
              <span className="line-through">
                {verifier.rejected_quotes[0].quote.slice(0, 60)}
              </span>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
