import json
from pathlib import Path

import pytest
from claude_md.discovery import (
    discover,
    encode_project_path,
    find_git_root,
    memory_dir,
)
from claude_md.model import LoadMode, Scope


@pytest.fixture
def layout(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    repo = root / "repo"
    home.mkdir()
    (repo / ".git").mkdir(parents=True)
    return root, home, repo


def write(path: Path, content: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def mem(home: Path, repo: Path) -> Path:
    return memory_dir(repo, home)


def memory_files(home: Path, project: Path):
    return [f for f in discover(project, home) if f.scope == Scope.MEMORY]


def test_encode_project_path_simple():
    assert encode_project_path(Path("/Users/rod/x")) == "-Users-rod-x"


def test_encode_handles_spaces_dots_unicode():
    assert encode_project_path(Path("/a/.claude/worktrees/fix+y")) == (
        "-a--claude-worktrees-fix-y"
    )
    assert encode_project_path(Path("/My Proj/a.b_c-d")) == "-My-Proj-a-b-c-d"
    assert encode_project_path(Path("/café/日本")) == "-caf----"


def test_find_git_root_plain_repo(layout):
    _, _, repo = layout
    assert find_git_root(repo) == repo


def test_find_git_root_from_subdirectory(layout):
    _, _, repo = layout
    sub = repo / "a" / "b"
    sub.mkdir(parents=True)
    assert find_git_root(sub) == repo


def test_find_git_root_linked_worktree_returns_main_repo(layout):
    root, _, repo = layout
    gitdir = repo / ".git" / "worktrees" / "wt"
    gitdir.mkdir(parents=True)
    wt = root / "wt"
    write(wt / ".git", f"gitdir: {gitdir}\n")
    assert find_git_root(wt) == repo


def test_find_git_root_relative_gitdir(layout):
    root, _, repo = layout
    (repo / ".git" / "worktrees" / "wt").mkdir(parents=True)
    wt = root / "wt"
    write(wt / ".git", "gitdir: ../repo/.git/worktrees/wt\n")
    assert find_git_root(wt) == repo


def test_find_git_root_submodule_returns_ancestor(layout):
    _, _, repo = layout
    gitdir = repo / ".git" / "modules" / "sub"
    gitdir.mkdir(parents=True)
    sub = repo / "sub"
    write(sub / ".git", f"gitdir: {gitdir}\n")
    assert find_git_root(sub) == sub


def test_find_git_root_none_without_repo(tmp_path):
    plain = tmp_path.resolve() / "plain"
    plain.mkdir()
    if any((d / ".git").exists() for d in [plain, *plain.parents]):
        pytest.skip("tmp directory is inside a git repository")
    assert find_git_root(plain) is None


def test_find_git_root_garbage_git_file(layout):
    root, _, _ = layout
    odd = root / "odd"
    write(odd / ".git", "not a gitdir line\n")
    assert find_git_root(odd) == odd


def test_find_git_root_binary_git_file(layout):
    root, _, _ = layout
    odd = root / "odd"
    odd.mkdir()
    (odd / ".git").write_bytes(b"\xff\xfe\x00\x01")
    assert find_git_root(odd) == odd


def test_memory_dir_same_for_subdirectory_and_worktree(layout):
    root, home, repo = layout
    sub = repo / "pkg"
    sub.mkdir()
    gitdir = repo / ".git" / "worktrees" / "wt"
    gitdir.mkdir(parents=True)
    wt = root / "wt"
    write(wt / ".git", f"gitdir: {gitdir}\n")
    expected = home / ".claude" / "projects" / encode_project_path(repo) / "memory"
    assert memory_dir(repo, home) == expected
    assert memory_dir(sub, home) == expected
    assert memory_dir(wt, home) == expected


def test_memory_dir_outside_git_uses_project_dir(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    home.mkdir()
    project = root / "plain" / "proj"
    project.mkdir(parents=True)
    if find_git_root(project) is not None:
        pytest.skip("tmp directory is inside a git repository")
    expected = home / ".claude" / "projects" / encode_project_path(project) / "memory"
    assert memory_dir(project, home) == expected


def settings(base: Path, value, name="settings.json") -> None:
    write(base / ".claude" / name, json.dumps({"autoMemoryDirectory": value}))


def test_auto_memory_directory_absolute(layout):
    root, home, repo = layout
    target = root / "elsewhere"
    settings(repo, str(target))
    assert memory_dir(repo, home) == target


def test_auto_memory_directory_tilde(layout):
    _, home, repo = layout
    settings(home, "~/mem")
    assert memory_dir(repo, home) == home / "mem"


def test_auto_memory_directory_relative_ignored(layout):
    _, home, repo = layout
    settings(repo, "relative/mem")
    assert memory_dir(repo, home).name == "memory"
    assert memory_dir(repo, home).parent.parent == home / ".claude" / "projects"


def test_auto_memory_directory_last_valid_scope_wins(layout):
    root, home, repo = layout
    settings(home, str(root / "one"))
    settings(home, str(root / "two"), "settings.local.json")
    settings(repo, str(root / "three"))
    settings(repo, "relative", "settings.local.json")
    assert memory_dir(repo, home) == root / "three"


def test_auto_memory_directory_malformed_settings_ignored(layout):
    root, home, repo = layout
    settings(home, str(root / "one"))
    write(repo / ".claude" / "settings.json", "{not json")
    settings(repo, 5, "settings.local.json")
    assert memory_dir(repo, home) == root / "one"


def test_memory_from_current_project_only(layout):
    root, home, repo = layout
    other = root / "other"
    (other / ".git").mkdir(parents=True)
    write(mem(home, repo) / "MEMORY.md", "mine\n")
    write(mem(home, other) / "MEMORY.md", "theirs\n")
    found = memory_files(home, repo)
    assert [f.path for f in found] == [mem(home, repo) / "MEMORY.md"]
    assert found[0].mode == LoadMode.ALWAYS
    assert found[0].text == "mine\n"
    assert all(f.path != mem(home, other) / "MEMORY.md" for f in found)


def test_memory_found_from_repo_subdirectory(layout):
    _, home, repo = layout
    sub = repo / "pkg"
    sub.mkdir()
    write(mem(home, repo) / "MEMORY.md", "mine\n")
    assert [f.text for f in memory_files(home, sub)] == ["mine\n"]


def test_memory_truncated_at_200_lines(layout):
    _, home, repo = layout
    write(mem(home, repo) / "MEMORY.md", "".join(f"l{i}\n" for i in range(237)))
    f = memory_files(home, repo)[0]
    assert f.text.count("\n") == 200
    assert f.text.endswith("l199\n")
    assert len(f.raw.splitlines()) == 237
    assert "truncated: only the first 200 lines load; 37 lines dropped" in f.notes


def test_memory_truncated_at_25kb(layout):
    _, home, repo = layout
    write(mem(home, repo) / "MEMORY.md", ("y" * 199 + "\n") * 150)
    f = memory_files(home, repo)[0]
    assert len(f.text.encode()) == 25 * 1024
    assert any(
        n.startswith("truncated: only the first 25600 bytes load; ") for n in f.notes
    )


def test_memory_byte_cut_never_splits_a_character(layout):
    _, home, repo = layout
    write(mem(home, repo) / "MEMORY.md", "é" * 20000)
    f = memory_files(home, repo)[0]
    assert "�" not in f.text
    assert set(f.text) == {"é"}
    assert len(f.text.encode()) == 25 * 1024


def test_memory_both_limits_reports_stricter(layout):
    _, home, repo = layout
    write(mem(home, repo) / "MEMORY.md", ("z" * 299 + "\n") * 300)
    f = memory_files(home, repo)[0]
    assert len(f.text.encode()) <= 25 * 1024
    assert f.text.count("\n") < 200
    assert any("25600 bytes" in n for n in f.notes)
    assert not any("200 lines" in n for n in f.notes)


def test_memory_html_comments_stripped_before_measuring(layout):
    _, home, repo = layout
    body = "".join(f"l{i}\n" for i in range(150))
    padded = "<!--\n" + "filler\n" * 100 + "-->\n" + body
    write(mem(home, repo) / "MEMORY.md", padded)
    f = memory_files(home, repo)[0]
    assert f.text.count("l149") == 1
    assert not any(n.startswith("truncated") for n in f.notes)


def test_untruncated_memory_has_no_note(layout):
    _, home, repo = layout
    write(mem(home, repo) / "MEMORY.md", "short\n")
    assert memory_files(home, repo)[0].notes == []


def test_topic_files_on_demand(layout):
    _, home, repo = layout
    d = mem(home, repo)
    write(d / "MEMORY.md", "index\n")
    write(d / "user_role.md", "role\n")
    write(d / "feedback_testing.md", "fb\n")
    write(d / "notes.txt", "ignored\n")
    write(d / "sub" / "deep.md", "ignored\n")
    found = memory_files(home, repo)
    assert [(f.path.name, f.mode) for f in found] == [
        ("MEMORY.md", LoadMode.ALWAYS),
        ("feedback_testing.md", LoadMode.ON_DEMAND),
        ("user_role.md", LoadMode.ON_DEMAND),
    ]
    assert found[1].raw == "fb\n"


def test_only_topic_files_without_memory_md(layout):
    _, home, repo = layout
    write(mem(home, repo) / "topic.md", "t\n")
    found = memory_files(home, repo)
    assert [(f.path.name, f.mode) for f in found] == [("topic.md", LoadMode.ON_DEMAND)]


def test_missing_memory_dir_returns_nothing(layout):
    _, home, repo = layout
    assert memory_files(home, repo) == []


def test_empty_memory_dir_returns_nothing(layout):
    _, home, repo = layout
    mem(home, repo).mkdir(parents=True)
    assert memory_files(home, repo) == []


def test_excludes_do_not_apply_to_memory(layout):
    _, home, repo = layout
    write(mem(home, repo) / "MEMORY.md", "m\n")
    write(
        repo / ".claude" / "settings.json",
        json.dumps({"claudeMdExcludes": ["**/*.md"]}),
    )
    assert memory_files(home, repo)[0].mode == LoadMode.ALWAYS


def test_imports_not_expanded_in_memory(layout):
    _, home, repo = layout
    write(mem(home, repo) / "MEMORY.md", "@other.md\n")
    write(mem(home, repo) / "other.md", "o\n")
    files = discover(repo, home)
    assert not any(f.scope == Scope.IMPORT for f in files)


def test_load_order_memory_after_local_before_nested(layout):
    _, home, repo = layout
    write(repo / "CLAUDE.md", "p\n")
    write(repo / "CLAUDE.local.md", "l\n")
    write(repo / "pkg" / "CLAUDE.md", "n\n")
    write(mem(home, repo) / "MEMORY.md", "m\n")
    write(mem(home, repo) / "topic.md", "t\n")
    files = discover(repo, home)
    names = [
        (f.scope, f.path.name) for f in files if f.path.is_relative_to(home.parent)
    ]
    assert names == [
        (Scope.PROJECT, "CLAUDE.md"),
        (Scope.LOCAL, "CLAUDE.local.md"),
        (Scope.MEMORY, "MEMORY.md"),
        (Scope.MEMORY, "topic.md"),
        (Scope.NESTED, "CLAUDE.md"),
    ]
    assert [f.order for f in files] == list(range(len(files)))
