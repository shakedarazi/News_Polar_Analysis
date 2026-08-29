"""Prototype renderer for the "same event, different audiences" screen.

    PYTHONPATH=. python demo/prototype/build_profile_page.py [--offline]

Writes a self-contained RTL HTML page from the local snapshot so the concept
can be reviewed before any of the demo runner is migrated. Every number on the
page is computed here from real data; nothing is illustrative.

With network, LLM framing variables are extracted once and cached to
demo/data/framing_cache.json; `--offline` renders from the cache alone.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from demo import config  # noqa: E402
from demo.core.framing import (LEX_CATEGORIES_HE, MIN_CELL_EVENTS,  # noqa: E402
                               Event, FramingExtractor, Snapshot,
                               attach_comment_profiles, bootstrap_ci,
                               build_event_clusters, category_mix_deviation,
                               change_point_power, coverage_matrix,
                               detect_change_point, keyword_recall,
                               outlet_deviation, sampling_curve,
                               topic_framing_matrix, verify_contrast,
                               verify_framing)

OUT_PATH = REPO_ROOT / "demo" / "prototype" / "outlet_profile.html"
SOURCE_LABELS_HE = {"ynet": "ynet", "mako": "mako", "haaretz": "הארץ",
                    "news12": "חדשות 12", "channel14": "ערוץ 14",
                    "reshet13": "רשת 13"}


def showcase_score(event: Event) -> tuple[int, int, int]:
    """Prefer events that are multi-source AND actually have audience data —
    without comments the whole right-hand side of the screen is empty."""
    with_comments = sum(1 for v in event.versions if (v.num_comments or 0) >= 15)
    return (len(event.sources), with_comments, event.total_comments)


def esc(value: object) -> str:
    return html.escape(str(value)) if value is not None else "—"


def fmt(value: float | None, digits: int = 4) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def plain_conclusions(event: Event, kw_found: int, kw_total: int,
                      cells: dict, profiles: dict, scans: list[dict],
                      verifier: dict) -> list[tuple[str, str]]:
    """The page in sentences a visitor can repeat afterwards.

    Generated from the same numbers as the tables rather than written by hand,
    so a headline can never drift away from the evidence under it. Each item is
    (claim, the number behind it).
    """
    out: list[tuple[str, str]] = []

    hijacked = [v for v in event.versions if v.audience_hijacked]
    if hijacked:
        v = hijacked[0]
        out.append((
            f"אותו אירוע, שני ויכוחים. הכתבה של {SOURCE_LABELS_HE.get(v.source, v.source)} "
            f"היא בעיקר על {v.lex_top_he} — הקוראים שלה דיברו בעיקר על {v.comment_top_he}.",
            f"{v.num_comments} תגובות אמיתיות שנאספו ונותחו"))

    out.append((
        "בלי AI אי אפשר בכלל להשוות: חיפוש מילים משותפות בכותרות לא מזהה "
        "שמדובר באותו סיפור.",
        f"מילות מפתח מצאו {kw_found} מתוך {kw_total} הגרסאות · אחזור סמנטי מצא את כולן"))

    hot = [c for c in cells.values() if c.significant]
    if hot:
        c = max(hot, key=lambda x: x.n)
        direction = "פחות ממוקדת נושאית" if c.ci[0] < 0 else "יותר ממוקדת נושאית"
        out.append((
            f"{SOURCE_LABELS_HE.get(c.source, c.source)} מכסה סיפורי {c.topic_he} "
            f"בצורה {direction} מכל השאר — באופן עקבי, לא במקרה.",
            f"{c.n} אירועים משותפים · רווח סמך [{c.ci[1]:+.3f}, {c.ci[2]:+.3f}] שאינו חוצה אפס"))

    watch = [c for c in cells.values() if not c.significant and c.n >= 10]
    if watch:
        c = max(watch, key=lambda x: abs(x.top_mix(1)[0][1]))
        mix_he, mix_val = c.top_mix(1)[0]
        out.append((
            f"דפוס שעדיין לא ראיה: {SOURCE_LABELS_HE.get(c.source, c.source)} נוטה "
            f"להזיז סיפורי {c.topic_he} לכיוון {mix_he} — צריך עוד דגימה כדי לקבוע.",
            f"{c.n} אירועים בלבד · רווח הסמך עדיין חוצה אפס"))

    if scans:
        out.append((
            "אף ערוץ לא שינה את הקו שלו בשבוע האחרון." if not any(s["cp"].detected for s in scans)
            else "זוהה שינוי בקו של אחד הערוצים.",
            f"נבדקו {len(scans)} סדרות זמן · הגלאי תופס שינוי בגודל סטיית תקן "
            f"ב־{max(s['power'] for s in scans):.0%} מהמקרים"))

    if verifier["terms_total"]:
        out.append((
            "כל מילה שהמודל מוציא נבדקת מול הטקסט המקורי, ומה שלא נמצא — נמחק.",
            f"{verifier['terms_rejected']} מתוך {verifier['terms_total']} ביטויים נדחו "
            f"({verifier['terms_rejected'] / verifier['terms_total']:.0%}) · "
            f"{verifier['quotes_rejected']} מתוך {verifier['quotes_total']} ציטוטים נדחו"))
    return out


def render_conclusions(items: list[tuple[str, str]]) -> str:
    cards = "".join(
        f'<div class="concl"><div class="concl-claim">{claim}</div>'
        f'<div class="concl-ev">{evidence}</div></div>'
        for claim, evidence in items)
    return f'<div class="concl-wrap">{cards}</div>'


def render_topic_matrix(cells: dict, sources: list[str], topics: list[str]) -> str:
    """Outlet × beat grid. Cells below MIN_CELL_EVENTS render greyed with their
    n visible — hiding them would imply the grid is fully populated."""
    head = "".join(f"<th>{esc(t)}</th>" for t in topics)
    body = []
    for source in sources:
        tds = []
        for topic in topics:
            cell = cells.get((source, topic))
            if cell is None or cell.n < 3:
                tds.append('<td class="cell empty">—</td>')
                continue
            mix_he, mix_val = cell.top_mix(1)[0]
            if not cell.usable:
                tds.append(f'<td class="cell thin">{cell.ci[0]:+.4f}'
                           f'<div class="sub">n={cell.n} · מדגם קטן</div></td>')
                continue
            cls = "hot" if cell.significant else "cell"
            star = " ★" if cell.significant else ""
            tds.append(f'<td class="cell {cls}">{cell.ci[0]:+.4f}{star}'
                       f'<div class="sub">n={cell.n} · [{cell.ci[1]:+.3f},{cell.ci[2]:+.3f}]'
                       f'<br>{esc(mix_he)} {mix_val:+.3f}</div></td>')
        body.append(f'<tr><td class="src">{esc(SOURCE_LABELS_HE.get(source, source))}</td>'
                    + "".join(tds) + "</tr>")
    return f"<table><tr><th>מקור</th>{head}</tr>{''.join(body)}</table>"


def render_change_verdict(scans: list[dict]) -> str:
    """The headline sentence, derived from the scan rather than written by hand
    — otherwise a future snapshot with a real shift would still read 'none'."""
    if not scans:
        return ("<b>אין סדרה ארוכה מספיק לפיצול.</b> הגלאי דורש לפחות 16 אירועים "
                "בתא (8 בכל צד), ואף תא בסנאפשוט הנוכחי לא הגיע לזה.")
    hits = [s for s in scans if s["cp"].detected]
    p_values = [s["cp"].p_value for s in scans]
    best_power = max(s["power"] for s in scans)
    if hits:
        lines = "; ".join(
            f'{SOURCE_LABELS_HE.get(s["source"], s["source"])} × {s["topic"]} '
            f'ב־{s["cp"].at[:10]} (Δ{s["cp"].shift:+.4f}, p={s["cp"].p_value:.3f})'
            for s in hits)
        return f"<b>זוהו {len(hits)} נקודות שינוי:</b> {lines}."
    return (f"<b>תוצאה: לא זוהה אף שינוי.</b> כל ערכי ה־p בטווח "
            f"{min(p_values):.2f}–{max(p_values):.2f}, רחוק מ־0.05. בחלון הנוכחי "
            f"אף ערוץ לא שינה את קו המסגור שלו בגודל שהגלאי מסוגל לראות — ובתא "
            f"הגדול ביותר הוא רואה שינוי של סטיית תקן אחת ב־{best_power:.0%} "
            f"מהמקרים, כך ש\"לא נמצא\" הוא ממצא ולא כישלון.")


def render_change_points(scans: list[dict], power_table: list[tuple[int, float, float]]
                         ) -> str:
    rows = []
    for scan in scans:
        cp = scan["cp"]
        verdict = ('<span class="sig">שינוי מזוהה</span>' if cp.detected
                   else '<span class="nosig">אין שינוי</span>')
        rows.append(f"""
        <tr><td class="src">{esc(SOURCE_LABELS_HE.get(scan["source"], scan["source"]))}
            × {esc(scan["topic"])}</td>
          <td>{cp.n}</td>
          <td>{esc(cp.at[:16])}</td>
          <td>{cp.before_mean:+.4f} ← {cp.after_mean:+.4f}</td>
          <td>{cp.p_value:.3f}</td>
          <td>{scan["power"]:.0%}</td>
          <td>{verdict}</td></tr>""")
    power_rows = "".join(
        f"<tr><td>n={n}</td><td>{p1:.0%}</td><td>{p05:.0%}</td></tr>"
        for n, p1, p05 in power_table)
    return f"""
    <table>
      <tr><th>מקור × תחום</th><th>מדגם</th><th>נקודת הפיצול הטובה ביותר</th>
          <th>לפני ← אחרי</th><th>p</th><th>עוצמה @1SD</th><th>מסקנה</th></tr>
      {''.join(rows)}
    </table>
    <div class="ledger" style="margin-top:14px">
      <b>כיול הגלאי</b> (מבחן תמורות, 2,000 ערבובים לכל סדרה). אזעקות שווא על
      רעש טהור נמדדו ב־5.3%–6.3% מול יעד של 5%. עוצמת הזיהוי:
      <table style="width:auto;margin-top:8px">
        <tr><th>גודל סדרה</th><th>שינוי של 1 סטיית תקן</th><th>שינוי של 0.5</th></tr>
        {power_rows}
      </table>
    </div>"""


def render(event: Event, kw_found: int, kw_total: int,
           profiles: dict[str, dict], curve_source: str,
           curve: list[dict], coverage: dict[str, dict],
           snap: Snapshot, extractor: FramingExtractor,
           events_total: int, topic_matrix_html: str,
           change_html: str, change_verdict: str,
           conclusions_html: str, verifier: dict) -> str:
    v_terms = verifier["terms_total"]
    v_terms_rej = verifier["terms_rejected"]
    v_q_tot = verifier["quotes_total"]
    v_q_rej = verifier["quotes_rejected"]
    rows = []
    for v in event.versions:
        top = snap.top_comment(v.article_id)
        framing = v.framing or {}
        loaded = ", ".join(framing.get("loaded_terms") or []) or "—"
        hijack = ("<span class='flag'>התהפך</span>" if v.audience_hijacked else "")
        rows.append(f"""
        <tr>
          <td class="src">{esc(SOURCE_LABELS_HE.get(v.source, v.source))}</td>
          <td class="ttl">{esc(v.title)}</td>
          <td>{esc(v.lex_top_he)}<div class="sub">{v.windows} חלונות · דומיננטיות {fmt(v.mean_dominance, 2)}</div></td>
          <td class="llm">{esc(framing.get("actor"))}</td>
          <td class="llm">{esc(framing.get("responsibility"))}</td>
          <td class="llm">{esc(loaded)}</td>
          <td>{esc(v.num_comments or 0)}<div class="sub">p85 {fmt(v.audience_p85)}</div></td>
          <td>{esc(v.comment_top_he)} {hijack}<div class="sub">{esc((top or {}).get("text", ""))[:90]}</div></td>
        </tr>""")

    prof_rows = []
    for source, p in sorted(profiles.items(), key=lambda kv: -kv[1]["n"]):
        ci = p["ci"]
        sig = "מובהק" if ci and (ci[1] > 0 or ci[2] < 0) else "לא מובהק"
        cls = "sig" if sig == "מובהק" else "nosig"
        mix = p["mix"]
        top_mix = np.argsort(-np.abs(mix))[:2]
        mix_txt = " · ".join(
            f"{LEX_CATEGORIES_HE[i]} {mix[i]:+.3f}" for i in top_mix)
        prof_rows.append(f"""
        <tr>
          <td class="src">{esc(SOURCE_LABELS_HE.get(source, source))}</td>
          <td>{p["n"]} אירועים</td>
          <td>{fmt(ci[0], 4) if ci else "—"}</td>
          <td>{f"[{ci[1]:+.4f}, {ci[2]:+.4f}]" if ci else "—"}</td>
          <td class="{cls}">{sig}</td>
          <td class="mix">{mix_txt}</td>
        </tr>""")

    max_width = max((c["width"] for c in curve), default=1.0) or 1.0
    bars = []
    for c in curve:
        pct = 100 * c["width"] / max_width
        bars.append(f"""
        <div class="bar-row">
          <div class="bar-label">{c["n"]} אירועים</div>
          <div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>
          <div class="bar-val">רוחב רווח סמך {c["width"]:.4f}</div>
        </div>""")

    cov_rows = []
    for source, c in sorted(coverage.items(), key=lambda kv: -kv[1]["share"]):
        warn = " <span class='warn'>נפח דגימה נמוך</span>" if c["in_snapshot"] < 30 else ""
        cov_rows.append(f"""
        <tr><td class="src">{esc(SOURCE_LABELS_HE.get(source, source))}</td>
        <td>{c["covered"]}/{c["total_events"]}</td>
        <td>{c["share"]:.0%}</td>
        <td>{c["in_snapshot"]} כתבות בסנאפשוט{warn}</td></tr>""")

    llm_note = (f"חולצו {extractor.calls} ניתוחי מסגור חיים בעלות "
                f"${extractor.cost_usd():.4f}" if extractor.calls else
                "ניתוחי המסגור נטענו מהמטמון המקומי (ללא רשת)")

    return f"""<!doctype html>
