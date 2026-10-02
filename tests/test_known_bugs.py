import pytest

TEN_LINES = "".join(f"- memory line {i}\n" for i in range(10))
FIFTY_LINES = "".join(f"- rule line {i}\n" for i in range(50))


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="memory is taken from another project's memory dir",
)
def test_memory_comes_from_current_project(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "# Title\n- Use uv.\n",
            "home/.claude/projects/-other/memory/MEMORY.md": TEN_LINES,
        }
    )
    result = run_cli(root / "project")
    assert result["memory_md"] is None


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="rules in subdirectories are not discovered",
)
def test_rules_are_scanned_recursively(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "# Title\n- Use uv.\n",
            "project/.claude/rules/a/b.md": "- nested rule\n",
        }
    )
    result = run_cli(root / "project")
    assert len(result["rules_files"]) == 1


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="path-scoped rules are counted as always-on lines",
)
def test_path_scoped_rules_do_not_count_as_always_on(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "# Title\n- Use uv.\n- Use ruff.\n",
            "project/.claude/rules/scoped.md": (
                '---\npaths:\n  - "src/**"\n---\n' + FIFTY_LINES
            ),
        }
    )
    result = run_cli(root / "project")
    assert result["total_lines"] == 3
