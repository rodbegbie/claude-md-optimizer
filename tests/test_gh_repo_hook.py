import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / ".claude/hooks/require-gh-repo.py"
FORK = "rodbegbie/claude-md-optimizer"
UPSTREAM = "geuneda/claude-md-optimizer"


def run_hook(command: str) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --title x",
        f"gh pr create --repo {UPSTREAM}",
        f"gh pr merge 7 --repo {UPSTREAM} --merge",
        "gh issue comment 4 --body hi",
        "cd x && gh pr ready 7",
        f"gh api repos/{UPSTREAM}/issues -f title=x",
        f"gh api -X POST repos/{UPSTREAM}/issues",
        "gh release create v1",
        "echo $(gh pr create --title x)",
    ],
)
def test_blocks_writes_not_aimed_at_the_fork(command):
    result = run_hook(command)
    assert result.returncode == 2
    assert "fork-only" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        f"gh pr create --repo {FORK} --draft",
        f"gh pr merge 7 --repo {FORK} --merge",
        f"gh pr create -R {FORK}",
        f"gh pr create --repo={FORK}",
        "gh pr view 7",
        f"gh pr list --repo {UPSTREAM}",
        "gh pr checks 7 || true",
        f"gh api repos/{FORK}/issues -f title=x",
        f"gh api repos/{UPSTREAM}/issues",
        "echo 'gh pr create is blocked'",
        "git status",
    ],
)
def test_allows_reads_and_fork_writes(command):
    assert run_hook(command).returncode == 0
