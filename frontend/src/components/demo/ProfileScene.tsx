"use client";

import type { ProfileEvent } from "./types";

const sign = (v: number | null, digits = 4): string =>
  v === null || v === undefined
    ? "—"
    : `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;

interface ProfileSceneProps {
  profile: ProfileEvent | null;
}

/**
 * Scene 7 — zoom out from one story to every shared event in the snapshot.
 *
 * Deliberately shows what cannot be claimed as prominently as what can: cells
 * under the size threshold are greyed out, the change-point scan reports its
 * own detection power next to a null result, and the coverage column carries
 * the snapshot size that makes it readable.
 */
export function ProfileScene({ profile }: ProfileSceneProps) {
  if (!profile) {
    return (
      <section className="dk-card flex h-full items-center justify-center">
        <p className="dk-breathe text-xl text-[var(--dk-ink-3)]">
          מצטבר על כל האירועים המשותפים…
        </p>
      </section>
    );
  }

  const curveMax = Math.max(...profile.sampling_curve.map((c) => c.width), 0.01);
  const usableCells = profile.topic_cells.filter((c) => c.usable);

  return (
    <section className="dk-card dk-scale-in grid h-full min-h-0 grid-cols-[1.05fr_1fr] gap-4 overflow-hidden p-5">
      <div className="flex min-h-0 flex-col gap-3 overflow-hidden">
        <div className="rounded-xl border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)] px-4 py-2.5 text-[14px] leading-snug">
          כל גרסה נמדדת מול <b>חציון אותו אירוע בדיוק</b>, על{" "}
          <b>{profile.events_total}</b> אירועים משותפים. זה מקבע את החדשות
          עצמן — מה שנשאר הוא הבחירה המערכתית.
        </div>

        <div className="flex flex-col gap-2">
          <div className="text-sm font-semibold text-[var(--dk-ink-3)]">
            סטייה ממוצעת מהחציון · רווח סמך 95%
          </div>
          {profile.outlets.map((o) => (
            <div
              key={o.source}
              className="flex items-center gap-3 rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/70 px-4 py-2.5"
            >
              <span className="w-20 shrink-0 text-[15px] font-bold">
                {o.source}
              </span>
              <span className="w-16 shrink-0 text-[13px] text-[var(--dk-ink-3)]">
                n={o.n}
              </span>
              {o.mean === null ? (
                <span className="flex-1 text-[14px] text-[var(--dk-ink-3)]">
                  פחות מ־3 אירועים — אין מספיק ראיות לפרופיל
                </span>
              ) : (
                <>
                  <span
                    className={`w-24 text-[17px] font-bold ${
                      o.significant
                        ? "text-[var(--dk-accent)]"
                        : "text-[var(--dk-ink-2)]"
                    }`}
                    dir="ltr"
                  >
                    {sign(o.mean)}
                  </span>
                  <span
                    className="flex-1 text-[13px] text-[var(--dk-ink-3)]"
                    dir="ltr"
                  >
                    [{sign(o.lo)}, {sign(o.hi)}]
                  </span>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-0.5 text-[12px] font-semibold ${
                      o.significant
                        ? "bg-[var(--dk-good)]/10 text-[var(--dk-good)]"
                        : "bg-[var(--dk-surface)] text-[var(--dk-ink-3)]"
                    }`}
                  >
                    {o.significant ? "מובהק" : "חוצה אפס"}
                  </span>
                </>
              )}
            </div>
          ))}
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-hidden">
          <div className="text-sm font-semibold text-[var(--dk-ink-3)]">
            ככל שנדגמים יותר אירועים — רוחב רווח הסמך ({profile.curve_source_he}
            )
          </div>
          {profile.sampling_curve.map((c) => (
            <div key={c.n} className="flex items-center gap-3">
              <span
                className="w-12 shrink-0 text-[13px] text-[var(--dk-ink-3)]"
                dir="ltr"
              >
                n={c.n}
              </span>
              <span className="h-2.5 flex-1 overflow-hidden rounded-full bg-[var(--dk-accent-dim)]">
                <span
                  className="dk-bar-fill block h-full rounded-full bg-[var(--dk-accent)]"
                  style={{ width: `${(c.width / curveMax) * 100}%` }}
                />
              </span>
              <span className="w-16 text-[13px] font-semibold" dir="ltr">
                {c.width.toFixed(4)}
              </span>
            </div>
          ))}
          <p className="text-[12px] leading-snug text-[var(--dk-ink-3)]">
            לא קשת מבוימת: ההערכה מתכווצת כי יותר אירועים באמת מגבילים אותה.
          </p>
        </div>
      </div>

      <div className="flex min-h-0 flex-col gap-3 overflow-hidden">
        <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-hidden">
          <div className="text-sm font-semibold text-[var(--dk-ink-3)]">
            פילוח לפי תחום — תא מתחת ל־{profile.min_cell_events} אירועים לא
            יכול לצאת מובהק
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-hidden">
            {profile.topic_cells.slice(0, 8).map((c) => (
              <div
                key={`${c.source}-${c.topic_he}`}
                className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[14px] ${
                  c.usable
                    ? "border-[var(--dk-border)] bg-[var(--dk-surface-2)]/70"
                    : "border-[var(--dk-border)]/40 bg-transparent text-[var(--dk-ink-3)]"
                }`}
              >
                <span className="w-16 shrink-0 font-semibold">{c.source}</span>
                <span className="w-20 shrink-0">{c.topic_he}</span>
                <span className="w-12 shrink-0 text-[12px]" dir="ltr">
                  n={c.n}
                </span>
                <span className="w-20 font-semibold" dir="ltr">
                  {sign(c.mean)}
                </span>
                <span className="mr-auto text-[12px]">
                  {c.significant
                    ? "מובהק"
                    : c.usable
                      ? "לא מובהק"
                      : "מתחת לסף — לא ראיה"}
                </span>
              </div>
            ))}
          </div>
          <p className="text-[12px] leading-snug text-[var(--dk-ink-3)]">
            {usableCells.length} תאים מגיעים לסף הגודל,{" "}
            {profile.topic_cells.filter((c) => c.significant).length} מהם
            מובהקים. זו התוצאה, לא כשל בהצגה.
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="text-sm font-semibold text-[var(--dk-ink-3)]">
            גלאי נקודת־שינוי — האם קו המערכת זז בתוך התקופה?
          </div>
          {profile.change_scans.map((s) => (
            <div
              key={`${s.source}-${s.topic_he}`}
              className="flex items-center gap-2 rounded-lg border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/70 px-3 py-1.5 text-[14px]"
            >
              <span className="w-16 shrink-0 font-semibold">{s.source}</span>
              <span className="w-20 shrink-0">{s.topic_he}</span>
              <span className="w-12 shrink-0 text-[12px]" dir="ltr">
                n={s.n}
              </span>
              <span className="w-20 text-[13px]" dir="ltr">
                p={s.p_value.toFixed(3)}
              </span>
              <span className="mr-auto text-[12px] text-[var(--dk-ink-3)]">
                {s.detected
                  ? "נמצאה נקודת שינוי"
                  : `לא נמצאה · עוצמת גילוי ${(s.power_1sd * 100).toFixed(0)}%`}
              </span>
            </div>
          ))}
          <p className="text-[12px] leading-snug text-[var(--dk-ink-3)]">
            &quot;לא נמצא&quot; נאמר תמיד יחד עם עוצמת הגילוי — כלומר: לא נמצא
            שינוי <b>בגודל שיכולנו לראות</b>.
          </p>
        </div>
      </div>
    </section>
  );
}
