import json
from pathlib import Path

import pytest
from claude_md.discovery import discover
from claude_md.model import LoadMode, Scope

DORMANT_NOTE = (
    "AGENTS.md not loaded: a CLAUDE.md exists at or above the working directory"
)


@pytest.fixture
def layout(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    project = root / "outer" / "proj"
    home.mkdir()
    project.mkdir(parents=True)
    return root, home, project


def write(path: Path, content: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def settings(path: Path, excludes) -> None:
    write(path, json.dumps({"claudeMdExcludes": excludes}))


def run(layout, managed=None):
    root, home, project = layout
    files = [f for f in discover(project, home, managed) if f.path.is_relative_to(root)]
    return {str(f.path.relative_to(root)): f for f in files}


def test_agents_loaded_when_no_claude_md(layout):
    _, _, project = layout
    write(project / "AGENTS.md", "agent rules\n")
    f = run(layout)["outer/proj/AGENTS.md"]
    assert (f.scope, f.mode, f.text) == (Scope.AGENTS, LoadMode.ALWAYS, "agent rules\n")


def test_agents_dormant_when_claude_md_exists(layout):
    _, _, project = layout
    write(project / "AGENTS.md")
    write(project / "CLAUDE.md")
    f = run(layout)["outer/proj/AGENTS.md"]
    assert (f.scope, f.mode) == (Scope.AGENTS, LoadMode.DORMANT)
    assert f.raw == "x\n"
    assert DORMANT_NOTE in f.notes


def test_claude_local_md_counts_as_claude_md(layout):
    _, _, project = layout
    write(project / "AGENTS.md")
    write(project / "CLAUDE.local.md")
    assert run(layout)["outer/proj/AGENTS.md"].mode == LoadMode.DORMANT


def test_user_claude_md_does_not_suppress_agents(layout):
    _, home, project = layout
    write(project / "AGENTS.md")
    write(home / ".claude" / "CLAUDE.md")
    assert run(layout)["outer/proj/AGENTS.md"].mode == LoadMode.ALWAYS


def test_managed_claude_md_does_not_suppress_agents(layout):
    root, _, project = layout
    write(project / "AGENTS.md")
    write(root / "managed" / "CLAUDE.md")
    files = run(layout, root / "managed")
    assert files["outer/proj/AGENTS.md"].mode == LoadMode.ALWAYS


def test_rules_do_not_suppress_agents(layout):
    _, home, project = layout
    write(project / "AGENTS.md")
    write(project / ".claude" / "rules" / "r.md")
    write(home / ".claude" / "rules" / "u.md")
    assert run(layout)["outer/proj/AGENTS.md"].mode == LoadMode.ALWAYS


def test_dot_claude_agents_md_is_read(layout):
    _, _, project = layout
    write(project / "AGENTS.md")
    write(project / ".claude" / "AGENTS.md")
    files = run(layout)
    assert list(files) == ["outer/proj/AGENTS.md", "outer/proj/.claude/AGENTS.md"]
    assert [f.order for f in files.values()] == [0, 1]
    assert all(f.mode == LoadMode.ALWAYS for f in files.values())


def test_ancestor_agents_loaded_root_to_cwd(layout):
    root, _, project = layout
    write(project / "AGENTS.md")
    write(root / "outer" / "AGENTS.md")
    write(root / "outer" / ".claude" / "AGENTS.md")
    files = run(layout)
    assert list(files) == [
        "outer/AGENTS.md",
        "outer/.claude/AGENTS.md",
        "outer/proj/AGENTS.md",
    ]
    assert all(f.mode == LoadMode.ALWAYS for f in files.values())


def test_ancestor_dot_claude_claude_md_suppresses_but_is_not_loaded(layout):
    root, _, project = layout
    write(root / "outer" / ".claude" / "CLAUDE.md")
    write(project / "AGENTS.md")
    files = run(layout)
    assert files["outer/proj/AGENTS.md"].mode == LoadMode.DORMANT
    assert "outer/.claude/CLAUDE.md" not in files


def test_ancestor_claude_md_makes_agents_dormant(layout):
    root, _, project = layout
    write(root / "outer" / "CLAUDE.md")
    write(project / "AGENTS.md")
    assert run(layout)["outer/proj/AGENTS.md"].mode == LoadMode.DORMANT


def test_nested_agents_on_demand_only_without_claude_family(layout):
    _, _, project = layout
    write(project / "a" / "AGENTS.md")
    write(project / "a" / "sub" / "AGENTS.md")
    write(project / "a" / "sub" / "CLAUDE.md")
    write(project / "z" / "CLAUDE.md")
    write(project / "c" / "AGENTS.md")
    write(project / "c" / ".claude" / "CLAUDE.md")
    write(project / "d" / "AGENTS.md")
    write(project / "d" / "CLAUDE.local.md")
    files = run(layout)
    agents = [k for k, v in files.items() if v.scope == Scope.AGENTS]
    assert agents == ["outer/proj/a/AGENTS.md"]
    assert files["outer/proj/a/AGENTS.md"].mode == LoadMode.ON_DEMAND
    assert files["outer/proj/z/CLAUDE.md"].mode == LoadMode.ON_DEMAND
    assert files["outer/proj/a/AGENTS.md"].order > files["outer/proj/z/CLAUDE.md"].order


def test_nested_agents_ignored_when_dormant(layout):
    _, _, project = layout
    write(project / "CLAUDE.md")
    write(project / "a" / "AGENTS.md")
    assert "outer/proj/a/AGENTS.md" not in run(layout)


def test_agents_variants_never_read(layout):
    _, _, project = layout
    write(project / "AGENTS.local.md")
    write(project / "AGENTS.override.md")
    write(project / ".agents" / "AGENTS.md")
    write(project / ".agents" / "x.md")
    write(project / "a" / "AGENTS.local.md")
    write(project / "a" / ".agents" / "AGENTS.md")
    assert run(layout) == {}


def test_imports_in_loaded_agents_are_expanded(layout):
    _, _, project = layout
    write(project / "AGENTS.md", "see @extra.md\n")
    write(project / "extra.md", "more\n")
    imported = run(layout)["outer/proj/extra.md"]
    assert imported.scope == Scope.IMPORT
    assert imported.imported_by == project / "AGENTS.md"
    assert imported.mode == LoadMode.ALWAYS


def test_imports_in_dormant_agents_are_not_expanded(layout):
    _, _, project = layout
    write(project / "CLAUDE.md")
    write(project / "AGENTS.md", "see @extra.md\n")
    write(project / "extra.md")
    assert "outer/proj/extra.md" not in run(layout)


def test_excludes_glob_marks_file(layout):
    _, _, project = layout
    write(project / "CLAUDE.md", "hello\n")
    settings(project / ".claude" / "settings.json", ["**/proj/CLAUDE.md"])
    f = run(layout)["outer/proj/CLAUDE.md"]
    assert f.mode == LoadMode.EXCLUDED
    assert f.notes == ["excluded by claudeMdExcludes: **/proj/CLAUDE.md"]
    assert f.raw == "hello\n"


def test_excludes_first_matching_pattern_in_note(layout):
    _, _, project = layout
    write(project / "CLAUDE.md")
    settings(
        project / ".claude" / "settings.json",
        ["**/nomatch.md", "**/*.md", "**/proj/*"],
    )
    f = run(layout)["outer/proj/CLAUDE.md"]
    assert f.notes == ["excluded by claudeMdExcludes: **/*.md"]


def test_excludes_merge_across_settings(layout):
    _, home, project = layout
    write(project / "CLAUDE.md")
    write(project / "CLAUDE.local.md")
    write(project / ".claude" / "rules" / "r.md")
    settings(home / ".claude" / "settings.json", ["**/CLAUDE.md"])
    settings(home / ".claude" / "settings.local.json", ["**/CLAUDE.local.md"])
    settings(project / ".claude" / "settings.local.json", ["**/rules/**"])
    files = run(layout)
    assert files["outer/proj/CLAUDE.md"].mode == LoadMode.EXCLUDED
    assert files["outer/proj/CLAUDE.local.md"].mode == LoadMode.EXCLUDED
    assert files["outer/proj/.claude/rules/r.md"].mode == LoadMode.EXCLUDED


def test_duplicates_across_layers_collapse(layout):
    _, home, project = layout
    write(project / "CLAUDE.md")
    settings(home / ".claude" / "settings.json", ["**/CLAUDE.md"])
    settings(project / ".claude" / "settings.json", ["**/CLAUDE.md"])
    f = run(layout)["outer/proj/CLAUDE.md"]
    assert f.notes == ["excluded by claudeMdExcludes: **/CLAUDE.md"]


def test_unreadable_settings_json_is_ignored(layout):
    _, home, project = layout
    write(project / "CLAUDE.md")
    write(project / ".claude" / "settings.json", "{not json")
    (project / ".claude" / "settings.local.json").mkdir()
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_bytes(b"\xff\xfe\x00")
    assert run(layout)["outer/proj/CLAUDE.md"].mode == LoadMode.ALWAYS


@pytest.mark.parametrize(
    "content",
    [
        '["**/CLAUDE.md"]',
        '{"claudeMdExcludes": "**/CLAUDE.md"}',
        '{"claudeMdExcludes": {"a": 1}}',
        "null",
    ],
)
def test_malformed_settings_shapes_are_ignored(layout, content):
    _, _, project = layout
    write(project / "CLAUDE.md")
    write(project / ".claude" / "settings.json", content)
    assert run(layout)["outer/proj/CLAUDE.md"].mode == LoadMode.ALWAYS


def test_non_string_entries_are_ignored(layout):
    _, _, project = layout
    write(project / "CLAUDE.md")
    settings(project / ".claude" / "settings.json", [1, None, ["x"], "**/CLAUDE.md"])
    assert run(layout)["outer/proj/CLAUDE.md"].mode == LoadMode.EXCLUDED


def test_tilde_pattern_expands_against_home(layout):
    _, home, project = layout
    write(home / "shared" / "team" / "CLAUDE.md")
    write(project / "CLAUDE.md", "@~/shared/team/CLAUDE.md\n")
    settings(project / ".claude" / "settings.json", ["~/shared/**"])
    files = run(layout)
    assert files["home/shared/team/CLAUDE.md"].mode == LoadMode.EXCLUDED
    assert files["outer/proj/CLAUDE.md"].mode == LoadMode.ALWAYS


def test_absolute_rules_pattern_from_docs(layout):
    _, _, project = layout
    write(project / ".claude" / "rules" / "sub" / "r.md")
    write(project / "CLAUDE.md")
    settings(project / ".claude" / "settings.json", [f"{project}/.claude/rules/**"])
    files = run(layout)
    assert files["outer/proj/.claude/rules/sub/r.md"].mode == LoadMode.EXCLUDED
    assert files["outer/proj/CLAUDE.md"].mode == LoadMode.ALWAYS


def test_pattern_matches_unresolved_symlink_path(layout):
    root, _, project = layout
    write(root / "real" / "rules" / "r.md")
    (project / ".claude").mkdir()
    (project / ".claude" / "rules").symlink_to(root / "real" / "rules")
    settings(project / ".claude" / "settings.json", [f"{project}/.claude/rules/**"])
    f = run(layout)["outer/proj/.claude/rules/r.md"]
    assert f.mode == LoadMode.EXCLUDED


def test_managed_claude_md_is_never_excluded(layout):
    root, home, _ = layout
    write(root / "managed" / "CLAUDE.md")
    settings(home / ".claude" / "settings.json", ["**/CLAUDE.md"])
    f = run(layout, root / "managed")["managed/CLAUDE.md"]
    assert f.mode == LoadMode.ALWAYS
    assert f.notes == []


def test_excluded_file_imports_are_not_loaded(layout):
    _, _, project = layout
    write(project / "CLAUDE.md", "@extra.md\n")
    write(project / "extra.md")
    settings(project / ".claude" / "settings.json", ["**/proj/CLAUDE.md"])
    files = run(layout)
    assert files["outer/proj/CLAUDE.md"].mode == LoadMode.EXCLUDED
    assert "outer/proj/extra.md" not in files


def test_excluded_agents_file_is_excluded(layout):
    _, _, project = layout
    write(project / "AGENTS.md", "@extra.md\n")
    write(project / "extra.md")
    settings(project / ".claude" / "settings.json", ["**/AGENTS.md"])
    files = run(layout)
    assert files["outer/proj/AGENTS.md"].mode == LoadMode.EXCLUDED
    assert "outer/proj/extra.md" not in files


def test_excluded_nested_file_is_excluded(layout):
    _, _, project = layout
    write(project / "sub" / "CLAUDE.md")
    settings(project / ".claude" / "settings.json", ["**/sub/CLAUDE.md"])
    assert run(layout)["outer/proj/sub/CLAUDE.md"].mode == LoadMode.EXCLUDED
