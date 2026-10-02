from pathlib import Path

from claude_md.discovery import discover
from claude_md.model import LoadMode, Scope


def write(path: Path, content: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def run(root: Path, project: Path, home: Path):
    files = discover(project, home)
    return {
        str(f.path.relative_to(root)): f for f in files if f.path.is_relative_to(root)
    }


def test_user_claude_md_does_not_suppress_agents_under_home(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    project = home / "work" / "proj"
    write(home / ".claude" / "CLAUDE.md")
    write(project / "AGENTS.md", "agent rules\n")
    write(project / "sub" / "AGENTS.md")
    files = run(root, project, home)
    assert files["home/.claude/CLAUDE.md"].scope == Scope.USER
    assert files["home/work/proj/AGENTS.md"].mode == LoadMode.ALWAYS
    assert files["home/work/proj/sub/AGENTS.md"].mode == LoadMode.ON_DEMAND


def test_user_claude_md_does_not_suppress_agents_when_project_is_home(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    write(home / ".claude" / "CLAUDE.md")
    write(home / "AGENTS.md")
    files = run(root, home, home)
    assert files["home/AGENTS.md"].mode == LoadMode.ALWAYS


def test_claude_md_in_home_directory_itself_still_suppresses_agents(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    project = home / "work" / "proj"
    write(home / "CLAUDE.md")
    write(project / "AGENTS.md")
    files = run(root, project, home)
    assert files["home/work/proj/AGENTS.md"].mode == LoadMode.DORMANT


def test_dot_claude_claude_md_between_home_and_project_still_suppresses(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    project = home / "work" / "proj"
    write(home / ".claude" / "CLAUDE.md")
    write(home / "work" / ".claude" / "CLAUDE.md")
    write(project / "AGENTS.md")
    files = run(root, project, home)
    assert files["home/work/proj/AGENTS.md"].mode == LoadMode.DORMANT


def test_dormant_note_explains_unloaded_ancestor_dot_claude_cause(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    project = home / "work" / "proj"
    cause = write(home / "work" / ".claude" / "CLAUDE.md")
    write(project / "AGENTS.md")
    files = run(root, project, home)
    assert cause.relative_to(root).as_posix() not in files
    notes = " ".join(files["home/work/proj/AGENTS.md"].notes)
    assert "not loaded by this tool" in notes
    assert "unverified" in notes
    assert "home/work/.claude/CLAUDE.md" in notes


def test_dormant_note_unchanged_for_a_loaded_cause(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    project = home / "work" / "proj"
    write(project / "CLAUDE.md")
    write(project / "AGENTS.md")
    files = run(root, project, home)
    assert files["home/work/proj/AGENTS.md"].notes == [
        "AGENTS.md not loaded: a CLAUDE.md exists at or above the working directory"
    ]
