def test_cli_runs_on_minimal_project(tree, run_cli):
    root = tree({"project/CLAUDE.md": "# Title\n- Use uv.\n"})
    result = run_cli(root / "project")
    assert "overall_score" in result
    assert result["project_claude_md"]["line_count"] == 2
