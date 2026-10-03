from claude_md.discovery import encode_project_path

BULLETS = "- Use uv.\n"


def entry(result, suffix):
    matches = [f for f in result["files"] if f["path"].endswith(suffix)]
    assert len(matches) == 1, suffix
    return matches[0]


def test_memory_file_is_classified_as_memory(tree, run_cli):
    root = tree({"project/CLAUDE.md": BULLETS})
    project = (root / "project").resolve()
    memory = root / "home" / ".claude" / "projects" / encode_project_path(project)
    (memory / "memory").mkdir(parents=True)
    (memory / "memory" / "MEMORY.md").write_text("- entry\n" * 300)
    result = run_cli(project)
    memory_file = entry(result, "MEMORY.md")
    assert memory_file["scope"] == "memory"
    assert memory_file["lines"] == 200
    flagged = [f for f in result["findings"] if f["path"] == memory_file["path"]]
    assert {f["check_id"] for f in flagged} == {"size-memory"}


def test_project_dot_claude_claude_md_is_not_user_level(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": BULLETS,
            "project/.claude/CLAUDE.md": BULLETS * 80,
        }
    )
    other = entry(run_cli(root / "project"), ".claude/CLAUDE.md")
    assert other["lines"] == 80
    assert other["scope"] == "project"


def test_real_user_claude_md_is_classified_as_user(tree, run_cli):
    root = tree({"project/CLAUDE.md": BULLETS, "home/.claude/CLAUDE.md": BULLETS * 60})
    user = entry(run_cli(root / "project"), "home/.claude/CLAUDE.md")
    assert user["scope"] == "user"
    assert user["lines"] == 60
    assert user["mode"] == "always"


def test_project_in_a_directory_named_rules_is_not_a_rule_file(tree, run_cli):
    root = tree({"rules-engine/proj/CLAUDE.md": BULLETS * 40})
    project = entry(run_cli(root / "rules-engine" / "proj"), "proj/CLAUDE.md")
    assert project["scope"] == "project"


def test_real_rule_file_is_classified_as_a_rule(tree, run_cli):
    root = tree(
        {"project/CLAUDE.md": BULLETS, "project/.claude/rules/r.md": BULLETS * 40}
    )
    rule = entry(run_cli(root / "project"), ".claude/rules/r.md")
    assert rule["scope"] == "project_rule"
    assert rule["lines"] == 40


def test_long_project_file_finding_makes_no_truncation_claim(tree, run_cli):
    root = tree({"project/CLAUDE.md": BULLETS * 250})
    findings = run_cli(root / "project")["findings"]
    size = [f for f in findings if f["check_id"] == "size-file"]
    assert len(size) == 1
    assert "250 lines" in size[0]["message"]
    text = " ".join([size[0]["message"], size[0]["fix"]])
    assert "truncation" not in text.lower()
    assert "silent" not in text.lower()
