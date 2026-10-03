def test_cli_runs_on_minimal_project(tree, run_cli):
    root = tree({"project/CLAUDE.md": "# Title\n- Use uv.\n"})
    result = run_cli(root / "project")
    assert "value" in result["score"]
    assert [f["lines"] for f in result["files"] if f["scope"] == "project"] == [2]
