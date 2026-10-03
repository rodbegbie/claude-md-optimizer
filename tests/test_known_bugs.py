from claude_md.discovery import encode_project_path

TEN_LINES = "".join(f"- memory line {i}\n" for i in range(10))
FIFTY_LINES = "".join(f"- rule line {i}\n" for i in range(50))


def test_memory_comes_from_current_project(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "# Title\n- Use uv.\n",
            "home/.claude/projects/-other/memory/MEMORY.md": TEN_LINES,
        }
    )
    result = run_cli(root / "project")
    assert [f for f in result["files"] if f["scope"] == "memory"] == []


def test_memory_for_current_project_is_reported(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "# Title\n- Use uv.\n",
            "home/.claude/projects/-other/memory/MEMORY.md": TEN_LINES,
        }
    )
    project = (root / "project").resolve()
    memory = root / "home" / ".claude" / "projects" / encode_project_path(project)
    (memory / "memory").mkdir(parents=True)
    (memory / "memory" / "MEMORY.md").write_text("- a\n- b\n- c\n")
    result = run_cli(project)
    memory = next(f for f in result["files"] if f["scope"] == "memory")
    assert memory["lines"] == 3
    assert result["memory_directory"]["found"] is True


def test_rules_are_scanned_recursively(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "# Title\n- Use uv.\n",
            "project/.claude/rules/a/b.md": "- nested rule\n",
        }
    )
    result = run_cli(root / "project")
    rules = [f for f in result["files"] if f["scope"] == "project_rule"]
    assert len(rules) == 1
    assert rules[0]["path"].endswith("a/b.md")


def test_path_scoped_rules_do_not_count_as_always_on(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "# Title\n- Use uv.\n- Use ruff.\n",
            "project/.claude/rules/scoped.md": (
                '---\npaths:\n  - "src/**"\n---\n' + FIFTY_LINES
            ),
            "project/.claude/rules/always.md": "- always one\n- always two\n",
        }
    )
    result = run_cli(root / "project")
    by_scope = {f["scope"]: f for f in result["files"] if f["mode"] == "always"}
    assert by_scope["project"]["lines"] == 3
    assert by_scope["project_rule"]["lines"] == 2
    assert result["totals"]["always"] == sum(
        f["tokens"] for f in result["files"] if f["mode"] == "always"
    )
    assert sum(f["lines"] for f in result["files"] if f["mode"] == "always") == 3 + 2
