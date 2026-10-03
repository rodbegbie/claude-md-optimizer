import os
from pathlib import Path

import pytest
from claude_md.discovery import default_managed_dir, discover
from claude_md.model import LoadMode, Scope


@pytest.fixture
def layout(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    project = root / "outer" / "mid" / "proj"
    home.mkdir()
    project.mkdir(parents=True)
    return root, home, project


def write(path: Path, content: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def found(root: Path, files):
    return [f for f in files if f.path.is_relative_to(root)]


def rel(root: Path, files):
    return [str(f.path.relative_to(root)) for f in found(root, files)]


def test_ancestor_order_root_to_cwd(layout):
    root, home, project = layout
    write(project / "CLAUDE.md")
    write(root / "outer" / "CLAUDE.md")
    write(root / "outer" / "mid" / "CLAUDE.md")
    files = found(root, discover(project, home))
    assert [(str(f.path.relative_to(root)), f.scope) for f in files] == [
        ("outer/CLAUDE.md", Scope.ANCESTOR),
        ("outer/mid/CLAUDE.md", Scope.ANCESTOR),
        ("outer/mid/proj/CLAUDE.md", Scope.PROJECT),
    ]
    assert all(f.mode == LoadMode.ALWAYS for f in files)


def test_local_after_sibling(layout):
    root, home, project = layout
    write(project / "CLAUDE.local.md")
    write(project / "CLAUDE.md")
    write(project / ".claude" / "CLAUDE.md")
    write(root / "outer" / "CLAUDE.local.md")
    files = found(root, discover(project, home))
    assert [(str(f.path.relative_to(root)), f.scope) for f in files] == [
        ("outer/CLAUDE.local.md", Scope.LOCAL),
        ("outer/mid/proj/CLAUDE.md", Scope.PROJECT),
        ("outer/mid/proj/.claude/CLAUDE.md", Scope.PROJECT),
        ("outer/mid/proj/CLAUDE.local.md", Scope.LOCAL),
    ]


def test_dot_claude_claude_md_read_only_in_project_dir(layout):
    root, home, project = layout
    write(root / "outer" / ".claude" / "CLAUDE.md")
    write(project / ".claude" / "CLAUDE.md")
    assert rel(root, discover(project, home)) == ["outer/mid/proj/.claude/CLAUDE.md"]


def test_nested_is_on_demand(layout):
    root, home, project = layout
    write(project / "CLAUDE.md")
    write(project / "b" / "CLAUDE.md")
    write(project / "a" / "deep" / "CLAUDE.md")
    files = found(root, discover(project, home))
    assert [
        (f.path.relative_to(project).as_posix(), f.scope, f.mode) for f in files
    ] == [
        ("CLAUDE.md", Scope.PROJECT, LoadMode.ALWAYS),
        ("a/deep/CLAUDE.md", Scope.NESTED, LoadMode.ON_DEMAND),
        ("b/CLAUDE.md", Scope.NESTED, LoadMode.ON_DEMAND),
    ]


def test_nested_pruning(layout):
    root, home, project = layout
    for skipped in ("node_modules", ".git", ".hidden", "__pycache__", "venv", ".venv"):
        write(project / skipped / "CLAUDE.md")
    write(project / "src" / "node_modules" / "CLAUDE.md")
    write(project / "src" / "CLAUDE.md")
    assert rel(root, discover(project, home)) == ["outer/mid/proj/src/CLAUDE.md"]


def test_managed_loads_first(layout):
    root, home, project = layout
    managed = root / "managed"
    write(managed / "CLAUDE.md")
    write(project / "CLAUDE.md")
    files = discover(project, home, managed)
    assert files[0].path == managed / "CLAUDE.md"
    assert files[0].scope == Scope.MANAGED
    assert files[0].mode == LoadMode.ALWAYS


def test_user_after_managed_before_ancestors(layout):
    root, home, project = layout
    managed = root / "managed"
    write(managed / "CLAUDE.md")
    write(home / ".claude" / "CLAUDE.md")
    write(root / "outer" / "CLAUDE.md")
    files = found(root, discover(project, home, managed))
    assert [f.scope for f in files] == [Scope.MANAGED, Scope.USER, Scope.ANCESTOR]


def test_orders_strictly_increase_from_zero(layout):
    _root, home, project = layout
    write(home / ".claude" / "CLAUDE.md")
    write(project / "CLAUDE.md")
    write(project / "sub" / "CLAUDE.md")
    files = discover(project, home)
    assert [f.order for f in files] == list(range(len(files)))


def test_home_as_cwd_is_not_double_counted(layout):
    root, home, _ = layout
    write(home / ".claude" / "CLAUDE.md")
    write(home / "CLAUDE.md")
    files = found(root, discover(home, home))
    assert [(str(f.path.relative_to(root)), f.scope) for f in files] == [
        ("home/.claude/CLAUDE.md", Scope.USER),
        ("home/CLAUDE.md", Scope.PROJECT),
    ]
    paths = [f.path for f in files]
    assert len(paths) == len(set(paths))


def test_symlinked_duplicate_is_skipped(layout):
    root, home, project = layout
    real = write(root / "shared.md")
    project.joinpath("CLAUDE.md").symlink_to(real)
    project.joinpath("CLAUDE.local.md").symlink_to(real)
    assert rel(root, discover(project, home)) == ["outer/mid/proj/CLAUDE.md"]


def test_symlinked_directories_are_not_followed(layout):
    root, home, project = layout
    write(root / "elsewhere" / "CLAUDE.md")
    project.mkdir(exist_ok=True)
    (project / "link").symlink_to(root / "elsewhere", target_is_directory=True)
    assert rel(root, discover(project, home)) == []


def test_empty_file_is_loaded_with_zero_lines(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "")
    (file,) = found(root, discover(project, home))
    assert file.mode == LoadMode.ALWAYS
    assert file.lines == 0
    assert file.notes == []


def test_invalid_utf8_is_read_with_replacement_and_noted(layout):
    root, home, project = layout
    (project / "CLAUDE.md").write_bytes(b"ok \xff\xfe bad\n")
    (file,) = found(root, discover(project, home))
    assert file.mode == LoadMode.ALWAYS
    assert "�" in file.raw
    assert "invalid UTF-8 replaced" in file.notes


def test_bom_is_stripped(layout):
    root, home, project = layout
    (project / "CLAUDE.md").write_bytes(b"\xef\xbb\xbfhello\n")
    (file,) = found(root, discover(project, home))
    assert file.raw == "hello\n"
    assert file.notes == []


def test_file_over_4_mib_is_skipped(layout):
    root, home, project = layout
    (project / "CLAUDE.md").write_bytes(b"a" * (4 * 1024 * 1024 + 1))
    (file,) = found(root, discover(project, home))
    assert file.mode == LoadMode.SKIPPED
    assert file.raw == ""
    assert file.text == ""
    assert "skipped: larger than 4 MiB" in file.notes


@pytest.mark.skipif(
    not hasattr(os, "geteuid") or os.geteuid() == 0, reason="needs a non-root user"
)
def test_unreadable_file_is_skipped_with_note(layout):
    root, home, project = layout
    target = write(project / "CLAUDE.md")
    target.chmod(0o000)
    try:
        (file,) = found(root, discover(project, home))
    finally:
        target.chmod(0o644)
    assert file.mode == LoadMode.SKIPPED
    assert file.raw == ""
    assert "skipped: unreadable (PermissionError)" in file.notes


def test_directory_named_claude_md_is_skipped_not_raised(layout):
    root, home, project = layout
    (project / "CLAUDE.md").mkdir()
    (file,) = found(root, discover(project, home))
    assert file.mode == LoadMode.SKIPPED
    assert any(n.startswith("skipped: unreadable (") for n in file.notes)


def test_default_managed_dir_is_a_path_or_none():
    result = default_managed_dir()
    assert result is None or isinstance(result, Path)
