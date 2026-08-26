"""Guard the scheduled ingestion order: analyze before classify."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "run_ingestion.sh").read_text(encoding="utf-8")


def _first_code_index(needle: str) -> int:
    for index, line in enumerate(SCRIPT.splitlines()):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if needle in line:
            return index
    raise AssertionError(f"{needle!r} not found in run_ingestion.sh")


def test_analyze_runs_before_classify():
    analyze_at = _first_code_index("--require-comments-fetched")
    classify_at = _first_code_index("classify_articles.py")
    assert analyze_at < classify_at


def test_classify_is_bonus_and_cannot_fail_the_run():
    classify_line = next(
        line for line in SCRIPT.splitlines() if "classify_articles.py" in line and not line.strip().startswith("#")
    )
    assert "run_bonus_step" in classify_line
    assert "run_step python" not in classify_line


def test_comment_fetch_is_capped():
    comments_line = next(
        line
        for line in SCRIPT.splitlines()
        if "fetch_comments.py" in line and not line.strip().startswith("#")
    )
    assert "--limit 80" in comments_line
    assert "--max-minutes 25" in comments_line
    assert "--haaretz-limit 10" in comments_line
