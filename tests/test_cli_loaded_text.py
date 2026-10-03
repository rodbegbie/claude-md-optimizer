import os
import subprocess
import sys

from claude_md.discovery import encode_project_path
from conftest import SCRIPT

CONTENT = "# Title\n- Use uv.\n- Run pytest.\n"


def run_text(project, home):
    home.mkdir(exist_ok=True)
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(project)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "HOME": str(home)},
    )


def test_memory_file_uses_the_loaded_text(tree, run_cli):
    root = tree({"project/CLAUDE.md": CONTENT})
    project = (root / "project").resolve()
    memory = root / "home" / ".claude" / "projects" / encode_project_path(project)
    (memory / "memory").mkdir(parents=True)
    (memory / "memory" / "MEMORY.md").write_text("- entry\n" * 300)
    result = run_cli(project)
    entry = next(f for f in result["files"] if f["scope"] == "memory")
    assert entry["lines"] == 200


def test_project_file_ignores_html_comment_blocks(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "<!--\nmaintainer note\nmore\n-->\n- Use uv.\n- Run pytest.\n"
        }
    )
    result = run_cli(root / "project")
    entry = next(f for f in result["files"] if f["scope"] == "project")
    assert entry["lines"] == 2


def test_rule_file_ignores_frontmatter(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": CONTENT,
            "project/.claude/rules/r.md": "---\ndescription: x\n---\n- a\n- b\n",
        }
    )
    result = run_cli(root / "project")
    entry = next(f for f in result["files"] if f["scope"] == "project_rule")
    assert entry["lines"] == 2


def test_agents_only_project_is_loaded_as_agents_instructions(tree, run_cli):
    root = tree({"project/AGENTS.md": CONTENT})
    result = run_cli(root / "project")
    entry = next(f for f in result["files"] if f["path"].endswith("AGENTS.md"))
    assert entry["scope"] == "agents"
    assert entry["mode"] == "always"
    assert entry["lines"] == 3


def test_agents_only_score_matches_the_same_content_as_claude_md(tree, run_cli):
    vague = "# T\n" + "Follow best practices.\nKeep code clean.\nWrite good code.\n" * 8
    root = tree({"a/AGENTS.md": vague, "b/CLAUDE.md": vague})
    scores = (
        run_cli(root / "a")["score"]["value"],
        run_cli(root / "b")["score"]["value"],
    )
    assert scores[0] == scores[1]
    assert scores[0] < 100


def test_additional_project_level_files_are_loaded_in_order(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": CONTENT,
            "project/.claude/CLAUDE.md": "- second\n",
            "project/CLAUDE.local.md": "- local\n",
        }
    )
    result = run_cli(root / "project")
    loaded = [
        f["path"].split("project/", 1)[1]
        for f in result["files"]
        if "project/" in f["path"]
    ]
    assert loaded == ["CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"]


def test_every_always_on_file_is_listed_and_checked(tree, run_cli):
    vague = "Follow best practices.\n"
    root = tree(
        {
            "project/CLAUDE.md": "@docs/x.md\n" + vague,
            "project/docs/x.md": vague,
            "project/.claude/CLAUDE.md": vague,
            "project/.claude/rules/r.md": vague,
            "project/CLAUDE.local.md": vague,
            "home/.claude/CLAUDE.md": vague,
        }
    )
    result = run_cli(root / "project")
    always = {f["path"] for f in result["files"] if f["mode"] == "always"}
    assert len(always) >= 6
    checked = {
        f["path"] for f in result["findings"] if f["check_id"] == "vague-instruction"
    }
    assert checked == always


def test_text_mode_lists_the_additional_files(tree):
    root = tree(
        {"project/CLAUDE.md": CONTENT, "project/.claude/CLAUDE.md": "- second\n"}
    )
    proc = run_text(root / "project", root / "home")
    assert proc.returncode == 0
    assert ".claude/CLAUDE.md" in proc.stdout
