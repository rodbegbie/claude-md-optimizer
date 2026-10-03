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
        "GH_TOKEN=x gh pr create --title t",
        "/opt/homebrew/bin/gh pr create --title t",
        "command gh pr create --title t",
        "env GH_TOKEN=x gh pr create --title t",
        "git status\ngh pr create --title t",
        "x=`gh pr create --title t`",
        'bash -c "gh pr create --title t"',
        "sh -c 'cd x && gh pr create'",
        "eval gh pr create --title t",
        "echo pr | xargs gh",
        f"gh api --method=POST repos/{UPSTREAM}/issues",
        f"gh api -XPOST repos/{UPSTREAM}/issues",
        f"gh api repos/{FORK}-evil/issues -f title=x",
        f"gh api repos/{UPSTREAM}/issues -f body=repos/{FORK}",
        "gh api graphql -f query=x",
        "gh repo fork",
        "gh repo sync",
        f"gh workflow run ci.yml --repo {UPSTREAM}",
        "gh secret set TOKEN",
        "gh run rerun 123",
        "gh variable set X",
        "gh cache delete --all",
        "gh pr create --title \"it's (unterminated quote",
        'gh issue comment 1 --body "oops',
        'echo "$(gh pr create --title t)"',
        'url="$(gh pr create --title t)"',
        'echo "`gh pr create --title t`"',
        "env -u GH_TOKEN gh pr create --title t",
        "xargs -I {} gh pr create --title t",
        "nice -n 10 gh pr create --title t",
        "sudo -u root gh pr create --title t",
        "timeout 30 gh pr create --title t",
        "if true; then gh pr create --title t; fi",
        "for i in 1; do gh pr create --title t; done",
        "{ gh pr create --title t; }",
        "! gh pr create --title t",
        "cat <(gh pr create --title t)",
        f"gh repo sync {UPSTREAM} --source {FORK}",
        "cat <<'EOF' | gh pr create --title t\nbody\nEOF",
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
        f"gh api repos/{FORK}-x/issues",
        f"gh api --method=GET repos/{UPSTREAM}/issues -f state=open",
        f"gh api -H 'Accept: x' -X POST repos/{FORK}/issues",
        "echo 'gh pr create is blocked'",
        "git status",
        "echo unterminated 'quote",
        f"gh pr create --repo {FORK.upper()}",
        f"gh pr create --repo github.com/{FORK}",
        f"gh pr create --repo https://github.com/{FORK}.git",
        f"gh repo edit {FORK} --description x",
        "gh run list",
        "gh workflow view ci.yml",
        "gh auth status",
        "gh gist create notes.txt",
        f"GH_TOKEN=x gh pr create --repo {FORK}",
        f"bash -c 'gh pr merge 7 --repo {FORK}'",
        "git log --oneline\ngit status",
        f'url="$(gh pr create --repo {FORK} --title t)"',
        "env -u GH_TOKEN gh pr view 7",
        "timeout 30 gh pr view 7",
        "cat > notes.md <<'EOF'\nIt's easy: gh pr create\nEOF",
        f"gh pr create --repo {FORK} --body \"$(cat <<'EOF'\nIt's: gh pr view\nEOF\n)\"",
    ],
)
def test_allows_reads_and_fork_writes(command):
    assert run_hook(command).returncode == 0
