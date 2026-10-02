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
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)

    def run(project: Path) -> dict:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(project), "--json"],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "HOME": str(home)},
        )
        return json.loads(proc.stdout)

    return run
