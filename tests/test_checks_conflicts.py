import time
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
            user("- Always use tabs.\n"),
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
    found = possible_conflict([a, b], CTX)
    assert [f.line for f in found] == [1, 2]
    assert "Prefer pytest" in found[0].message
    assert "Avoid pytest" in found[0].message
    assert "Don't use mocks" in found[1].message
    assert "Use mocks" in found[1].message


def flagged(earlier: str, later: str) -> int:
    return len(possible_conflict([user(earlier + "\n"), project(later + "\n")], CTX))


def test_qualified_rules_not_flagged():
    assert flagged("Use TypeScript", "Never use TypeScript for scripts") == 0
    assert flagged("Use pytest for tests", "Never use pytest for e2e") == 0
    assert flagged("Always use tabs", "Never use tabs, except in Makefiles") == 0
    assert flagged("Use uv when available", "Don't use uv") == 0


def test_unqualified_rules_still_flagged():
    assert flagged("Always use tabs", "Never use tabs") == 1
    assert flagged("Use uv", "Don't use uv") == 1
    assert flagged("- **Always** use tabs.", "- Never use tabs.") == 1


def test_descriptive_use_is_not_a_rule():
    for prose in ("We use pytest", "Tests use fixtures", "You can use the CLI"):
        assert flagged(prose, "Never use pytest") == 0
        assert flagged(prose, "Never use fixtures") == 0
        assert flagged(prose, "Never use the CLI") == 0


def test_imperative_use_is_a_rule():
    assert flagged("- Use the CLI.", "Never use the CLI") == 1
    assert flagged("You should use the CLI", "Never use the CLI") == 1
    assert flagged("Please use the CLI", "Never use the CLI") == 1


def test_using_is_a_stopword():
    assert flagged("Use mocks", "Avoid using mocks") == 1


def test_double_negation_skipped():
    assert flagged("Use mocks", "Do not avoid mocks") == 0
    assert flagged("Never avoid mocks", "Use mocks") == 0


def test_same_underlying_file_not_paired():
    a = make("Always use tabs.\n", Scope.USER, "same.md", 0)
    b = make("Never use tabs.\n", Scope.IMPORT, "same.md", 1)
    assert possible_conflict([a, b], CTX) == []


def test_repeated_object_gives_bounded_findings():
    files = [user("Always use tabs.\n")]
    files += [
        make("Never use tabs.\n", Scope.PROJECT, f"p{i}.md", i + 1) for i in range(20)
    ]
    found = possible_conflict(files, CTX)
    assert len(found) == 20
    assert all("home/CLAUDE.md:1" in f.message for f in found)


def test_many_files_finish_quickly():
    objects = ["tabs", "spaces", "eval", "mocks", "pytest"]
    lines = [
        f"- {'Always use' if i % 2 else 'Never use'} {objects[i % 5]}."
        for i in range(200)
    ]
    text = "\n".join(lines) + "\n"
    files = [
        make(text, Scope.USER if i % 2 else Scope.PROJECT, f"f{i}.md", i)
        for i in range(50)
    ]
    start = time.perf_counter()
    found = possible_conflict(files, CTX)
    assert time.perf_counter() - start < 1.0
    assert len(found) <= 50 * 200


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
