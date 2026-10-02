import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "claude-md-optimizer"
    / "scripts"
    / "analyze_claude_md.py"
)


@pytest.fixture
def tree(tmp_path):
    def build(files: dict[str, str]) -> Path:
        for rel, content in files.items():
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return tmp_path

    return build


@pytest.fixture
def run_cli(tmp_path):
    """Run the analyser with HOME set to tmp_path/home.

    The fake home sits beside the tree built by `tree`, so pass a project
    subdirectory such as tmp_path / "project", never tmp_path itself, or the
    fake home is analysed as project content.
    """
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)

    def run(project: Path) -> dict:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(project), "--json"],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "HOME": str(home)},
        )
        assert proc.returncode == 0, (
            f"analyser exited {proc.returncode}:\n{proc.stderr}"
        )
        return json.loads(proc.stdout)

    return run
