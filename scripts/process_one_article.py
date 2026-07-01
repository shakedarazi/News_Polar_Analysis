"""Process a single fixture article using Simchon-style polarization scoring."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.hashing import article_id_from_url
from src.features.article_windows import compute_article_analysis
from src.features.comments_scoring import compute_comments_analysis
from src.lexicon.deterministic_matcher import DeterministicLexiconMatcher
from src.lexicon.load_polarization_lexicon import (
    DEFAULT_LEXICON_PATH,
    lexicon_version_from_file,
    load_expanded_lexicon,
    load_lexicon,
)

ARTICLE_PATH = ROOT / "data" / "fixtures" / "sample_article.json"
LEXICON_PATH = ROOT / DEFAULT_LEXICON_PATH

PIPELINE_VERSION = "0.5.0-deterministic"
RUN_ID = "manual-run-001"


def _print_token_classifications(token_matches: dict[str, str | None]) -> None:
    grouped: dict[str, list[str]] = {
        "issue": [],
        "affective": [],
        "unmatched": [],
    }
    for token, component in token_matches.items():
        if component == "issue":
            grouped["issue"].append(token)
        elif component == "affective":
            grouped["affective"].append(token)
        else:
            grouped["unmatched"].append(token)

    print("=== token classifications ===")
    for label in ("issue", "affective", "unmatched"):
        tokens = grouped[label]
        print(f"{label} ({len(tokens)}):")
        if tokens:
            for token in tokens:
                print(f"  - {token}")
        else:
            print("  (none)")
        print()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    article = json.loads(ARTICLE_PATH.read_text(encoding="utf-8"))
    lexicon_base = load_lexicon(LEXICON_PATH)
    lexicon_expanded = load_expanded_lexicon(LEXICON_PATH)
    matcher = DeterministicLexiconMatcher(lexicon_expanded)
    lexicon_version = lexicon_version_from_file(LEXICON_PATH)

    article_id = article_id_from_url(article["canonical_url"])
    analysis = compute_article_analysis(
        article_id=article_id,
        text=article["text"],
        lexicon_base=lexicon_base,
        token_matcher=matcher,
        lexicon_version=lexicon_version,
        pipeline_version=PIPELINE_VERSION,
        run_id=RUN_ID,
    )

    print(f"article_id: {article_id}")
    print(f"source: {article['source']}")
    print(f"lexicon: {LEXICON_PATH.relative_to(ROOT)}")
    print(f"lexicon lemmas: {len(lexicon_base)}")
    print(f"expanded forms (in memory): {len(lexicon_expanded)}")
    print(f"windows: {len(analysis.windows)}\n")

    _print_token_classifications(analysis.token_matches)

    print("=== article score ===")
    print(json.dumps(analysis.article.to_dict(), ensure_ascii=False, indent=2))
    print("\n=== window scores ===")
    for window in analysis.windows:
        print(json.dumps(window.to_dict(), ensure_ascii=False))

    comments = article.get("comments", [])
    if not comments:
        return

    comments_analysis = compute_comments_analysis(
        article_id=article_id,
        comments=comments,
        lexicon_base=lexicon_base,
        token_matcher=matcher,
        lexicon_version=lexicon_version,
        pipeline_version=PIPELINE_VERSION,
        run_id=RUN_ID,
    )

    print(f"\ncomments: {len(comments_analysis.comments)}\n")
    _print_token_classifications(comments_analysis.token_matches)

    print("=== audience score (comments) ===")
    print(json.dumps(comments_analysis.audience.to_dict(), ensure_ascii=False, indent=2))
    print("\n=== comment scores ===")
    for comment in comments_analysis.comments:
        print(json.dumps(comment.to_dict(), ensure_ascii=False))


if __name__ == "__main__":
    main()