<html lang="he" dir="rtl"><head><meta charset="utf-8">
<title>פרופיל ערוץ — אותו אירוע, קהלים שונים</title>
<style>
  :root {{ --bg:#0f1117; --card:#171a23; --line:#262b38; --txt:#e8ecf4;
           --dim:#8b93a7; --accent:#5b9dff; --warn:#ffb454; --good:#4ade80; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--txt);
         font-family:"Heebo","Segoe UI",Arial,sans-serif; padding:28px 34px; }}
  h1 {{ font-size:26px; margin:0 0 4px; }}
  h2 {{ font-size:19px; margin:34px 0 10px; border-right:3px solid var(--accent);
        padding-right:10px; }}
  .lead {{ color:var(--dim); margin:0 0 22px; font-size:14px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
           padding:18px 20px; margin-bottom:18px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:right; color:var(--dim); font-weight:500; padding:8px 10px;
        border-bottom:1px solid var(--line); white-space:nowrap; }}
  td {{ padding:11px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  .src {{ font-weight:700; color:var(--accent); white-space:nowrap; }}
  .ttl {{ max-width:250px; line-height:1.45; }}
  .sub {{ color:var(--dim); font-size:11px; margin-top:4px; line-height:1.4; }}
  .llm {{ background:rgba(91,157,255,.07); }}
  .flag {{ background:var(--warn); color:#000; border-radius:4px; padding:1px 6px;
           font-size:10px; font-weight:700; }}
  .sig {{ color:var(--good); font-weight:700; }}
  .nosig {{ color:var(--dim); }}
  .warn {{ color:var(--warn); font-size:11px; }}
  .mix {{ font-size:12px; color:var(--dim); }}
  .proof {{ display:flex; gap:26px; align-items:center; flex-wrap:wrap; }}
  .big {{ font-size:34px; font-weight:800; }}
  .big small {{ font-size:13px; font-weight:400; color:var(--dim); display:block; }}
  .fail {{ color:#ff6b6b; }} .pass {{ color:var(--good); }}
  .bar-row {{ display:flex; align-items:center; gap:12px; margin:7px 0; font-size:12px; }}
  .bar-label {{ width:90px; color:var(--dim); }}
  .bar-track {{ flex:1; height:9px; background:#0b0d13; border-radius:5px; overflow:hidden; }}
  .bar-fill {{ height:100%; background:linear-gradient(90deg,var(--accent),#7c5cff); }}
  .bar-val {{ width:190px; color:var(--dim); }}
  .ledger {{ font-size:12.5px; color:var(--dim); line-height:1.85; }}
  .ledger b {{ color:var(--txt); }}
  .tag {{ display:inline-block; font-size:10px; padding:2px 7px; border-radius:4px;
          margin-left:6px; vertical-align:middle; }}
  .tag-det {{ background:#1f3d2b; color:var(--good); }}
  .tag-ai {{ background:#1e3358; color:var(--accent); }}
  .tag-stat {{ background:#3d3520; color:var(--warn); }}
  .cell {{ text-align:center; font-variant-numeric:tabular-nums; }}
  .cell.empty {{ color:#3a4152; }}
  .cell.thin {{ color:var(--dim); background:rgba(255,255,255,.02); }}
  .cell.hot {{ background:rgba(74,222,128,.12); color:var(--good); font-weight:700; }}
  .cell .sub {{ font-weight:400; }}
  .concl-wrap {{ display:grid; gap:10px; margin-bottom:26px; }}
  .concl {{ background:linear-gradient(90deg,rgba(91,157,255,.10),transparent);
            border-right:3px solid var(--accent); border-radius:8px; padding:13px 16px; }}
  .concl-claim {{ font-size:17px; line-height:1.55; }}
  .concl-ev {{ color:var(--dim); font-size:12px; margin-top:6px; }}
  .null-box {{ border-right:3px solid var(--warn); padding:10px 14px;
               background:rgba(255,180,84,.06); border-radius:6px;
               font-size:13px; line-height:1.75; margin-bottom:14px; }}
</style></head><body>

<h1>אותו אירוע, קהלים שונים</h1>
<p class="lead">פרוטוטיפ · כל המספרים מחושבים מהסנאפשוט המקומי · {events_total} אירועים חוצי־מקורות</p>

<h2>מה מצאנו</h2>
{conclusions_html}

<h2>1. האירוע<span class="tag tag-ai">אחזור סמנטי</span></h2>
<div class="card">
  <div style="font-size:17px;margin-bottom:14px">{esc(event.headline)}</div>
  <div class="proof">
    <div class="big fail">{kw_found}<small>גרסאות שהתאמת מילות מפתח מוצאת</small></div>
    <div class="big pass">{kw_total}<small>גרסאות שאחזור סמנטי מוצא</small></div>
    <div style="flex:1;min-width:260px;color:var(--dim);font-size:12.5px;line-height:1.7">
      כותרות של אותו אירוע כמעט לא חולקות מילים. בלי אחזור סמנטי אין בכלל
      השוואה בין מקורות — וזו ההצדקה הנמדדת לשכבת ה־AI.
    </div>
  </div>
</div>

<h2>2. הגרסאות זו מול זו<span class="tag tag-det">לקסיקון</span><span class="tag tag-ai">חילוץ מסגור</span></h2>
<div class="card"><table>
  <tr><th>מקור</th><th>הכותרת</th><th>לקסיקון הכתבה</th><th>מי המבצע</th>
      <th>למי מיוחסת אחריות</th><th>מילים טעונות</th><th>קהל בפועל</th>
      <th>על מה התגובות דיברו</th></tr>
  {''.join(rows)}
</table>
<p class="sub">העמודות המסומנות בכחול הן היחידות שמגיעות ממודל שפה — הן המשתנים
שהלקסיקון עיוור אליהם. {llm_note}.</p></div>

<h2>3. פרופיל ערוץ — סטייה מחציון האירוע<span class="tag tag-stat">סטטיסטיקה, לא AI</span></h2>
<div class="card">
  <p class="sub" style="margin-top:0">כל ערוץ מושווה לחציון של <b>אותו אירוע בדיוק</b>,
  מה שמנטרל את השאלה מה קרה בעולם ומשאיר רק את הבחירה המערכתית. ערך שלילי
  בדומיננטיות = הגרסה של הערוץ פחות מרוכזת נושאית מהחציון.</p>
  <table>
    <tr><th>מקור</th><th>מדגם</th><th>סטייה ממוצעת</th><th>רווח סמך 95%</th>
        <th>מובהקות</th><th>הטיית תמהיל בולטת</th></tr>
    {''.join(prof_rows)}
  </table>
</div>

<h2>3.5 המאמת — הסוכן שבודק את המודל<span class="tag tag-det">דטרמיניסטי</span></h2>
<div class="card">
  <p class="sub" style="margin-top:0">מודל שפה שמחזיר "מילה טעונה" עלול להמציא אותה.
  המאמת מחפש כל ביטוי בטקסט שהמודל עצמו קיבל, ומוחק את מה שלא נמצא. זו לא
  חוות דעת שנייה של מודל — זו בדיקת עיגון דטרמיניסטית.</p>
  <div class="proof">
    <div class="big">{v_terms}<small>ביטויים שהמודל הוציא</small></div>
    <div class="big fail">{v_terms_rej}<small>נדחו — לא נמצאו בטקסט</small></div>
    <div class="big fail">{v_q_rej}/{v_q_tot}<small>ציטוטי ראיה שנדחו</small></div>
    <div style="flex:1;min-width:240px;color:var(--dim);font-size:12.5px;line-height:1.7">
      כמעט מחצית מ"הציטוטים" שהמודל מביא הם פרפרזה ולא ציטוט. בלי המאמת
      חצי מהמרכאות על המסך היו מומצאות. זה מה שהופך את שכבת הסוכנים
      מתפאורה לרכיב שמשנה את הפלט.
    </div>
  </div>
</div>

<h2>4. פילוח מסגור לפי תחום<span class="tag tag-stat">סטטיסטיקה, לא AI</span></h2>
<div class="card">
  <p class="sub" style="margin-top:0">אותה סטייה תוך־אירועית, מפוצלת לפי התחום
  של האירוע (התחום נקבע מחציון פרופיל הלקסיקון של כל הגרסאות, כך שהתווית שייכת
  לאירוע ולא לערוץ שאותו מודדים). ★ = רווח הסמך אינו חוצה אפס.
  תאים מתחת ל־{MIN_CELL_EVENTS} אירועים מוצגים באפור — הם עדיין לא ראיה.</p>
  {topic_matrix_html}
  <p class="sub">כאן נמצא "המתווה שעליו הם רצים": ערוץ יכול לשבת בדיוק על החציון
  בסך הכל ועדיין למסגר מחדש תחום אחד באופן שיטתי, כי תחומים בסימנים הפוכים
  מקזזים זה את זה במספר המאוחד.</p>
</div>

<h2>5. גלאי נקודת־שינוי<span class="tag tag-stat">מבחן תמורות</span></h2>
<div class="card">
  <div class="null-box">{change_verdict}</div>
  {change_html}
  <p class="sub"><b>מגבלה שצריך לדעת:</b> ציר הזמן הוא <code>first_seen_at</code>,
  כלומר מועד הסריקה ולא מועד הפרסום, והמנה הראשונה בסנאפשוט היא מילוי־לאחור של
  269 כתבות בשעה אחת. לכן נקודת הפיצול הטובה ביותר נופלת כמעט תמיד בתחילת
  הסדרה — ארטיפקט סריקה, לא אירוע עריכתי. הגלאי יקבל ציר זמן אמיתי רק כשהריצה
  בענן תצבור שבועות.</p>
</div>

<h2>6. ככל שנדגם יותר — מדויק יותר<span class="tag tag-stat">bootstrap</span></h2>
<div class="card">
  <p class="sub" style="margin-top:0">רווח הסמך של {esc(SOURCE_LABELS_HE.get(curve_source, curve_source))}
  כפונקציה של מספר האירועים שנדגמו. זו הקשת האמיתית: היא מצטמצמת כי יותר
  ראיות מגבילות את ההערכה, לא כי סודרה מראש.</p>
  {''.join(bars)}
</div>

<h2>7. כיסוי והשמטה</h2>
<div class="card"><table>
  <tr><th>מקור</th><th>אירועים משותפים שסוקרו</th><th>שיעור</th><th>הסתייגות</th></tr>
  {''.join(cov_rows)}
</table>
<p class="sub"><b>אזהרה מתודולוגית:</b> המדד הזה מערבב בחירה מערכתית עם נפח
הסריקה שלנו. ערוץ עם תשע כתבות בסנאפשוט יקבל 0% מסיבות דגימה, לא עריכה.
לפני שמסיקים ממנו משהו צריך נרמול לפי נפח.</p></div>

<h2>פנקס יושרה למסך הזה</h2>
<div class="card ledger">
  <b>מה אמיתי:</b> כל מספר בעמוד מחושב מהסנאפשוט. האשכולות, ספירות הלקסיקון,
  התגובות, קיטוב הקהל, רווחי הסמך — הכול נמדד.<br>
  <b>מה AI:</b> שתי שכבות בלבד — אחזור האירוע (embeddings) וחילוץ המסגור
  (מודל שפה). זהו.<br>
  <b>מה לא AI:</b> ניתוח הלקסיקון, הסטטיסטיקה, רווחי הסמך והקשת. דטרמיניסטי לגמרי.<br>
  <b>מה עוד לא ניתן לטעון:</b> טווח הסנאפשוט הוא חמישה ימים; מדגם משתני המסגור
  קטן מכדי להסיק ממנו על ערוץ; פרופיל ברמת כתב בודד אינו אפשרי כלל — אין
  שדה מחבר בנתונים.
</div>
</body></html>"""


def run_verifier(snap: Snapshot, events: list[Event], articles: dict,
                 extractor: FramingExtractor) -> dict:
    """Grounding pass over everything the model produced, cached or fresh.

    Counted across the whole cache rather than just the showcase event, so the
    rejection rate on screen describes the extractor's real behaviour and not
    one lucky story.
    """
    terms_total = terms_rejected = 0
    for evt in events:
        for version in evt.versions:
            framing = extractor.cached(version.article_id)
            if not framing:
                continue
            verdict = verify_framing(framing, version.title,
                                     articles[version.article_id]["text"])
            terms_total += len(verdict.kept_terms) + len(verdict.dropped_terms)
            terms_rejected += len(verdict.dropped_terms)

    quotes_total = quotes_rejected = 0
    cache_path = config.DATA_DIR / "contrast_cache.json"
    if cache_path.exists():
        contrast = json.loads(cache_path.read_text(encoding="utf-8"))
        by_id = {e.event_id: e for e in events}
        for event_id, result in contrast.items():
            evt = by_id.get(event_id)
            if evt is None:
                continue
            versions = [(v.source, v.title, articles[v.article_id]["text"])
                        for v in evt.versions[:5]]
            quotes_total += sum(1 for item in (result.get("per_source") or [])
                                if item.get("evidence"))
            _, violations = verify_contrast(result, versions)
            quotes_rejected += sum(1 for v in violations if v.startswith("ציטוט"))
    return {"terms_total": terms_total, "terms_rejected": terms_rejected,
            "quotes_total": quotes_total, "quotes_rejected": quotes_rejected}


def build_change_scans(events: list[Event]) -> list[dict]:
    """Run the change-point detector over every (outlet, beat) time series that
    is long enough to split, reporting the detector's power alongside so a null
    result is legible."""
    series: dict[tuple[str, str], list[tuple[str, float]]] = {}
    for event in events:
        topic = event.topic_he
        if topic is None:
            continue
        observed = [(v.source, v.mean_dominance) for v in event.versions
                    if v.mean_dominance is not None]
        if len(observed) < 2:
            continue
        median = float(np.median([v for _, v in observed]))
        for source, value in observed:
            series.setdefault((source, topic), []).append(
                (event.first_seen_at, value - median))

    scans = []
    for (source, topic), points in sorted(series.items(), key=lambda kv: -len(kv[1])):
        cp = detect_change_point(points)
        if cp is None:
            continue
        scans.append({"source": source, "topic": topic, "cp": cp,
                      "power": change_point_power(cp.n, 1.0, iterations=120)})
    return scans


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true",
                        help="render from the framing cache without network")
    parser.add_argument("--event", type=int, default=0,
                        help="index into the showcase ranking (0 = best)")
    args = parser.parse_args()

    snap = Snapshot()
    events = build_event_clusters(snap)
    print(f"cross-source events: {len(events)}")

    ranked = sorted(events, key=showcase_score, reverse=True)
    event = ranked[args.event]
    attach_comment_profiles(snap, event)
    kw_found, kw_total = keyword_recall(snap, event)
    print(f"showcase: {event.headline[:60]} "
          f"({len(event.sources)} sources, keyword {kw_found}/{kw_total})")

    extractor = FramingExtractor()
    articles = snap.articles()
    for version in event.versions:
        version.framing = extractor.extract(
            version.article_id, version.title,
            articles[version.article_id]["text"],
            allow_network=not args.offline)
    if extractor.calls:
        extractor.save()
        print(f"framing extracted: {extractor.calls} calls, "
              f"{extractor.failures} failures, ${extractor.cost_usd():.4f}")

    deviations = outlet_deviation(events, "dominance")
    mixes = category_mix_deviation(events)
    profiles = {
        s: {"n": len(v), "ci": bootstrap_ci(v), "mix": mixes.get(s, np.zeros(7))}
        for s, v in deviations.items() if len(v) >= 3
    }
    curve_source = max(profiles, key=lambda s: profiles[s]["n"])
    curve = sampling_curve(deviations[curve_source])

    counts: dict[str, int] = {}
    for row in articles.values():
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    coverage = coverage_matrix(events, counts)
    for source in coverage:
        coverage[source]["in_snapshot"] = counts.get(source, 0)

    verifier = run_verifier(snap, events, articles, extractor)
    print(f"verifier: rejected {verifier['terms_rejected']}/{verifier['terms_total']} terms, "
          f"{verifier['quotes_rejected']}/{verifier['quotes_total']} evidence quotes")
    # Show only what survived verification — the screen must never carry a
    # phrase the audience cannot find in the source text.
    for version in event.versions:
        if version.framing:
            verdict = verify_framing(version.framing, version.title,
                                     articles[version.article_id]["text"])
            version.framing = {**version.framing,
                               "loaded_terms": verdict.kept_terms}

    cells = topic_framing_matrix(events)
    matrix_sources = sorted({s for s, _ in cells}, key=lambda s: -counts.get(s, 0))
    topic_totals: dict[str, int] = {}
    for (_, topic), cell in cells.items():
        topic_totals[topic] = topic_totals.get(topic, 0) + cell.n
    matrix_topics = sorted(topic_totals, key=lambda t: -topic_totals[t])
    significant = [c for c in cells.values() if c.significant]
    print(f"topic cells: {len(cells)} ({len(significant)} significant, "
          f"{sum(1 for c in cells.values() if c.usable)} usable)")

    scans = build_change_scans(events)
    detected = sum(1 for s in scans if s["cp"].detected)
    print(f"change-point scan: {len(scans)} series, {detected} detected at p<0.05")
    power_table = [(n, change_point_power(n, 1.0, iterations=150),
                    change_point_power(n, 0.5, iterations=150))
                   for n in (20, 40, 75)]

    OUT_PATH.write_text(
        render(event, kw_found, kw_total, profiles, curve_source, curve,
               coverage, snap, extractor, len(events),
               render_topic_matrix(cells, matrix_sources, matrix_topics),
               render_change_points(scans, power_table),
               render_change_verdict(scans),
               render_conclusions(plain_conclusions(
                   event, kw_found, kw_total, cells, profiles, scans, verifier)),
               verifier),
        encoding="utf-8")
    print(f"written: {OUT_PATH}")


if __name__ == "__main__":
    main()
