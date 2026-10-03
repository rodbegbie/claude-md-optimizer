import os

import pytest
from claude_md.discovery import discover
from claude_md.model import LoadMode, Scope


@pytest.fixture
def layout(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    project = root / "outer" / "proj"
    home.mkdir()
    project.mkdir(parents=True)
    return root, home, project


def write(path, content="x\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def found(root, files):
    return [f for f in files if f.path.is_relative_to(root)]


def rel(root, files):
    return [str(f.path.relative_to(root)) for f in found(root, files)]


def rules(root, files, scope):
    return [f for f in found(root, files) if f.scope == scope]


def test_rules_recursive(layout):
    root, home, project = layout
    write(project / ".claude" / "rules" / "a.md")
    write(project / ".claude" / "rules" / "sub" / "deep" / "b.md")
    files = rules(root, discover(project, home), Scope.PROJECT_RULE)
    assert [f.path.name for f in files] == ["a.md", "b.md"]
    assert all(f.mode == LoadMode.ALWAYS and f.paths is None for f in files)


def test_user_rules_before_project_rules(layout):
    root, home, project = layout
    write(project / ".claude" / "rules" / "p.md")
    write(home / ".claude" / "rules" / "u.md")
    files = found(root, discover(project, home))
    assert [(f.path.name, f.scope) for f in files] == [
        ("u.md", Scope.USER_RULE),
        ("p.md", Scope.PROJECT_RULE),
    ]
    assert [f.order for f in files] == sorted(f.order for f in files)


def test_paths_frontmatter_makes_rule_conditional(layout):
    root, home, project = layout
    write(
        project / ".claude" / "rules" / "r.md",
        "---\npaths:\n  - src/**/*.ts\n  - lib/*.py\n---\nBody\n",
    )
    (f,) = rules(root, discover(project, home), Scope.PROJECT_RULE)
    assert f.mode == LoadMode.CONDITIONAL
    assert f.paths == ["src/**/*.ts", "lib/*.py"]


def test_malformed_paths_is_unconditional(layout):
    root, home, project = layout
    write(
        project / ".claude" / "rules" / "r.md",
        '---\npaths: ["unclosed\n---\nBody\n',
    )
    (f,) = rules(root, discover(project, home), Scope.PROJECT_RULE)
    assert f.mode == LoadMode.ALWAYS
    assert f.paths is None


def test_non_list_paths_string_is_accepted(layout):
    root, home, project = layout
    write(
        project / ".claude" / "rules" / "r.md",
        "---\npaths: src/**/*.ts, docs/*.md\n---\nBody\n",
    )
    (f,) = rules(root, discover(project, home), Scope.PROJECT_RULE)
    assert f.mode == LoadMode.CONDITIONAL
    assert f.paths == ["src/**/*.ts", "docs/*.md"]


def test_symlink_loop_in_rules_terminates(layout):
    root, home, project = layout
    rules_dir = project / ".claude" / "rules"
    write(rules_dir / "a.md")
    (rules_dir / "sub").mkdir()
    os.symlink(rules_dir, rules_dir / "sub" / "loop")
    files = rules(root, discover(project, home), Scope.PROJECT_RULE)
    assert [f.path.name for f in files] == ["a.md"]


def test_user_rules_after_user_claude_md_before_ancestors(layout):
    root, home, project = layout
    write(home / ".claude" / "CLAUDE.md")
    write(home / ".claude" / "rules" / "u.md")
    write(root / "outer" / "CLAUDE.md")
    files = found(root, discover(project, home))
    assert [f.scope for f in files] == [Scope.USER, Scope.USER_RULE, Scope.ANCESTOR]


def test_project_rules_between_dot_claude_md_and_local(layout):
    root, home, project = layout
    write(project / "CLAUDE.md")
    write(project / ".claude" / "CLAUDE.md")
    write(project / ".claude" / "rules" / "r.md")
    write(project / "CLAUDE.local.md")
    files = found(root, discover(project, home))
    assert [f.scope for f in files] == [
        Scope.PROJECT,
        Scope.PROJECT,
        Scope.PROJECT_RULE,
        Scope.LOCAL,
    ]
    assert files[1].path.name == "CLAUDE.md"
    assert files[1].path.parent.name == ".claude"


def test_ancestor_rules_not_read(layout):
    root, home, project = layout
    write(root / "outer" / ".claude" / "rules" / "r.md")
    assert found(root, discover(project, home)) == []


def test_non_md_files_ignored(layout):
    root, home, project = layout
    write(project / ".claude" / "rules" / "a.md")
    write(project / ".claude" / "rules" / "b.txt")
    write(project / ".claude" / "rules" / "c.md.bak")
    files = rules(root, discover(project, home), Scope.PROJECT_RULE)
    assert [f.path.name for f in files] == ["a.md"]


def test_sorted_by_relative_posix_path(layout):
    root, home, project = layout
    base = project / ".claude" / "rules"
    write(base / "b.md")
    write(base / "a" / "z.md")
    write(base / "a.md")
    write(base / "a-b.md")
    files = rules(root, discover(project, home), Scope.PROJECT_RULE)
    assert [f.path.relative_to(base).as_posix() for f in files] == sorted(
        ["b.md", "a/z.md", "a.md", "a-b.md"]
    )
    assert [f.order for f in files] == sorted(f.order for f in files)


def test_frontmatter_and_comments_stripped_from_text_not_raw(layout):
    root, home, project = layout
    content = "---\npaths: src/*.ts\n---\n<!-- hidden -->\nBody\n"
    write(project / ".claude" / "rules" / "r.md", content)
    (f,) = rules(root, discover(project, home), Scope.PROJECT_RULE)
    assert f.raw == content
    assert "paths:" not in f.text
    assert "hidden" not in f.text
    assert "Body" in f.text


def test_brace_glob_paths_intact(layout):
    root, home, project = layout
    write(
        project / ".claude" / "rules" / "r.md",
        '---\npaths: ["src/**/*.{ts,tsx}"]\n---\nBody\n',
    )
    (f,) = rules(root, discover(project, home), Scope.PROJECT_RULE)
    assert f.mode == LoadMode.CONDITIONAL
    assert f.paths == ["src/**/*.{ts,tsx}"]


def test_oversized_rule_is_skipped(layout):
    root, home, project = layout
    path = project / ".claude" / "rules" / "big.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"---\npaths: a\n---\n" + b"x" * (4 * 1024 * 1024))
    (f,) = rules(root, discover(project, home), Scope.PROJECT_RULE)
    assert f.mode == LoadMode.SKIPPED
    assert f.paths is None
    assert f.notes == ["skipped: larger than 4 MiB"]


def test_symlinked_rule_file_returned_once(layout):
    root, home, project = layout
    base = project / ".claude" / "rules"
    target = write(root / "shared" / "t.md")
    base.mkdir(parents=True)
    os.symlink(target, base / "link.md")
    os.symlink(target, base / "other.md")
    files = rules(root, discover(project, home), Scope.PROJECT_RULE)
    assert len(files) == 1
