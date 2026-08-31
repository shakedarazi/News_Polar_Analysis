"use client";

import { useState } from "react";
import type { Facts } from "./facts";
import {
  Arrow,
  BarRow,
  Caveat,
  Chip,
  CodeRef,
  Ladder,
  Node,
  Panel,
  SubNav,
  type TabDef,
} from "./kit";

const TABS: TabDef[] = [
  { id: "discovery", label_he: "הגילוי" },
  { id: "identity", label_he: "מפתח הזהות" },
  { id: "extract", label_he: "סולם החילוץ" },
  { id: "run", label_he: "התזמון והקצב" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: how articles actually get in — four decisions, one per tab.
 *
 * Discovery reads a fixed feed list instead of crawling a link tree; identity
 * is sha256 of the canonical URL, claimed before the fetch rather than after
 * the save; the article path is requests + lxml with no JavaScript, which is
 * what the fallback ladder pays for; and the schedule lives in GitHub Actions,
 * which is what frees the API host to sleep.
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
      {tab === "identity" && <Identity facts={facts} />}
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
  const maxArticles = Math.max(1, ...sources.map((s) => s.articles));
  const rss = sources.filter((s) => s.discovery === "rss").length;
  const empty = sources.filter((s) => s.articles === 0).length;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <Panel
        title="הגילוי קורא פידים ולא זוחל על האתר"
        hint="src/crawling/sources/"
      >
        <div className="flex flex-col gap-4">
          <div className="flex items-stretch gap-2">
            <Node
              title="RSS / feedparser"
              tone="accent"
              wide
              sub={
                <>
                  כל
                  <code dir="ltr" className="mx-1 font-mono">
                    entry.link
                  </code>
                  נאסף. קישור שכבר נראה בפיד אחר נזרק.
                </>
              }
            />
            <Node
              title="__NEXT_DATA__"
              tone="accent"
              wide
              mono
              sub={
                <>
                  לרשת 13 אין פיד. הגילוי סורק את בלוב ה־JSON של הדף אחרי כל
                  מחרוזת שמכילה
                  <code dir="ltr" className="mx-1 font-mono">
                    /item/news/newsfeed/article-
                  </code>
                </>
              }
            />
          </div>

          {sources.length > 0 && (
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              {rss} מהמקורות מפרסמים פיד, והגילוי מושך רק אותם. זחילה על עץ
              הקישורים הייתה דורשת פרסר נפרד לכל אתר.
            </p>
          )}

          <Caveat>
            כתבה שלא עברה בפיד — המערכת לא תגלה אותה. זו החלטה, לא מגבלה
            טכנית.
          </Caveat>
        </div>
      </Panel>

      <Panel
        title="מקור שהחזיר אפס נשאר בטבלה"
        hint="פידים רשומים ← כתבות בסנאפשוט"
      >
        {sources.length > 0 ? (
          <div className="flex h-full flex-col gap-2 overflow-auto pe-1">
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              {sources.length} מקורות רשומים, {empty} מהם בלי כתבות בסנאפשוט.
              הסתרת מקור ריק הייתה מנפחת את הכיסוי.
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
                      ? `${s.feeds.length} פידים`
                      : "__NEXT_DATA__"}
                  </Chip>
                  {s.bespoke_he && <Chip tone="warn">{s.bespoke_he}</Chip>}
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
    </div>
  );
}

/* ── 2. identity, claimed before the fetch ──────────────────────── */

function Identity({ facts }: Props) {
  const ex = facts?.identity_example;
  const params = facts?.constants.canonical.tracking_params ?? [];

  return (
    <div className="grid min-h-0 flex-1 grid-rows-[auto_1fr] gap-3">
      <Panel
        title="המזהה נתפס לפני ההורדה, לא אחרי השמירה"
        hint="src/common/canonical_url.py · src/common/hashing.py"
      >
        <div className="flex flex-col gap-3">
          <div className="flex items-stretch justify-center gap-1">
            <Node title="URL גולמי" mono sub="כפי שהגיע מהפיד או משיתוף" />
            <Arrow label="https, host קטן, בלי / בסוף" />
            <Node title="canonicalize_url" mono tone="accent" />
            <Arrow
              label={
                params.length
                  ? `מסיר ${params.length} פרמטרי מעקב`
                  : "מסיר פרמטרי מעקב"
              }
            />
            <Node title="canonical_url" mono tone="accent" />
            <Arrow label="sha256" />
            <Node title="article_id" mono tone="good" sub="מפתח ראשי בטבלה" />
          </div>
          <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
            <code dir="ltr" className="font-mono text-[14.5px]">
              check_and_add
            </code>{" "}
            תופס את המזהה בבדיקה אטומית אחת לפני שהכתבה נמשכת. כתבה מוכרת לא
            נמשכת שוב, ושני מקורות שרצים במקביל לא ישמרו אותה פעמיים.
          </p>
        </div>
      </Panel>

      <Panel
        title="אותה כתבה בשתי כתובות, מזהה אחד"
        hint="הסקריפט מלכלך כתובת מהסנאפשוט ומריץ עליה את הקוד"
      >
        {ex ? (
          <div className="flex flex-col gap-2.5">
            <UrlRow label="נקייה" url={ex.clean_url} />
            <UrlRow label="משותפת בוואטסאפ" url={ex.dirty_url} dirty />
            <div className="text-center text-lg text-[var(--dk-ink-3)]">↓</div>
            <div className="rounded-xl border border-[var(--dk-good)]/40 bg-[var(--dk-good)]/6 p-3">
              <div className="mb-1 text-[14.5px] text-[var(--dk-ink-2)]">
                שתיהן מצטמצמות לאותה כתובת קנונית:
              </div>
              <code
                dir="ltr"
                className="block break-all font-mono text-[15px] text-[var(--dk-good)]"
              >
                {ex.clean_canonical}
              </code>
              <div className="mt-2 mb-1 text-[14.5px] text-[var(--dk-ink-2)]">
                ולכן לאותו מזהה — וזה המזהה השמור בטבלה:
              </div>
              <code
                dir="ltr"
                className="block break-all font-mono text-[13.5px] text-[var(--dk-good)]"
              >
                {ex.article_id}
              </code>
            </div>
            <Chip tone={ex.same ? "good" : "bad"}>
              {ex.same
                ? "✓ ההשוואה רצה בזמן הבנייה והחזירה true"
                : "✗ ההשוואה נכשלה — האינווריאנט נשבר"}
            </Chip>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}

function UrlRow({
  label,
  url,
  dirty = false,
}: {
  label: string;
  url: string;
  dirty?: boolean;
}) {
  return (
    <div className="rounded-xl border border-[var(--dk-border)] bg-[var(--dk-surface-2)]/50 p-2.5">
      <div className="mb-1 text-[13.5px] text-[var(--dk-ink-3)]">{label}</div>
      <code
        dir="ltr"
        className={`block break-all font-mono text-[14.5px] ${dirty ? "text-[var(--dk-warn)]" : "text-[var(--dk-ink)]"}`}
      >
        {url}
      </code>
    </div>
  );
}

/* ── 3. static fetching, and the ladder it pays for ─────────────── */

function Extract({ facts }: Props) {
  const minLen = facts?.constants.extract.min_len;
  const minPara = facts?.constants.extract.min_paragraph_len;
  const haaretz = facts?.sources.find((s) => s.id === "haaretz");
  const ynet = facts?.sources.find((s) => s.id === "ynet");

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[52%_1fr] gap-3">
      <Panel
        title="מסלול הכתבות לא מריץ JavaScript"
        hint="src/crawling/extractors.py"
      >
        <div className="flex flex-col gap-3">
          <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
            דפדפן חסר־ראש היה פותר את שכבת ה־DOM אצל חלק מהמקורות, במחיר סדר
            גודל בזמן לכל כתבה. במקומו יש סולם: ארבע שכבות, כל אחת פחות אמינה
            מקודמתה.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <CodeRef path="requests" />
            <CodeRef path="lxml" />
            <Chip tone="warn">Playwright — רק תגובות הארץ</Chip>
          </div>
          <Ladder
            rungs={[
              {
                label: "JSON-LD · NewsArticle.articleBody",
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
                label: "DOM · selectors ייעודיים לאתר",
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
                label: "og:description",
                tone: "bad",
                detail: (
                  <>
                    תקציר המטא של הדף. פסקה אחת, לא כתבה — כישלון מוסווה, לא
                    הצלחה.
                  </>
                ),
                fallsThroughWhen: minLen
                  ? `גם זה מתחת ל־${minLen}`
                  : "גם זה קצר מדי",
              },
              {
                label: "ValueError → נספר כ־failed",
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
        title={
          haaretz
            ? `בהארץ נשמר התקציר, ולכן ${num(haaretz.avg_chars)} תווים`
            : "בהארץ נשמר התקציר, לא הכתבה"
        }
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
                sub={`המקסימום כולו ${num(haaretz.max_chars)} תווים`}
                tone="bad"
              />
            </div>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              גוף הכתבה מאחורי תשלום, שתי השכבות הראשונות נופלות, והמערכת
              שומרת את <code dir="ltr">og:description</code>. זו חתימת האורך
              שלו, לא כתיבה תמציתית.
            </p>
            <Caveat>
              כל מסקנה על {haaretz.source_he} נשענת על פסקה אחת לכתבה. משם מגיע
              רווח הסמך הרחב שלו.
            </Caveat>
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
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
  tone: "good" | "bad";
}) {
  const border =
    tone === "good"
      ? "border-[var(--dk-good)]/40 bg-[var(--dk-good)]/6"
      : "border-[var(--dk-bad)]/40 bg-[var(--dk-bad)]/6";
  const color =
    tone === "good" ? "text-[var(--dk-good)]" : "text-[var(--dk-bad)]";
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
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <Panel
        title="התזמון גר ב־GitHub Actions, ולכן ה־API חופשי להירדם"
        hint=".github/workflows/ingestion.yml"
      >
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-2">
            <Node
              title="cron של מערכת ההפעלה"
              tone="bad"
              sub="macOS חסם אותו בשקט, והריצה לא קרתה"
            />
            <Node
              title="APScheduler בתוך ה־API"
              tone="bad"
              sub="מחייב את שרת ה־API להישאר ער רק כדי להפעיל טיימר"
            />
            <Node
              title="GitHub Actions"
              tone="good"
              sub="runner חינמי, cron כל שש שעות, והרצה ידנית ב־workflow_dispatch"
            />
          </div>
          <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
            שני המנגנונים הראשונים כשלו, והשלישי הוציא את הטיימר מתהליך ה־API.
            השרת שמגיש את הנתונים יכול להירדם בלי שהם יתיישנו.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Chip tone="neutral">
              <span dir="ltr" className="font-mono">
                0 */6 * * *
              </span>
            </Chip>
            <CodeRef path="scripts/run_ingestion.sh" />
          </div>
          {c && (
            <Caveat>
              מקור שנשבר מייצר שורה ביומן:{" "}
              <span dir="ltr" className="font-mono">
                failed / (saved + failed)
              </span>{" "}
              מעל {c.crawl.failure_rate_threshold}, ורק מ־
              {c.crawl.min_discovered_for_alert} כתבות שהתגלו ומעלה. כפילויות
              שדולגו לא נכנסות למכנה. אף אחד לא מקבל הודעה.
            </Caveat>
          )}
        </div>
      </Panel>

      <Panel
        title={
          delay
            ? `לולאה אחת, ${delay} שניות בין כתבה לכתבה`
            : "האיסוף סדרתי, בכוונה"
        }
        hint="src/crawling/base.py"
      >
        {c && delay ? (
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-center gap-1">
              <Node title="כתבה" tone="neutral" />
              <Arrow label={`${delay}s`} />
              <Node title="כתבה" tone="neutral" />
              <Arrow label={`${delay}s`} />
              <Node title="כתבה" tone="neutral" />
            </div>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              אין באטצ׳ים מקביליים בתוך מקור. ההשהיה קונה נימוס כלפי אתר שלא
              ביקש את התנועה, וסדר כתיבה זהה בכל ריצה.
            </p>
            <div className="flex flex-wrap items-center gap-2 text-[14.5px] text-[var(--dk-ink-2)]">
              <Chip tone="accent">timeout · 5xx</Chip>
              <span>
                עד {c.retry.max_attempts} ניסיונות, המתנה{" "}
                {c.retry.backoff_sequence_s.map((b) => `${b}s`).join(" ואז ")}
              </span>
              <Chip tone="bad">4xx</Chip>
              <span>נזרק מיד</span>
            </div>
            <p className="text-[15.5px] leading-snug text-[var(--dk-ink-2)]">
              ניסיון חוזר על 404 קונה עיכוב. שרת שקרס תחת עומס דווקא יענה אם
              מחכים.
            </p>
            {ynet && (
              <Caveat>
                {num(ynet.articles)} כתבות ynet שבסנאפשוט הן{" "}
                {Math.round((ynet.articles * delay) / 60)} דקות המתנה בלבד,
                פרוסות על כל הריצות. זה מתקבל כי האיסוף הוא באטצ׳ מתוזמן, לא
                בקשת משתמש.
              </Caveat>
            )}
          </div>
        ) : (
          <Missing />
        )}
      </Panel>
    </div>
  );
}
