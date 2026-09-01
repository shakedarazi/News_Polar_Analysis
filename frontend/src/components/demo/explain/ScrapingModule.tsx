"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import {
  Arrow,
  BarRow,
  Chip,
  Ladder,
  Node,
  Panel,
  Stage,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "discovery", label_he: "מאיפה מגיעות הכתבות" },
  { id: "extract", label_he: "איך מוציאים את הטקסט" },
  { id: "run", label_he: "מי מפעיל את זה" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: how articles get in — three questions a non-engineer would ask.
 *
 * Where do they come from (the outlet's own publication list, not a crawl —
 * with deduplication folded in as a single line, because a business reader
 * does not need the hashing chain to believe an article is counted once);
 * how the text comes out (a four-rung ladder, so a site redesign costs a rung
 * instead of the source); and who runs it (a scheduled free runner, so the
 * API host is free to sleep and the run flags a broken source itself).
 *
 * Everything here describes src/crawling/ as written. There is no headless
 * browser in the article path and no crawler framework; saying otherwise on a
 * wall in front of a panel would be the one unforced error this whole demo is
 * built to avoid.
 */
export function ScrapingModule({ facts }: Props) {
  const [tab, setTab] = useState("discovery");

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "discovery" && <Discovery facts={facts} />}
      {tab === "extract" && <Extract facts={facts} />}
      {tab === "run" && <Run facts={facts} />}
    </div>
  );
}

function num(x: number): string {
  return x.toLocaleString("en-US");
}

function Missing() {
  return (
    <p className="text-[15px] text-[var(--dk-ink-3)]">
      אין קובץ מדידות — הדיאגרמות מוצגות בלי המספרים.
    </p>
  );
}

/* ── 1. a feed list, not a crawl ────────────────────────────────── */

