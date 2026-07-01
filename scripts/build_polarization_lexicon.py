"""Build Hebrew polarization lexicon from Simchon et al. OSF source files."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.lexicon.expand_lexicon import expand_lexicon  # used in main() stats only

SOURCE_PATH = ROOT / "data" / "lexicon" / "source" / "dict_hclust.csv"
LEXICON_PATH = ROOT / "data" / "lexicon" / "polarization.csv"

# US-specific hashtags, slang, or low-relevance terms for Israeli news.
SKIP_STEMS = frozenset(
    {
        "tcot", "ccot", "ctot", "tgdn", "opslam", "lnyhbt", "rednationrising",
        "wakeupamerica", "gop", "potus", "nra", "gunsense", "gunrights",
        "guncontrol", "narps", "deniers", "alarmists", "sceptics", "skeptics",
        "cynics", "beneran", "dems", "repubs", "libs", "anti-abortion",
        "pro-gun", "anti-gun", "gun-control", "man-made", "manmade",
        "generational", "confiscation", "redistribution", "publichealth",
        "renewables", "globalwarming", "commonsense", "wakeupamerica",
        "buddhist", "hindu", "isis", "tgdn",
    }
)

# English stem -> Hebrew lemma (curated draft; review before production use).
STEM_TO_HEBREW: dict[str, str] = {
    "absolutely": "לגמרי",
    "accused": "הואשם",
    "amend": "תיקון",
    "amendment": "תיקון",
    "annoying": "מעצבן",
    "assholes": "מטומטמים",
    "attack": "תקיפה",
    "awful": "נורא",
    "bipartisan": "דו-מפלגתי",
    "blame": "אשמה",
    "bombing": "פיגוע",
    "broadcast": "שידור",
    "bs": "שטויות",
    "bullets": "כדורים",
    "bullshit": "שטויות",
    "capitalism": "קפיטליזם",
    "capitalist": "קפיטליסטי",
    "caught": "נתפס",
    "charge": "האשמה",
    "cheaters": "רמאים",
    "christians": "נוצרים",
    "citizens": "אזרחים",
    "claims": "טענה",
    "communism": "קומוניזם",
    "completely": "לחלוטין",
    "conservative": "שמרני",
    "constitution": "חוקה",
    "constitutional": "חוקתי",
    "corruption": "שחיתות",
    "crazy": "משוגע",
    "crime": "פשע",
    "criminal": "פושע",
    "crony": "מקורבים",
    "damn": "לעזאזל",
    "death": "מוות",
    "democracy": "דמוקרטיה",
    "democrat": "דמוקרט",
    "democratic": "דמוקרטי",
    "destroy": "להרוס",
    "devil": "שטן",
    "diaries": "יומן",
    "draconian": "דרקוני",
    "dumb": "טיפש",
    "dumbass": "טמבל",
    "dumbasses": "טמבלים",
    "enemy": "אויב",
    "except": "חוץ",
    "expose": "חשיפה",
    "extremism": "קיצוניות",
    "extremist": "קיצוני",
    "fault": "אשמה",
    "fear": "פחד",
    "firearms": "נשק",
    "fraud": "הונאה",
    "fuck": "לעזאזל",
    "genocide": "רצח עם",
    "hoax": "הונאה",
    "horror": "אימה",
    "hypocrites": "צבועים",
    "idiot": "אידיוט",
    "insane": "מטורף",
    "islam": "איסלאם",
    "islamic": "איסלאמי",
    "jews": "יהודים",
    "jihad": "ג'יהאד",
    "kill": "להרוג",
    "lawlessness": "חוסר חוק",
    "laws": "חוק",
    "leftist": "שמאלני",
    "legislation": "חקיקה",
    "let": "לתת",
    "liars": "שקרנים",
    "liberal": "ליברלי",
    "lie": "שקר",
    "literally": "ממש",
    "makes": "גורם",
    "migrants": "מהגרים",
    "moron": "טיפש",
    "murder": "רצח",
    "muslim": "מוסלמי",
    "offenders": "עבריינים",
    "palestinians": "פלסטינים",
    "people": "אנשים",
    "political": "פוליטי",
    "politicians": "פוליטיקאים",
    "progressives": "פרוגרסיבי",
    "radical": "רדיקלי",
    "rape": "אונס",
    "rapists": "אנסים",
    "refugee": "פליט",
    "religious": "דתי",
    "republican": "רפובליקני",
    "revealed": "נחשף",
    "revocation": "ביטול",
    "ridiculous": "מגוחך",
    "rifle": "רובה",
    "rumor": "שמועה",
    "scam": "הונאה",
    "scammers": "רמאים",
    "scheme": "תרסיס",
    "senate": "סנאט",
    "sharia": "שריעה",
    "shit": "חרא",
    "shocking": "מזעזע",
    "shooting": "ירי",
    "socialism": "סוציאליזם",
    "socialist": "סוציאליסטי",
    "strike": "מכה",
    "stupid": "טיפש",
    "suspense": "מתח",
    "syrian": "סורי",
    "systemic": "מערכתי",
    "tell": "לספר",
    "terror": "טרור",
    "terrorism": "טרור",
    "terrorist": "מחבל",
    "theft": "גניבה",
    "threat": "איום",
    "threatening": "מאיים",
    "totally": "לגמרי",
    "truth": "אמת",
    "unbelievable": "בלתי יאומן",
    "unconstitutional": "לא חוקתי",
    "unreal": "לא אמיתי",
    "violence": "אלימות",
    "warming": "התחממות",
    "weapon": "נשק",
    "worse": "גרוע",
    "wrong": "שגוי",
    "gun": "נשק",
}

# Israeli-context additions not present in the English dictionary.
HEBREW_ONLY_ADDITIONS: dict[str, str] = {
    "ממשלה": "issue",
    "רפורמה": "issue",
    "אופוזיציה": "issue",
    "קואליציה": "issue",
    "כנסת": "issue",
    "שמאל": "issue",
    "ימין": "issue",
    "התנגד": "affective",
    "מחולק": "affective",
    "הסתה": "affective",
    "בוגד": "affective",
    "איום": "affective",
}


def _load_stem_labels() -> dict[str, str]:
    with SOURCE_PATH.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        labels: dict[str, str] = {}
        for row in rows:
            labels[row["stem"]] = row["label"]
        return labels


# Curated Israeli-news additions (formerly hebrew_lexicon_v2.py supplement).
HEBREW_MEDIA_V2_ADDITIONS: dict[str, str] = {
    "ציבור": "issue",
    "מחלוקת": "issue",
    "פילוג": "issue",
    "עימות": "issue",
    "בהחלט": "affective",
    "תמיד": "affective",
    "כולם": "affective",
    "מוחלט": "affective",
    "זעזוע": "affective",
    "הלם": "affective",
    "שוק": "affective",
    "משבר": "affective",
    "זעם": "affective",
    "כעס": "affective",
    "אסון": "affective",
    "טרגדיה": "affective",
    "קטסטרופה": "affective",
    "קורבן": "affective",
    "נפגע": "affective",
    "נהרג": "affective",
    "נרצח": "affective",
    "סובל": "affective",
    "סכנה": "affective",
    "תוקפני": "affective",
    "שונא": "affective",
    "מתנגד": "affective",
    "אשם": "affective",
    "אחריות": "affective",
    "גרם": "affective",
    "מאשים": "affective",
    "סערה": "affective",
    "דרמה": "affective",
    "חריפות": "affective",
    "בושה": "affective",
    "משחית": "affective",
    "שחית": "affective",
    "פוליטיקה": "issue",
}


def build() -> list[dict[str, str]]:
    stem_labels = _load_stem_labels()
    draft_rows: list[dict[str, str]] = []

    for stem, component in sorted(stem_labels.items()):
        if stem in SKIP_STEMS:
            draft_rows.append(
                {
                    "lemma_he": "",
                    "lemma_en": stem,
                    "component": component,
                    "status": "skipped",
                    "notes": "US-specific or low relevance for Israeli news",
                }
            )
            continue

        lemma_he = STEM_TO_HEBREW.get(stem, "")
        status = "approved" if lemma_he else "needs_review"
        draft_rows.append(
            {
                "lemma_he": lemma_he,
                "lemma_en": stem,
                "component": component,
                "status": status,
                "notes": "" if lemma_he else "missing Hebrew translation",
            }
        )

    for lemma_he, component in sorted(HEBREW_ONLY_ADDITIONS.items()):
        draft_rows.append(
            {
                "lemma_he": lemma_he,
                "lemma_en": "",
                "component": component,
                "status": "approved",
                "notes": "added for Israeli news context",
            }
        )

    for lemma_he, component in sorted(HEBREW_MEDIA_V2_ADDITIONS.items()):
        draft_rows.append(
            {
                "lemma_he": lemma_he,
                "lemma_en": "",
                "component": component,
                "status": "approved",
                "notes": "added from hebrew_lexicon_v2.py (reviewed)",
            }
        )

    return draft_rows


def _dedupe_approved_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    approved = [row for row in rows if row["status"] == "approved" and row["lemma_he"]]
    by_lemma: dict[str, dict[str, str]] = {}
    for row in approved:
        lemma = row["lemma_he"]
        existing = by_lemma.get(lemma)
        if existing is None or "hebrew_lexicon_v2" in row["notes"]:
            by_lemma[lemma] = row
    return list(by_lemma.values())


def write_outputs(rows: list[dict[str, str]]) -> int:
    approved = _dedupe_approved_rows(rows)
    output_rows = [
        {
            "lemma": row["lemma_he"],
            "component": row["component"],
            "notes": row["notes"] or row["lemma_en"],
        }
        for row in sorted(approved, key=lambda item: item["lemma_he"])
    ]
    with LEXICON_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["lemma", "component", "notes"])
        writer.writeheader()
        writer.writerows(output_rows)
    return len(output_rows)


def main() -> None:
    rows = build()
    approved_count = write_outputs(rows)
    skipped = sum(1 for row in rows if row["status"] == "skipped")
    needs_review = sum(1 for row in rows if row["status"] == "needs_review")
    lexicon = {row["lemma_he"]: row["component"] for row in _dedupe_approved_rows(rows)}
    expanded_count = len(expand_lexicon(lexicon))
    print(f"build rows: {len(rows)}")
    print(f"approved lemmas: {approved_count}")
    print(f"skipped: {skipped}")
    print(f"needs_review: {needs_review}")
    print(f"wrote {LEXICON_PATH}")
    print(f"expanded surface forms (in memory): {expanded_count}")


if __name__ == "__main__":
    main()
