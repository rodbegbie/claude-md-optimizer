from claude_md.discovery import encode_project_path

BULLETS = "- Use uv.\n"


def messages(analysis):
    return analysis["issues"] + analysis["warnings"] + analysis["suggestions"]


def test_memory_file_is_not_reported_as_user_level_claude_md(tree, run_cli):
    root = tree({"project/CLAUDE.md": BULLETS})
    project = (root / "project").resolve()
    memory = root / "home" / ".claude" / "projects" / encode_project_path(project)
    (memory / "memory").mkdir(parents=True)
    (memory / "memory" / "MEMORY.md").write_text("- entry\n" * 300)
    result = run_cli(project)
    assert result["memory_md"]["line_count"] == 200
    assert not any("User-level" in m for m in messages(result["memory_md"]))


def test_project_dot_claude_claude_md_is_not_user_level(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": BULLETS,
            "project/.claude/CLAUDE.md": BULLETS * 80,
        }
    )
    other = run_cli(root / "project")["other_files"][0]
    assert other["line_count"] == 80
    assert not any("User-level" in m for m in messages(other))


def test_real_user_claude_md_gets_the_user_level_check(tree, run_cli):
    root = tree({"project/CLAUDE.md": BULLETS, "home/.claude/CLAUDE.md": BULLETS * 60})
    user = run_cli(root / "project")["user_claude_md"]
    assert any("User-level CLAUDE.md has 60 lines" in m for m in user["issues"])


def test_project_in_a_directory_named_rules_is_not_a_rule_file(tree, run_cli):
    root = tree({"rules-engine/proj/CLAUDE.md": BULLETS * 40})
    project = run_cli(root / "rules-engine" / "proj")["project_claude_md"]
    assert not any("Rule file" in m for m in messages(project))


def test_real_rule_file_gets_the_rule_file_check(tree, run_cli):
    root = tree(
        {"project/CLAUDE.md": BULLETS, "project/.claude/rules/r.md": BULLETS * 40}
    )
    rule = run_cli(root / "project")["rules_files"][0]
    assert any("Rule file has 40 lines" in m for m in rule["warnings"])


def test_long_project_file_message_makes_no_truncation_claim(tree, run_cli):
    root = tree({"project/CLAUDE.md": BULLETS * 160})
    project = run_cli(root / "project")["project_claude_md"]
    text = " ".join(messages(project))
    assert "Project CLAUDE.md has 160 lines" in text
    assert "may reduce adherence" in text
    assert "truncation" not in text.lower()
    assert "silent" not in text.lower()
