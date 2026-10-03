#!/usr/bin/env python3
"""PreToolUse hook (matcher: Bash): gh writes must target the fork."""

import json
import shlex
import sys

FORK = "rodbegbie/claude-md-optimizer"
OPERATORS = {";", "&&", "||", "|", "&", "(", ")"}
WRITE_VERBS = {
    "pr": {
        "create",
        "edit",
        "comment",
        "merge",
        "ready",
        "close",
        "reopen",
        "review",
        "revert",
        "update-branch",
    },
    "issue": {
        "create",
        "edit",
        "comment",
        "close",
        "reopen",
        "delete",
        "transfer",
        "pin",
        "unpin",
        "lock",
        "unlock",
    },
    "release": {"create", "edit", "delete", "upload", "delete-asset"},
    "label": {"create", "edit", "delete", "clone"},
    "repo": {"edit", "delete", "rename", "archive", "unarchive"},
}
API_WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


def segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    result: list[list[str]] = [[]]
    for token in lexer:
        if token in OPERATORS:
            result.append([])
        else:
            result[-1].append(token)
    return [segment for segment in result if segment]


def repo_flag(args: list[str]) -> str | None:
    for i, arg in enumerate(args):
        if arg in ("--repo", "-R") and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--repo="):
            return arg.split("=", 1)[1]
    return None


def api_is_write(args: list[str]) -> bool:
    for i, arg in enumerate(args):
        if arg in ("-X", "--method") and i + 1 < len(args):
            return args[i + 1].upper() in API_WRITE_METHODS
        if arg in ("-f", "-F", "--field", "--raw-field", "--input"):
            return True
    return False


def problem(tokens: list[str]) -> str | None:
    if not tokens or tokens[0] != "gh":
        return None
    args = tokens[1:]
    if args[:1] == ["api"]:
        if api_is_write(args) and f"repos/{FORK}" not in " ".join(args):
            return f"gh api writes must use a path under repos/{FORK}"
        return None
    if len(args) >= 2 and args[1] in WRITE_VERBS.get(args[0], set()):
        repo = repo_flag(args)
        if repo != FORK:
            return f"gh {args[0]} {args[1]} needs --repo {FORK} (got {repo})"
    return None


def main() -> int:
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    try:
        problems = [p for s in segments(command) if (p := problem(s))]
    except ValueError:
        problems = []
    if problems:
        print(
            "Blocked: " + "; ".join(problems) + ". This project is fork-only: "
            "never post to geuneda/claude-md-optimizer.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
