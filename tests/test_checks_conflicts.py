from pathlib import Path

from claude_md import checks  # noqa: F401
from claude_md.checks.conflicts import possible_conflict
from claude_md.discovery import discover
from claude_md.findings import REGISTRY, Context, run_checks
from claude_md.model import LoadedFile, LoadMode, Scope

CTX = Context(Path("/p"), Path("/h"))
BANNED = ["per request", "every request", "each request", "per turn", "turns"]
BANNED += ["compound", "session cost"]


def make(
    text: str,
    scope: Scope = Scope.PROJECT,
    name: str = "CLAUDE.md",
    order: int = 0,
    mode: LoadMode = LoadMode.ALWAYS,
) -> LoadedFile:
    return LoadedFile(Path("/p") / name, scope, mode, order, text, text)


def user(text: str) -> LoadedFile:
    return make(text, Scope.USER, "home/CLAUDE.md", 0)


def project(text: str) -> LoadedFile:
    return make(text, Scope.PROJECT, "CLAUDE.md", 1)


def test_registered_as_low_confidence_heuristic():
    spec = REGISTRY["possible-conflict"]
    assert spec.source.kind == "heuristic"
    assert spec.source.url is None


def test_flags_use_vs_never_use():
    found = possible_conflict(
        [
            user("- Always use tabs for indentation.\n"),
            project("# P\n\n- Never use tabs.\n"),
        ],
        CTX,
    )
    assert len(found) == 1
    finding = found[0]
    assert finding.check_id == "possible-conflict"
    assert finding.severity == "suggestion"
    assert finding.path == Path("/p/CLAUDE.md")
    assert finding.line == 3
    assert "/p/home/CLAUDE.md:1" in finding.message
    assert "/p/CLAUDE.md:3" in finding.message
    assert "low-confidence heuristic" in finding.message
    assert "Never use tabs" in finding.message
    assert "Decide which" in finding.fix
    assert not any(b in finding.message.lower() for b in BANNED)


def test_flags_prefer_vs_avoid_and_dont_use():
    a = user("Prefer pytest over unittest.\nDon't use mocks.\n")
    b = project("Avoid pytest.\nUse mocks.\n")
    assert len(possible_conflict([a, b], CTX)) == 2


def test_no_flag_within_same_polarity():
    found = possible_conflict(
        [user("- Always use tabs.\n"), project("- Prefer tabs.\n")], CTX
    )
    assert found == []


def test_same_file_not_flagged():
    text = "- Always use tabs.\n- Never use tabs.\n"
    assert possible_conflict([project(text)], CTX) == []


def test_same_scope_different_files_not_flagged():
    a = make("- Always use tabs.\n", Scope.PROJECT_RULE, "r/a.md", 1)
    b = make("- Never use tabs.\n", Scope.PROJECT_RULE, "r/b.md", 2)
    assert possible_conflict([a, b], CTX) == []


def test_fenced_lines_ignored():
    a = user("```\nAlways use tabs.\n```\n")
    b = project("Never use tabs.\n")
    assert possible_conflict([a, b], CTX) == []


def test_unrelated_nouns_not_flagged():
    a = user("Always use tabs.\n")
    b = project("Never use eval.\n")
    assert possible_conflict([a, b], CTX) == []


def test_stopword_only_overlap_not_flagged():
    a = user("Use the\n")
    b = project("Never use the\n")
    assert possible_conflict([a, b], CTX) == []


def test_unloaded_files_not_flagged():
    a = user("Always use tabs.\n")
    b = make("Never use tabs.\n", mode=LoadMode.DORMANT)
    assert possible_conflict([a, b], CTX) == []


def test_anchored_at_later_loaded_file_regardless_of_input_order():
    a = user("Never use tabs.\n")
    b = project("Always use tabs.\n")
    found = possible_conflict([b, a], CTX)
    assert len(found) == 1
    assert found[0].path == b.path


def test_through_real_discovery(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "CLAUDE.md").write_text("- Always use tabs.\n")
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "CLAUDE.md").write_text("- Never use tabs.\n")
    files = discover(proj, home, tmp_path / "none")
    found = [
        f
        for f in run_checks(files, Context(proj, home))
        if f.check_id == "possible-conflict"
    ]
    assert len(found) == 1
