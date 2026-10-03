from pathlib import Path

from claude_md import checks  # noqa: F401
from claude_md.checks.duplicates import duplicate_across, duplicate_within, no_trigger
from claude_md.checks.language import non_english
from claude_md.findings import REGISTRY, Context
from claude_md.model import LoadedFile, LoadMode, Scope

CTX = Context(Path("/p"), Path("/h"))
LINE = "Always run the full test suite before committing"


def make(
    text: str,
    mode: LoadMode = LoadMode.ALWAYS,
    path: str = "/p/CLAUDE.md",
    scope: Scope = Scope.PROJECT,
) -> LoadedFile:
    return LoadedFile(Path(path), scope, mode, 0, text, text)


def test_registered_as_heuristic():
    for check_id in (
        "duplicate-within",
        "duplicate-across",
        "no-trigger",
        "non-english",
    ):
        assert REGISTRY[check_id].source.kind == "heuristic"


def test_duplicate_within_flags_repeated_line():
    found = duplicate_within([make(f"{LINE}\nother\n{LINE}\n")], CTX)
    assert len(found) == 1
    assert found[0].check_id == "duplicate-within"
    assert found[0].line == 3
    assert "1 duplicate" in found[0].message


def test_duplicate_within_ignores_short_and_unique_lines():
    assert duplicate_within([make("short line\nshort line\n" + LINE)], CTX) == []


def test_duplicate_across_flags_shared_line_once():
    a = make(f"{LINE}\n{LINE}\n", path="/p/CLAUDE.md")
    b = make(f"x\n{LINE}\n", path="/p/.claude/rules/r.md", scope=Scope.PROJECT_RULE)
    found = duplicate_across([a, b], CTX)
    assert len(found) == 1
    assert found[0].path == a.path
    assert found[0].line == 1
    assert "/p/CLAUDE.md" in found[0].message
    assert "/p/.claude/rules/r.md" in found[0].message


def conditional(path: str, paths: list[str], text: str = LINE + "\n") -> LoadedFile:
    file = make(text, LoadMode.CONDITIONAL, path, Scope.PROJECT_RULE)
    file.paths = paths
    return file


def test_duplicate_across_ignores_rules_scoped_to_different_paths():
    src = conditional("/p/.claude/rules/src.md", ["src/**"])
    tests = conditional("/p/.claude/rules/tests.md", ["tests/**"])
    assert duplicate_across([src, tests], CTX) == []


def test_duplicate_across_flags_rules_scoped_to_the_same_paths():
    a = conditional("/p/.claude/rules/a.md", ["src/**", "lib/**"])
    b = conditional("/p/.claude/rules/b.md", ["lib/**", "src/**"])
    found = duplicate_across([a, b], CTX)
    assert len(found) == 1
    assert "same paths" in found[0].fix


def test_duplicate_across_flags_a_scoped_copy_of_an_always_on_line():
    always = make(LINE + "\n")
    scoped = conditional("/p/.claude/rules/src.md", ["src/**"])
    found = duplicate_across([always, scoped], CTX)
    assert len(found) == 1
    assert found[0].path == always.path
    assert "always-loaded" in found[0].fix


def test_duplicate_across_with_three_scopes_flags_only_the_redundant_pair():
    one = conditional("/p/.claude/rules/one.md", ["src/**"])
    two = conditional("/p/.claude/rules/two.md", ["src/**"])
    other = conditional("/p/.claude/rules/other.md", ["tests/**"])
    found = duplicate_across([one, two, other], CTX)
    assert len(found) == 1
    assert "one.md" in found[0].message and "two.md" in found[0].message
    assert "other.md" not in found[0].message


def test_duplicate_across_reports_every_redundant_scope_group():
    src_a = conditional("/p/.claude/rules/src-a.md", ["src/**"])
    src_b = conditional("/p/.claude/rules/src-b.md", ["src/**"])
    tests_a = conditional("/p/.claude/rules/tests-a.md", ["tests/**"])
    tests_b = conditional("/p/.claude/rules/tests-b.md", ["tests/**"])
    found = duplicate_across([src_a, src_b, tests_a, tests_b], CTX)
    assert len(found) == 2
    assert [f.path for f in found] == [src_a.path, tests_a.path]
    assert "tests-" not in found[0].message
    assert "src-" not in found[1].message


def test_duplicate_across_negative_for_distinct_files_and_headings():
    a = make("# A heading that is long enough to count\n")
    b = make("# A heading that is long enough to count\n", path="/p/b.md")
    assert duplicate_across([a, b], CTX) == []
    assert duplicate_across([a], CTX) == []


def test_duplicate_across_ignores_excluded_files():
    a = make(LINE)
    for mode in (LoadMode.EXCLUDED, LoadMode.DORMANT, LoadMode.ON_DEMAND):
        b = make(LINE, mode=mode, path="/p/b.md")
        assert duplicate_across([a, b], CTX) == []
    c = make(LINE, mode=LoadMode.CONDITIONAL, path="/p/c.md")
    assert len(duplicate_across([a, c], CTX)) == 1


def test_no_trigger_flags_long_project_file():
    text = "\n".join(f"line number {i}" for i in range(90))
    found = no_trigger([make(text)], CTX)
    assert [f.check_id for f in found] == ["no-trigger"]


def test_no_trigger_negative_cases():
    long = "\n".join(f"line number {i}" for i in range(90))
    assert no_trigger([make("short")], CTX) == []
    assert no_trigger([make(long + "\nRead docs/a.md when editing api\n")], CTX) == []
    rule = make(long, scope=Scope.PROJECT_RULE, path="/p/.claude/rules/r.md")
    assert no_trigger([rule], CTX) == []


def test_non_english_flags_cjk_heavy_text():
    found = non_english([make("使用中文编写所有的指令和说明 abc")], CTX)
    assert len(found) == 1
    assert "Non-English content" in found[0].message
    assert "extra tokens" in found[0].message


def test_non_english_absent_for_english_only():
    assert non_english([make("Plain English instructions only.")], CTX) == []
    assert non_english([make("")], CTX) == []
