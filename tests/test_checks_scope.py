import json
from pathlib import Path

from claude_md import checks  # noqa: F401
from claude_md.checks.scope import import_misconception, scope_candidate
from claude_md.discovery import discover
from claude_md.findings import REGISTRY, Context, run_checks
from claude_md.model import LoadedFile, LoadMode, Scope

CTX = Context(Path("/p"), Path("/h"))
MEMORY_DOCS = "https://code.claude.com/docs/en/memory"
FIXTURES = Path(__file__).parent / "fixtures"
BANNED = ["per request", "every request", "each request", "per turn", "turns"]
BANNED += ["compound", "session cost"]
IDS = ("scope-candidate", "import-misconception")


def make(text: str, mode: LoadMode = LoadMode.ALWAYS) -> LoadedFile:
    return LoadedFile(Path("/p/CLAUDE.md"), Scope.PROJECT, mode, 0, text, text)


def section(count: int, heading: str = "## API rules") -> str:
    rules = [
        "- When editing `src/api/**`, add a test.",
        "* when working in the `web/` directory, use the design tokens.",
        "When touching *.sql files, run the formatter.",
        "1. When editing `src/db/`, write a migration.",
    ]
    return f"{heading}\n\n" + "\n".join(rules[:count]) + "\n"


def test_registered_with_docs_source():
    for check_id in IDS:
        assert REGISTRY[check_id].source.kind == "docs"
        assert REGISTRY[check_id].source.url == MEMORY_DOCS


def test_scope_candidate_flagged():
    text = "# P\n\nIntro.\n\n" + section(3)
    found = scope_candidate([make(text)], CTX)
    assert len(found) == 1
    assert found[0].check_id == "scope-candidate"
    assert found[0].line == 5
    assert ".claude/rules" in found[0].fix
    assert "paths:" in found[0].fix
    assert "CLAUDE.md" in found[0].fix
    assert found[0].source.url == MEMORY_DOCS
    assert not any(b in found[0].message.lower() for b in BANNED)


def test_scope_candidate_one_finding_per_section():
    text = section(4, "## One") + "\n" + section(3, "## Two")
    assert [f.line for f in scope_candidate([make(text)], CTX)] == [1, 8]


def test_scope_boundary_two_lines_not_enough():
    assert scope_candidate([make(section(2))], CTX) == []


def test_scope_ignores_general_section():
    text = "## Style\n\n- When editing, be careful.\n- Prefer small functions.\n"
    text += "- When working in a team, communicate.\n- When touching code, test.\n"
    assert scope_candidate([make(text)], CTX) == []


def test_scope_conditional_rule_not_flagged():
    assert scope_candidate([make(section(4), LoadMode.CONDITIONAL)], CTX) == []


def test_scope_ignores_fenced_content():
    text = "## Example\n\n```\n" + section(4) + "```\n"
    assert scope_candidate([make(text)], CTX) == []


def test_scope_lines_split_across_sections_not_summed():
    text = section(2, "## A") + "\n" + section(2, "## B")
    assert scope_candidate([make(text)], CTX) == []


def import_text(sentence: str, with_import: bool = True) -> str:
    imp = "@docs/conventions.md\n" if with_import else ""
    return f"# P\n\n{sentence}\n\n{imp}"


def test_import_misconception_flagged():
    text = import_text("We split into imports to save tokens.")
    found = import_misconception([make(text)], CTX)
    assert len(found) == 1
    assert found[0].check_id == "import-misconception"
    assert found[0].severity == "suggestion"
    assert found[0].line == 3
    assert "launch" in found[0].message
    assert found[0].source.url == MEMORY_DOCS
    assert not any(b in found[0].message.lower() for b in BANNED)


def test_import_misconception_variants():
    for sentence in (
        "Use @imports to reduce context.",
        "I moved rules into an imported file to save context.",
        "Importing keeps the token count down: reduce tokens this way.",
    ):
        found = import_misconception([make(import_text(sentence))], CTX)
        assert len(found) == 1, sentence


def test_import_note_absent_without_imports():
    text = import_text("We split into imports to save tokens.", with_import=False)
    assert import_misconception([make(text)], CTX) == []


def test_import_in_code_does_not_count_as_import():
    text = import_text("Split into imports to save tokens.", with_import=False)
    text += "```\n@docs/conventions.md\n```\nUse `@docs/x.md` sparingly.\n"
    assert import_misconception([make(text)], CTX) == []


def test_import_unrelated_mention_not_flagged():
    text = import_text("The CLI can import CSVs. Saving is automatic.")
    assert import_misconception([make(text)], CTX) == []


def test_import_ignores_fenced_sentence():
    text = "```\nSplit into imports to save tokens.\n```\n@docs/c.md\n"
    assert import_misconception([make(text)], CTX) == []


def test_import_only_loaded_files():
    text = import_text("We split into imports to save tokens.")
    assert import_misconception([make(text, LoadMode.ON_DEMAND)], CTX) == []


def run_fixture(name: str, tmp_path: Path) -> set[str]:
    project = FIXTURES / name / "project"
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    files = discover(project, home, tmp_path / "managed")
    return {f.check_id for f in run_checks(files, Context(project, home))}


def test_fixture_scoped_in_always_on_includes_id(tmp_path):
    assert "scope-candidate" in run_fixture("scoped-in-always-on", tmp_path)


def test_fixture_import_for_savings_includes_id(tmp_path):
    assert "import-misconception" in run_fixture("import-for-savings", tmp_path)


def test_clean_fixture_not_flagged(tmp_path):
    assert not run_fixture("clean", tmp_path) & set(IDS)


def test_fixtures_excluding_ids_do_not_flag(tmp_path):
    for expected in FIXTURES.glob("*/expected.json"):
        data = json.loads(expected.read_text())
        ids = run_fixture(expected.parent.name, tmp_path)
        for check_id in IDS:
            if check_id in data["must_exclude"]:
                assert check_id not in ids, expected.parent.name
