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
  { id: "discovery", label_he: "גילוי" },
  { id: "identity", label_he: "זהות ודה־דופליקציה" },
  { id: "extract", label_he: "עץ החילוץ" },
  { id: "failure", label_he: "כשל, קצב וניטור" },
];

interface Props {
  facts: Facts | null;
}

/**
 * Module: how articles actually get in.
 *
 * Everything here describes src/crawling/ as written — requests + feedparser
 * + BeautifulSoup/lxml. There is no headless browser in the article path and
 * no crawler framework; saying otherwise on a wall in front of a panel would
 * be the one unforced error this whole demo is built to avoid.
 */
export function ScrapingModule({ facts }: Props) {
  const [tab, setTab] = useState("discovery");
  const c = facts?.constants;

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <SubNav tabs={TABS} active={tab} onSelect={setTab} />
      {tab === "discovery" && <Discovery facts={facts} />}
      {tab === "identity" && <Identity facts={facts} />}
      {tab === "extract" && <Extract facts={facts} />}
      {tab === "failure" && <Failure c={c} />}
    </div>
  );
}

/* ── 1. discovery ───────────────────────────────────────────────── */

function Discovery({ facts }: Props) {
  const sources = facts?.sources ?? [];
  const maxArticles = Math.max(1, ...sources.map((s) => s.articles));

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[46%_1fr] gap-3">
      <Panel title="שני מסלולי גילוי — לא אחד" hint="src/crawling/registry.py">
        <div className="flex flex-col gap-4">
          <div className="flex items-stretch gap-2">
            <Node
              title="RSS / feedparser"
              tone="accent"
              wide
              sub={
                <>
                  חמישה מקורות מפרסמים פיד. הפיד נמשך, נפרסר, וכל
                  <code dir="ltr" className="mx-1 font-mono">
                    entry.link
                  </code>
                  נאסף. קישור שכבר נראה בפיד אחר נזרק — מקור אחד מפרסם את אותה
                  כתבה בכמה פידים.
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
                  לרשת 13 אין פיד. הגילוי מושך את דף הניוזפיד, חולץ את בלוב
                  ה־JSON של Next.js, ומטייל בו רקורסיבית אחרי כל מחרוזת שמכילה
                  <code dir="ltr" className="mx-1 font-mono">
                    /item/news/newsfeed/article-
                  </code>
                </>
              }
            />
          </div>

          <div className="flex items-center justify-center gap-1">
            <Node title="רשימת כתובות" tone="good" />
            <Arrow label="ללא כפילויות" />
            <Node title="seen: set" mono />
          </div>

          <Caveat>
            הגילוי הוא רשימת פידים קבועה בקוד, לא סריקה של האתר. כתבה שלא עברה
            בפיד — המערכת לא תגלה אותה. זה מה שמחליף כאן זחילה על עץ הקישורים:
            החלטה, לא מגבלה טכנית.
          </Caveat>
        </div>
      </Panel>

      <Panel
        title="מה כל מקור באמת החזיר בסנאפשוט הזה"
        hint="פידים רשומים ← כתבות בפועל"
      >
        <div className="flex h-full flex-col gap-2 overflow-auto pe-1">
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
                {s.articles === 0 && <Chip tone="bad">0 כתבות בסנאפשוט</Chip>}
              </div>
              <BarRow
                label={s.id}
                n={s.articles}
                max={maxArticles}
                tone={s.articles === 0 ? "muted" : "accent"}
                note={
                  s.articles > 0
                    ? `${s.avg_chars.toLocaleString("en-US")} תווים בממוצע`
                    : undefined
                }
              />
            </div>
          ))}
          {sources.length === 0 && (
            <p className="text-[15.5px] text-[var(--dk-ink-3)]">
              קובץ המדידות לא נטען — הדיאגרמות למעלה עדיין תקפות.
            </p>
          )}
        </div>
      </Panel>
    </div>
  );
}

/* ── 2. identity ────────────────────────────────────────────────── */

