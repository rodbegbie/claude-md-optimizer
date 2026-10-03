import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "claude-md-optimizer"


def _description() -> str:
    frontmatter = (SKILL_DIR / "SKILL.md").read_text().split("---")[1]
    match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    assert match, "SKILL.md has no description"
    return match.group(1).strip()


def test_description_starts_with_use_when():
    assert _description().startswith("Use when")


def test_description_under_500_chars():
    assert len(_description()) < 500


def test_description_has_no_line_limits():
    description = _description()
    assert "150" not in description
    assert "50 lines" not in description


def test_description_states_triggers_not_workflow():
    description = _description().lower()
    for workflow_word in ("scores", "detects", "0-100"):
        assert workflow_word not in description


def test_rules_reference_has_contents_list():
    text = (SKILL_DIR / "references" / "optimization-rules.md").read_text()
    assert re.search(r"^## Contents$", text, re.MULTILINE)
    assert "(#sources)" in text