function Discovery({ facts }: Props) {
  const sources = facts?.sources ?? [];
  const ex = facts?.identity_example;
  const maxArticles = Math.max(1, ...sources.map((s) => s.articles));
  const rss = sources.filter((s) => s.discovery === "rss").length;
  const empty = sources.filter((s) => s.articles === 0).length;

  return (
    <Stage cols="grid-cols-[46%_1fr]">
      <Panel
        title="אנחנו קוראים את רשימת הפרסום של האתר, לא סורקים אותו"
        hint="src/crawling/sources/"
      >
        <div className="flex flex-col gap-4">
          {sources.length > 0 ? (
            <>
              <p className="text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
                כל אתר חדשות מפרסם רשימה רשמית של מה שיצא עכשיו — הכתובת שהוא
                נותן לגוגל ולאפליקציות. {rss} מ־{sources.length} המקורות
                מפרסמים אחת, ואנחנו קוראים אותה.
              </p>
              <p className="text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
                החלופה היא לסרוק את האתר ולנחש מה חדש: איטי, שביר בכל שינוי
                עיצוב, ולא מחזיר את אותו סט כתבות פעמיים. הרשימה הרשמית מגיעה
                מהאתר עצמו, ולכן היא גם מדויקת וגם מנומסת.
              </p>
              {ex && (
                <div className="rounded-xl border border-[var(--dk-good)]/35 bg-[var(--dk-good)]/6 px-3.5 py-2.5">
                  <div className="text-[15.5px] font-bold text-[var(--dk-good)]">
                    אותה כתבה בשתי כתובות נספרת פעם אחת
                  </div>
                  <p className="mt-1 text-[15px] leading-snug text-[var(--dk-ink-2)]">
                    קישור שהגיע מהאתר וקישור שעבר בוואטסאפ נראים שונה, ומצביעים
                    על אותה כתבה. שניהם מצטמצמים לאותו מזהה עוד לפני ההורדה,
                    ולכן שום כתבה לא נספרת פעמיים ולא נמשכת פעמיים.
                  </p>
                  {ex.same && (
                    <code
                      dir="ltr"
                      className="mt-1.5 block break-all font-mono text-[12.5px] text-[var(--dk-ink-3)]"
                    >
                      {ex.dirty_url}
                    </code>
                  )}
                </div>
              )}
            </>
          ) : (
            <Missing />
          )}
        </div>
      </Panel>

      <Panel title="מה נאסף בפועל, מקור־מקור" hint="כתבות בסנאפשוט">
        {sources.length > 0 ? (
          <div className="flex h-full flex-col gap-2 overflow-auto pe-1">
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              {empty} מהמקורות לא החזירו אף כתבה, והם נשארים בטבלה. כיסוי
              שמסתיר את מי שלא ענה הוא כיסוי שאי אפשר לתכנן לפיו.
            </p>
            {sources.map((s) => (
              <div
                key={s.id}
                className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-2.5"
              >
                <div className="mb-1.5 flex items-center gap-2">
                  <span className="text-[16.5px] font-bold">{s.source_he}</span>
                  <Chip tone={s.discovery === "rss" ? "neutral" : "accent"}>
                    {s.discovery === "rss"
                      ? `${s.feeds.length} רשימות פרסום`
                      : "בלי רשימה — נקרא מהדף"}
                  </Chip>
                  {s.articles === 0 && <Chip tone="bad">0 כתבות</Chip>}
                </div>
                <BarRow
                  label={s.id}
                  n={s.articles}
                  max={maxArticles}
                  tone={s.articles === 0 ? "muted" : "accent"}
                  note={
                    s.articles > 0
                      ? `${num(s.avg_chars)} תווים בממוצע`
                      : undefined
                  }
                />
              </div>
            ))}
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

/* ── 3. static fetching, and the ladder it pays for ─────────────── */

function Extract({ facts }: Props) {
  const minLen = facts?.constants.extract.min_len;
  const minPara = facts?.constants.extract.min_paragraph_len;
  const haaretz = facts?.sources.find((s) => s.id === "haaretz");
  const ynet = facts?.sources.find((s) => s.id === "ynet");

  return (
    <Stage cols="grid-cols-[52%_1fr]">
      <Panel
        title="אתר משנה את העיצוב שלו, והאיסוף לא נשבר"
        hint="src/crawling/extractors.py"
      >
        <div className="flex flex-col gap-3">
          <p className="text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
            טקסט הכתבה יושב בכל אתר במקום אחר, והמקום הזה משתנה. במקום להיצמד
            לדרך אחת ולהישבר איתה, יש ארבע דרכים לפי סדר איכות — והמערכת יורדת
            לדרך הבאה רק כשהקודמת לא החזירה מספיק.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Chip tone="good">בלי הרצת דפדפן</Chip>
            <Chip tone="warn">Playwright — רק תגובות הארץ</Chip>
          </div>
          <Ladder
            rungs={[
              {
                label: "הטקסט שהאתר מפרסם לגוגל",
                tone: "good",
                detail: (
                  <>
                    הנתון המובנה שהאתר מפרסם לגוגל: הטקסט שהעורך התכוון אליו,
                    בלי תפריטים ופרסומות.
                  </>
                ),
                fallsThroughWhen: minLen
                  ? `אין תגית, או שהגוף קצר מ־${minLen} תווים`
                  : "אין תגית, או שהגוף קצר מדי",
              },
              {
                label: "קריאה ממבנה הדף, לפי אתר",
                tone: "neutral",
                detail: (
                  <>
                    selectors לפי מקור, לפי הסדר. הראשון שמחזיר פסקאות מנצח
                    {minPara
                      ? `, ופסקה קצרה מ־${minPara} תווים נזרקת עם שורות הקרדיט והכיתובים`
                      : ""}
                    .
                  </>
                ),
                fallsThroughWhen: minLen
                  ? `אף selector לא הניב ${minLen} תווים`
                  : "אף selector לא הניב מספיק טקסט",
              },
              {
                label: "תקציר הפתיחה של הדף",
                tone: "bad",
                detail: (
                  <>
                    תקציר המטא של הדף: פסקה אחת שמעגנת מסגור, ולא גוף כתבה.
                  </>
                ),
                fallsThroughWhen: minLen
                  ? `גם זה מתחת ל־${minLen}`
                  : "גם זה קצר מדי",
              },
              {
                label: "הכתבה מדולגת ונספרת ככישלון",
                tone: "bad",
                detail: (
                  <>
                    הכתבה לא נשמרת, המזהה נשאר תפוס עד סוף הריצה, והאיסוף עובר
                    למקור הבא.
                  </>
                ),
              },
            ]}
          />
        </div>
      </Panel>

      <Panel
        title="גם מקור מאחורי תשלום נשאר בהשוואה"
        hint="אורך טקסט ממוצע לפי מקור"
      >
        {haaretz && ynet ? (
          <div className="flex flex-col gap-3">
            <div className="flex items-end gap-3">
              <BigStat
                label={ynet.source_he}
                value={num(ynet.avg_chars)}
                sub={`עד ${num(ynet.max_chars)} תווים`}
                tone="good"
              />
              <BigStat
                label={haaretz.source_he}
                value={num(haaretz.avg_chars)}
                sub={`עד ${num(haaretz.max_chars)} תווים`}
                tone="accent"
              />
            </div>
            <p className="text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
              ב{haaretz.source_he} גוף הכתבה סגור מאחורי מנוי, והמערכת מקבלת
              ממנו {num(haaretz.avg_chars)} תווים במקום {num(ynet.avg_chars)} —
              פסקת הפתיחה. די בה כדי לדעת איך הכתבה ממוסגרת.
            </p>
            <p className="text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
              מערכת שדורשת את הכתבה המלאה הייתה מוותרת על המקור הזה, ואיתו על
              השוואה בין הערוצים. עדיף פחות טקסט מכולם מאשר טקסט מלא מחלקם.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}

function BigStat({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub: string;
  // "accent" reads as a different grade of result rather than a worse one —
  // the short lead is what the ladder is designed to return, not a failure.
  tone: "good" | "bad" | "accent";
}) {
  const border = {
    good: "border-[var(--dk-good)]/40 bg-[var(--dk-good)]/6",
    bad: "border-[var(--dk-bad)]/40 bg-[var(--dk-bad)]/6",
    accent: "border-[var(--dk-accent)]/40 bg-[var(--dk-accent-dim)]/40",
  }[tone];
  const color = {
    good: "text-[var(--dk-good)]",
    bad: "text-[var(--dk-bad)]",
    accent: "text-[var(--dk-accent)]",
  }[tone];
  return (
    <div className={`flex-1 rounded-2xl border p-3 text-center ${border}`}>
      <div className="text-[14.5px] text-[var(--dk-ink-2)]">{label}</div>
      <div className={`text-3xl font-black ${color}`} dir="ltr">
        {value}
      </div>
      <div className="text-[13px] text-[var(--dk-ink-3)]">{sub}</div>
    </div>
  );
}

/* ── 4. who fires the run, and how fast it goes ─────────────────── */

function Run({ facts }: Props) {
  const c = facts?.constants;
  const delay = c?.crawl.delay_seconds;
  const ynet = facts?.sources.find((s) => s.id === "ynet");

  return (
    <Stage cols="grid-cols-[46%_1fr]">
      <Panel
        title="התזמון גר ב־GitHub Actions, ולכן ה־API חופשי להירדם"
        hint=".github/workflows/ingestion.yml"
      >
        <div className="flex flex-col gap-3">
          <div className="flex items-stretch justify-center gap-1">
            <Node title="runner מתוזמן" tone="good" sub="כל שש שעות" />
            <Arrow label="כותב ל־Postgres" />
            <Node title="Neon" mono tone="accent" sub="מסד מנוהל" />
            <Arrow label="קורא בלבד" />
            <Node title="API" tone="neutral" sub="רשאי להירדם" />
          </div>
          <p className="text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
            האיסוף רץ מעצמו כל שש שעות על תשתית חינמית, ולא על שרת שאנחנו
            מחזיקים. השרת שמגיש את הנתונים יכול להיות כבוי לגמרי — הנתונים
            ימשיכו להתעדכן בלעדיו.
          </p>
          <p className="text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
            הדרך הנפוצה — טיימר בתוך השרת עצמו — מחייבת להחזיק אותו ער עשרים
            וארבע שעות ביממה רק כדי שהשעון יתקתק. זה עלות חודשית קבועה על
            כלום.
          </p>
          {c && (
            <p className="text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
              אף אחד לא צופה בריצה, ולכן היא בודקת את עצמה: מקור שיותר מ־
              {Math.round(c.crawl.failure_rate_threshold * 100)}% מהכתבות שלו
              נכשלו מסומן ביומן כשבור — ורק אם היו לפחות{" "}
              {c.crawl.min_discovered_for_alert} כתבות באותה ריצה, כדי שמדגם
              זעיר לא ייצור אזעקת שווא.
            </p>
          )}
        </div>
      </Panel>

      <Panel title="אורח מנומס אצל האתרים שאנחנו קוראים" hint="src/crawling/base.py">
        {c && delay ? (
          <div className="flex flex-col gap-3">
            <p className="text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
              כתבה אחת בכל פעם, {delay} שניות המתנה בין אחת לשנייה. אף אתר לא
              מרגיש את התנועה שלנו, ולכן אף אתר לא חוסם אותנו.
            </p>
            {ynet && (
              <p className="text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
                המחיר: {num(ynet.articles)} הכתבות של ynet שבמאגר הן{" "}
                {Math.round((ynet.articles * delay) / 60)} דקות המתנה מצטברות.
                עבודת רקע יכולה להרשות לעצמה את הזמן הזה — אף אחד לא ממתין לה.
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2 text-[15px] text-[var(--dk-ink-2)]">
              <Chip tone="accent">שרת שנפל</Chip>
              <span>
                עד {c.retry.max_attempts} ניסיונות, בהמתנה גדלה
              </span>
              <Chip tone="bad">כתובת שלא קיימת</Chip>
              <span>מוותרים מיד</span>
            </div>
            <p className="text-[16px] leading-relaxed text-[var(--dk-ink-2)]">
              ההבחנה הזאת חוסכת את שני הכשלים: לא מציפים אתר שכבר בקושי עומד,
              ולא מבזבזים דקות על קישור שבור שלעולם לא יענה.
            </p>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </Stage>
  );
}