function Identity({ facts }: Props) {
  const ex = facts?.identity_example;
  const params = facts?.constants.canonical.tracking_params ?? [];

  return (
    <div className="grid min-h-0 flex-1 grid-rows-[auto_1fr] gap-3">
      <Panel
        title="מפתח הזהות: sha256 של הכתובת הקנונית"
        hint="src/common/canonical_url.py · src/common/hashing.py"
      >
        <div className="flex items-stretch justify-center gap-1">
          <Node title="URL גולמי" mono sub="כפי שהגיע מהפיד או משיתוף" />
          <Arrow label="https, host קטן, בלי / בסוף" />
          <Node title="canonicalize_url" mono tone="accent" />
          <Arrow label={`מסיר ${params.length} פרמטרי מעקב`} />
          <Node title="canonical_url" mono tone="accent" />
          <Arrow label="sha256" />
          <Node title="article_id" mono tone="good" sub="מפתח ראשי בטבלה" />
        </div>
      </Panel>

      <div className="grid min-h-0 grid-cols-[1fr_37%] gap-3">
        <Panel
          title="אותה כתבה, שתי כתובות — חושב עכשיו על נתון אמיתי"
          hint="לא דוגמה כתובה ביד: הסקריפט מלכלך כתובת מהסנאפשוט ומריץ את הקוד"
        >
          {ex ? (
            <div className="flex flex-col gap-2.5">
              <UrlRow label="נקייה" url={ex.clean_url} />
              <UrlRow label="משותפת בוואטסאפ" url={ex.dirty_url} dirty />
              <div className="text-center text-lg text-[var(--dk-ink-3)]">
                ↓
              </div>
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
                  ולכן לאותו מזהה — וזה בדיוק המזהה השמור בטבלה:
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
            <p className="text-[15.5px] text-[var(--dk-ink-3)]">
              אין קובץ מדידות — הדוגמה המחושבת אינה זמינה.
            </p>
          )}
        </Panel>

        <div className="flex min-h-0 flex-col justify-center gap-3">
          <Panel title="מה נמחק מהכתובת" hint="TRACKING_PARAMS">
            <div className="flex flex-wrap gap-1.5">
              {params.map((p) => (
                <code
                  key={p}
                  dir="ltr"
                  className="rounded-md bg-[var(--dk-surface-2)] px-2 py-1 font-mono text-[13.5px] text-[var(--dk-ink-2)] line-through decoration-[var(--dk-bad)]/70"
                >
                  {p}
                </code>
              ))}
            </div>
          </Panel>

          <Panel title="למה הבדיקה קודמת להורדה">
            <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
              <code dir="ltr" className="font-mono text-[14.5px]">
                check_and_add
              </code>{" "}
              תופס את המזהה בבדיקה אטומית אחת <b>לפני</b> ההורדה, לא אחרי
              השמירה. זה מה שהופך את הריצה לבטוחה כששני מקורות עובדים במקביל על
              אותו מאגר מזהים, וזה גם מה שהופך הרצה חוזרת לחסרת נזק — כתבה מוכרת
              לא נמשכת שוב בכלל.
            </p>
          </Panel>
        </div>
      </div>
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

/* ── 3. extraction ladder ───────────────────────────────────────── */

function Extract({ facts }: Props) {
  const minLen = facts?.constants.extract.min_len ?? 100;
  const minPara = facts?.constants.extract.min_paragraph_len ?? 30;
  const haaretz = facts?.sources.find((s) => s.id === "haaretz");
  const ynet = facts?.sources.find((s) => s.id === "ynet");

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[52%_1fr] gap-3">
      <Panel
        title="עץ ההחלטות של חילוץ הטקסט"
        hint="src/crawling/extractors.py"
      >
        <Ladder
          rungs={[
            {
              label: "JSON-LD · NewsArticle.articleBody",
              tone: "good",
              detail: (
                <>
                  הנתון המובנה שהאתר עצמו מפרסם לגוגל. הכי אמין — זה הטקסט
                  שהעורך התכוון אליו, בלי פרסומות ובלי תפריטים.
                </>
              ),
              fallsThroughWhen: `אין תגית, או שהגוף קצר מ־${minLen} תווים`,
            },
            {
              label: "DOM · selectors ייעודיים לאתר",
              tone: "neutral",
              detail: (
                <>
                  רשימת selectors לפי מקור, לפי הסדר. ה־selector הראשון שמחזיר
                  פסקאות מנצח; פסקה קצרה מ־{minPara} תווים נזרקת — ככה נופלות
                  שורות קרדיט, כיתובים ותגיות.
                </>
              ),
              fallsThroughWhen: `אף selector לא הניב ${minLen} תווים`,
            },
            {
              label: "og:description",
              tone: "bad",
              detail: (
                <>
                  תקציר המטא של הדף. פסקה אחת, לא כתבה — נשמר כדי שכתבה חסומה לא
                  תיעלם לגמרי, אבל זה כישלון מוסווה, לא הצלחה.
                </>
              ),
              fallsThroughWhen: `גם זה מתחת ל־${minLen}`,
            },
            {
              label: "ValueError → נספר כ־failed",
              tone: "bad",
              detail: (
                <>
                  הכתבה לא נשמרת, המזהה נשאר תפוס, והריצה ממשיכה למקור הבא.
                  קרולר לא קורס בגלל כתבה אחת.
                </>
              ),
            },
          ]}
        />
      </Panel>

      <div className="flex min-h-0 flex-col justify-center gap-3">
        <Panel
          title="השכבה השלישית באמת נדלקת — והמדידה מסגירה אותה"
          hint="אורך טקסט ממוצע לפי מקור"
        >
          {haaretz && ynet ? (
            <div className="flex flex-col gap-3">
              <div className="flex items-end gap-3">
                <BigStat
                  label={ynet.source_he}
                  value={ynet.avg_chars.toLocaleString("en-US")}
                  sub={`עד ${ynet.max_chars.toLocaleString("en-US")} תווים`}
                  tone="good"
                />
                <BigStat
                  label={haaretz.source_he}
                  value={haaretz.avg_chars.toLocaleString("en-US")}
                  sub={`המקסימום כולו ${haaretz.max_chars} תווים`}
                  tone="bad"
                />
              </div>
              <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
                אצל <b>{haaretz.source_he}</b> אף כתבה בסנאפשוט לא עוברת את{" "}
                {haaretz.max_chars} תווים. זו לא כתיבה תמציתית — זה חתימת האורך
                של <code dir="ltr">og:description</code>. גוף הכתבה מאחורי
                תשלום, שתי השכבות הראשונות נופלות, והמערכת שומרת את התקציר.
              </p>
              <Caveat>
                כל מסקנה על {haaretz.source_he} בהמשך המצגת מבוססת על פסקה אחת
                לכתבה, לא על הכתבה. זו הסיבה שהרווח בר־הסמך שלו רחב ולא מובהק —
                המגבלה הזו מגיעה עד הסטטיסטיקה.
              </Caveat>
            </div>
          ) : (
            <p className="text-[15.5px] text-[var(--dk-ink-3)]">
              אין קובץ מדידות.
            </p>
          )}
        </Panel>

        <Panel title="למה לא דפדפן חסר־ראש לכל כתבה">
          <p className="text-[15.5px] leading-relaxed text-[var(--dk-ink-2)]">
            מסלול הכתבות הוא <CodeRef path="requests" /> +{" "}
            <CodeRef path="lxml" /> בלבד — בלי הרצת JavaScript. דפדפן היה פותר
            את שכבת ה־DOM אצל חלק מהמקורות, במחיר של סדר גודל בזמן ובזיכרון לכל
            כתבה. Playwright כן מותקן בפרויקט, ומופעל במקום אחד ויחיד: איסוף
            התגובות של {haaretz?.source_he ?? "הארץ"}, שם אין דרך אחרת.
          </p>
        </Panel>
      </div>
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

/* ── 4. failure & pacing ────────────────────────────────────────── */

function Failure({ c }: { c: Facts["constants"] | undefined }) {
  const attempts = c?.retry.max_attempts ?? 3;
  const backoff = c?.retry.backoff_sequence_s ?? [2, 4];
  const delay = c?.crawl.delay_seconds ?? 2;
  const minDisc = c?.crawl.min_discovered_for_alert ?? 5;
  const thresh = c?.crawl.failure_rate_threshold ?? 0.3;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-3 gap-3">
      <Panel title="מה שווה לנסות שוב" hint="src/crawling/retry.py">
        <div className="flex flex-col gap-2.5">
          <div className="flex flex-col gap-2">
            <Node
              title="timeout · connection · 5xx"
              mono
              tone="accent"
              sub={`חולף מטבעו — עד ${attempts} ניסיונות, המתנה ${backoff.map((b) => `${b}s`).join(" ואז ")}`}
            />
            <Node
              title="4xx · כל שאר החריגות"
              mono
              tone="bad"
              sub="נזרק מיד, בלי ניסיון חוזר"
            />
          </div>
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            ההבחנה היא לא זהירות — היא חיסכון. כתובת שהחזירה 404 תחזיר 404 גם
            בעוד שש שניות; ניסיון חוזר עליה קונה רק עיכוב. השרת שנפל תחת עומס
            דווקא יענה, אם נחכה.
          </p>
        </div>
      </Panel>

      <Panel title="קצב — סדרתי, בכוונה" hint="src/crawling/base.py">
        <div className="flex flex-col gap-2.5">
          <div className="flex items-center justify-center gap-1">
            <Node title="כתבה" tone="neutral" />
            <Arrow label={`${delay}s`} />
            <Node title="כתבה" tone="neutral" />
            <Arrow label={`${delay}s`} />
            <Node title="כתבה" tone="neutral" />
          </div>
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            אין באטצ׳ים מקביליים בתוך מקור. לולאה אחת, השהיה של {delay} שניות
            בין כתבה לכתבה. זו החלטה כפולה: נימוס כלפי אתר חדשות שלא ביקש את
            התנועה הזו, ושמירה על דטרמיניזם — סדר הכתיבה לבסיס הנתונים זהה בכל
            ריצה.
          </p>
          <Caveat>
            המחיר הוא זמן: מקור עם 200 כתבות חדשות לוקח לפחות{" "}
            {Math.round((200 * delay) / 60)} דקות רק בהשהיות. זה מתקבל כי הריצה
            היא באטצ׳ מתוזמן כל 6 שעות, לא בקשת משתמש.
          </Caveat>
        </div>
      </Panel>

      <Panel title="מתי הריצה מתלוננת" hint="check_failure_rate_spike">
        <div className="flex flex-col gap-2.5">
          <div
            dir="ltr"
            className="rounded-lg border border-[var(--dk-accent)]/25 bg-[var(--dk-accent-dim)]/40 px-3 py-2 text-center font-mono text-[15.5px] text-[var(--dk-accent)]"
          >
            failed / (saved + failed) &gt; {thresh}
          </div>
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            המכנה הוא מה ש<b>נוסה</b>, לא מה שנתגלה: כתבות שדולגו ככפילות מעולם
            לא נמשכו, וספירתן הייתה מדללת כל זינוק אמיתי בכשלים דווקא בריצות
            שבהן רוב הפיד כבר מוכר.
          </p>
          <p className="text-[15px] leading-relaxed text-[var(--dk-ink-2)]">
            והתראה נשלחת רק אם התגלו לפחות {minDisc} כתבות — בפיד של שתיים,
            כישלון בודד הוא 50% ואין בו שום מידע.
          </p>
          <Caveat>
            זו אזהרה ביומן, לא עצירה. אם מקור משנה מבנה, הריצה נמשכת ורק הלוג
            יודע. אין כאן התראה שמגיעה לטלפון של אף אחד.
          </Caveat>
        </div>
      </Panel>
    </div>
  );
}
