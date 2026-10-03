import json
from pathlib import Path

from claude_md import checks  # noqa: F401
from claude_md.checks.enforcement import (
    EMPHASIS_LINE_LIMIT,
    emphasis_dilution,
    hook_candidate,
)
from claude_md.discovery import discover
from claude_md.findings import REGISTRY, Context, run_checks
from claude_md.model import LoadedFile, LoadMode, Scope

CTX = Context(Path("/p"), Path("/h"))
DOCS = "https://code.claude.com/docs/en/best-practices"
FIXTURES = Path(__file__).parent / "fixtures"
BANNED = ["per request", "every request", "each request", "per turn", "turns"]
BANNED += ["compound", "session cost"]


def make(text: str, mode: LoadMode = LoadMode.ALWAYS) -> LoadedFile:
    return LoadedFile(Path("/p/CLAUDE.md"), Scope.PROJECT, mode, 0, text, text)


def emphatic(count: int) -> str:
    return "\n".join(f"- IMPORTANT: rule number {i}." for i in range(count)) + "\n"


def test_registered_with_docs_source():
    for check_id in ("hook-candidate", "emphasis-dilution"):
        assert REGISTRY[check_id].source.kind == "docs"
        assert REGISTRY[check_id].source.url == DOCS


def test_hook_candidate_always_run():
    text = "# P\n\n- Always run `ruff format` before committing.\n"
    found = hook_candidate([make(text)], CTX)
    assert len(found) == 1
    assert found[0].check_id == "hook-candidate"
    assert found[0].line == 3
    assert "PreToolUse" in found[0].fix
    assert "PostToolUse" in found[0].fix
    assert "Stop" in found[0].fix
    assert "guidance" in found[0].fix
    assert found[0].source.url == DOCS
    assert not any(b in found[0].message.lower() for b in BANNED)


def test_hook_candidate_variants():
    text = (
        "Never commit without running `pytest`.\n"
        "After each edit run `make lint`.\n"
        "Run `mypy .` before every commit.\n"
    )
    assert [f.line for f in hook_candidate([make(text)], CTX)] == [1, 2, 3]


def test_hook_candidate_ignores_plain_preference():
    text = "- Prefer small functions.\n- Always be concise.\n- Never use `eval`.\n"
    assert hook_candidate([make(text)], CTX) == []


def test_hook_candidate_ignores_path_spans():
    text = "Never edit files under `pkg/_generated/`.\n"
    assert hook_candidate([make(text)], CTX) == []


def test_hook_candidate_ignores_fenced_code():
    text = "```\nAlways run `ruff format` before committing.\n```\n"
    assert hook_candidate([make(text)], CTX) == []


def test_hook_candidate_only_loaded_files():
    text = "Always run `ruff format`.\n"
    assert hook_candidate([make(text, LoadMode.ON_DEMAND)], CTX) == []


def test_emphasis_flags_six_lines():
    found = emphasis_dilution([make("# P\n\n" + emphatic(6))], CTX)
    assert len(found) == 1
    assert found[0].check_id == "emphasis-dilution"
    assert found[0].line == 3
    assert "6" in found[0].message
    assert "heuristic" in found[0].message
    assert "hook" in found[0].fix.lower()
    assert found[0].source.url == DOCS
    assert not any(b in found[0].message.lower() for b in BANNED)


def test_emphasis_ok_with_one_line():
    assert emphasis_dilution([make("IMPORTANT: run tests.\n")], CTX) == []


def test_emphasis_boundary():
    assert EMPHASIS_LINE_LIMIT == 5
    assert emphasis_dilution([make(emphatic(5))], CTX) == []
    assert len(emphasis_dilution([make(emphatic(6))], CTX)) == 1


def test_emphasis_counts_each_line_once():
    text = "".join("You MUST NEVER do IMPORTANT things.\n" for _ in range(5))
    assert emphasis_dilution([make(text)], CTX) == []


def test_emphasis_capitalised_run():
    text = "".join(f"DO NOT TOUCH file {i}.\n" for i in range(6))
    assert len(emphasis_dilution([make(text)], CTX)) == 1


def test_emphasis_ignores_lowercase_and_short_caps():
    text = "".join("must never important. Use the API and SDK.\n" for _ in range(8))
    assert emphasis_dilution([make(text)], CTX) == []


def test_emphasis_ignores_fenced_code():
    text = "```\n" + emphatic(8) + "```\n" + emphatic(3)
    assert emphasis_dilution([make(text)], CTX) == []


def test_emphasis_only_loaded_files():
    assert emphasis_dilution([make(emphatic(8), LoadMode.ON_DEMAND)], CTX) == []


def run_fixture(name: str, tmp_path: Path) -> set[str]:
    project = FIXTURES / name / "project"
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    files = discover(project, home, tmp_path / "managed")
    return {f.check_id for f in run_checks(files, Context(project, home))}


def test_fixture_hook_candidates_includes_id(tmp_path):
    assert "hook-candidate" in run_fixture("hook-candidates", tmp_path)


def test_fixture_emphasis_overload_includes_id(tmp_path):
    assert "emphasis-dilution" in run_fixture("emphasis-overload", tmp_path)


def test_clean_fixture_not_flagged(tmp_path):
    ids = run_fixture("clean", tmp_path)
    assert not ids & {"hook-candidate", "emphasis-dilution"}


def test_fixtures_excluding_ids_do_not_flag(tmp_path):
    for expected in FIXTURES.glob("*/expected.json"):
        data = json.loads(expected.read_text())
        ids = run_fixture(expected.parent.name, tmp_path)
        for check_id in ("hook-candidate", "emphasis-dilution"):
            if check_id in data["must_exclude"]:
                assert check_id not in ids, expected.parent.name
