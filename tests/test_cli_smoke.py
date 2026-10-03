def test_cli_runs_on_minimal_project(tree, run_cli):
    root = tree({"project/CLAUDE.md": "# Title\n- Use uv.\n"})
    result = run_cli(root / "project")
    assert isinstance(result["score"]["value"], int)
    assert 0 <= result["score"]["value"] <= 100
    assert [f["lines"] for f in result["files"] if f["scope"] == "project"] == [2]
