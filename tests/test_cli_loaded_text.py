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


def analysed_paths(result):
    singles = [
        result["project_claude_md"],
        result["user_claude_md"],
        result["memory_md"],
    ]
    analyses = [a for a in singles if a] + result["rules_files"] + result["other_files"]
    return {a["path"] for a in analyses}


def test_memory_analysis_uses_the_loaded_text(tree, run_cli):
    root = tree({"project/CLAUDE.md": CONTENT})
    project = (root / "project").resolve()
    memory = root / "home" / ".claude" / "projects" / encode_project_path(project)
    (memory / "memory").mkdir(parents=True)
    (memory / "memory" / "MEMORY.md").write_text("- entry\n" * 300)
    result = run_cli(project)
    entry = next(f for f in result["files"] if f["scope"] == "memory")
    assert entry["lines"] == 200
    assert result["memory_md"]["line_count"] == 200


def test_project_analysis_ignores_html_comment_blocks(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "<!--\nmaintainer note\nmore\n-->\n- Use uv.\n- Run pytest.\n"
        }
    )
    result = run_cli(root / "project")
    assert result["project_claude_md"]["line_count"] == 2


def test_rule_analysis_ignores_frontmatter(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": CONTENT,
            "project/.claude/rules/r.md": "---\ndescription: x\n---\n- a\n- b\n",
        }
    )
    result = run_cli(root / "project")
    assert result["rules_files"][0]["line_count"] == 2


def test_agents_only_project_is_analysed_as_project_instructions(tree, run_cli):
    root = tree({"project/AGENTS.md": CONTENT})
    result = run_cli(root / "project")
    assert result["project_claude_md"] is not None
    assert result["project_claude_md"]["path"].endswith("AGENTS.md")
    assert result["project_claude_md"]["line_count"] == 3


def test_agents_only_score_matches_the_same_content_as_claude_md(tree, run_cli):
    vague = "# T\n" + "Follow best practices.\nKeep code clean.\nWrite good code.\n" * 8
    root = tree({"a/AGENTS.md": vague, "b/CLAUDE.md": vague})
    scores = run_cli(root / "a")["overall_score"], run_cli(root / "b")["overall_score"]
    assert scores[0] == scores[1]
    assert scores[0] < 100


def test_additional_project_level_files_are_analysed(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": CONTENT,
            "project/.claude/CLAUDE.md": "- second\n",
            "project/CLAUDE.local.md": "- local\n",
        }
    )
    result = run_cli(root / "project")
    assert result["project_claude_md"]["path"].endswith("project/CLAUDE.md")
    assert [a["path"].split("project/", 1)[1] for a in result["other_files"]] == [
        ".claude/CLAUDE.md",
        "CLAUDE.local.md",
    ]


def test_every_always_on_file_is_analysed(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "@docs/x.md\n- Use uv.\n",
            "project/docs/x.md": "- imported\n",
            "project/.claude/CLAUDE.md": "- second\n",
            "project/.claude/rules/r.md": "- rule\n",
            "project/CLAUDE.local.md": "- local\n",
            "home/.claude/CLAUDE.md": "- user\n",
        }
    )
    result = run_cli(root / "project")
    always = {f["path"] for f in result["files"] if f["mode"] == "always"}
    assert len(always) >= 6
    assert analysed_paths(result) == always


def test_text_mode_lists_the_additional_files(tree):
    root = tree(
        {"project/CLAUDE.md": CONTENT, "project/.claude/CLAUDE.md": "- second\n"}
    )
    proc = run_text(root / "project", root / "home")
    assert proc.returncode == 0
    assert "Other instruction file" in proc.stdout
    assert ".claude/CLAUDE.md" in proc.stdout
