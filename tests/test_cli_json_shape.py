import json
import os
import subprocess
import sys

from conftest import SCRIPT

FILE_KEYS = {
    "path",
    "scope",
    "mode",
    "order",
    "lines",
    "bytes",
    "tokens",
    "notes",
    "paths",
    "imported_by",
    "external",
}
SCOPED = '---\npaths:\n  - "src/**"\n---\n- scoped one\n- scoped two\n'


def run_text(project, home):
    home.mkdir(exist_ok=True)
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(project)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "HOME": str(home)},
    )


def test_json_has_files_totals_unverified(tree, run_cli):
    root = tree({"project/CLAUDE.md": "# Title\n- Use uv.\n"})
    result = run_cli(root / "project")
    assert {
        "files",
        "totals",
        "findings",
        "score",
        "unverified",
        "memory_directory",
    } == set(result)
    assert "session_cost_per_request" not in result
    assert "session_cost_30_turns" not in result
    assert result["files"]
    for entry in result["files"]:
        assert FILE_KEYS <= set(entry)
        assert isinstance(entry["scope"], str)
        assert isinstance(entry["mode"], str)
    assert set(result["totals"]) == {"always", "conditional", "on_demand"}
    assert result["unverified"] == ["COMBINED_LINES"]
    assert set(result["memory_directory"]) == {"path", "found"}


def test_json_valid_for_empty_project(tree, run_cli):
    root = tree({"project/README.txt": "nothing here\n"})
    result = run_cli(root / "project")
    assert result["files"] == []
    assert result["totals"] == {"always": 0, "conditional": 0, "on_demand": 0}
    assert result["findings"] == []
    assert result["score"] == {"value": 100, "deductions": []}


def test_conditional_rule_listed_but_not_counted(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "# Title\n- Use uv.\n",
            "project/.claude/rules/scoped.md": SCOPED,
        }
    )
    result = run_cli(root / "project")
    scoped = [f for f in result["files"] if f["path"].endswith("scoped.md")]
    assert [f["mode"] for f in scoped] == ["conditional"]
    assert scoped[0]["scope"] == "project_rule"
    assert scoped[0]["paths"] == ["src/**"]
    assert result["totals"]["conditional"] > 0
    always = [f for f in result["files"] if f["mode"] == "always"]
    assert result["totals"]["always"] == sum(f["tokens"] for f in always)


def test_files_are_in_load_order(tree, run_cli):
    root = tree(
        {
            "home/.claude/CLAUDE.md": "- user\n",
            "project/CLAUDE.md": "# Title\n@docs/extra.md\n",
            "project/docs/extra.md": "- extra\n",
            "project/.claude/rules/a.md": "- a\n",
        }
    )
    result = run_cli(root / "project")
    orders = [f["order"] for f in result["files"]]
    assert len(orders) >= 3
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders)


def test_import_has_import_scope_and_parent(tree, run_cli):
    root = tree(
        {
            "project/CLAUDE.md": "# Title\n@docs/extra.md\n",
            "project/docs/extra.md": "- extra\n",
        }
    )
    result = run_cli(root / "project")
    imported = [f for f in result["files"] if f["path"].endswith("extra.md")]
    assert [f["scope"] for f in imported] == ["import"]
    assert imported[0]["imported_by"].endswith("CLAUDE.md")


def test_text_mode_reports_context_load(tree):
    root = tree(
        {
            "project/CLAUDE.md": "# Title\n- Use uv.\n",
            "project/.claude/rules/scoped.md": SCOPED,
        }
    )
    proc = run_text(root / "project", root / "home")
    assert proc.returncode == 0, proc.stderr
    assert "Context load" in proc.stdout
    assert "Memory directory:" in proc.stdout
    assert "Unverified limits" in proc.stdout
    assert "session cost" not in proc.stdout.lower()
    assert "compound" not in proc.stdout.lower()


def test_text_mode_empty_project(tree):
    root = tree({"project/README.txt": "nothing\n"})
    proc = run_text(root / "project", root / "home")
    assert proc.returncode == 0, proc.stderr
    assert "No instruction files found" in proc.stdout


BANNED = [
    "per request",
    "every request",
    "each request",
    "per turn",
    "turns",
    "compound",
    "session cost",
]


def test_non_english_messages_make_no_per_request_claims(tree, run_cli):
    cjk = "".join(f"- 请使用中文编写第{i}条说明文档\n" for i in range(20))
    root = tree({"project/CLAUDE.md": "# Title\n" + cjk})
    result = run_cli(root / "project")
    found = [f for f in result["findings"] if f["check_id"] == "non-english"]
    assert found
    proc = run_text(root / "project", root / "home")
    assert proc.returncode == 0, proc.stderr
    assert "Non-English content" in proc.stdout
    texts = [proc.stdout, json.dumps(result)]
    texts += [f["message"] + " " + f["fix"] for f in result["findings"]]
    for text in texts:
        for phrase in BANNED:
            assert phrase not in text.lower()


def test_json_findings_and_score_shape(tree, run_cli):
    root = tree({"project/CLAUDE.md": "# T\n" + "Follow best practices.\n" * 4})
    result = run_cli(root / "project")
    assert result["findings"]
    for entry in result["findings"]:
        assert set(entry) == {
            "check_id",
            "severity",
            "path",
            "line",
            "message",
            "fix",
            "source",
        }
        assert set(entry["source"]) == {"kind", "url"}
    assert set(result["score"]) == {"value", "deductions"}
    assert result["score"]["value"] == 100 - sum(
        d["points"] for d in result["score"]["deductions"]
    )
    for deduction in result["score"]["deductions"]:
        assert set(deduction) == {"check_id", "count", "points", "capped"}


def test_text_mode_shows_groups_deductions_and_score(tree):
    root = tree({"project/CLAUDE.md": "# T\n" + "Follow best practices.\n" * 4})
    proc = run_text(root / "project", root / "home")
    assert proc.returncode == 0, proc.stderr
    assert "Backed by Anthropic docs" in proc.stdout
    assert "Heuristics" in proc.stdout
    assert "Deductions:" in proc.stdout
    assert "Score:" in proc.stdout
