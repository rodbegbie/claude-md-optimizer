#!/usr/bin/env python3
"""PreToolUse hook (matcher: Bash): gh writes must target the fork."""

import json
import os
import re
import shlex
import sys

FORK = "rodbegbie/claude-md-optimizer"
OPERATORS = {";", "&&", "||", "|", "&", "(", ")"}
READ_VERBS = {
    "view",
    "list",
    "status",
    "checks",
    "diff",
    "checkout",
    "download",
    "watch",
    "clone",
    "browse",
    "get",
}
NOT_REPO_SCOPED = {
    "auth",
    "config",
    "alias",
    "completion",
    "help",
    "version",
    "browse",
    "search",
    "status",
    "extension",
    "gist",
    "ssh-key",
    "gpg-key",
    "codespace",
    "project",
    "preview",
    "attestation",
}
WRAPPERS = {
    "command",
    "builtin",
    "env",
    "sudo",
    "time",
    "exec",
    "nohup",
    "nice",
    "xargs",
}
SHELLS = {"bash", "sh", "zsh", "dash"}
API_READ_METHODS = {"GET", "HEAD"}
API_FIELD_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input"}
API_VALUE_FLAGS = {
    "-H",
    "--header",
    "-q",
    "--jq",
    "-t",
    "--template",
    "--hostname",
    "--cache",
    "-p",
    "--preview",
}
UNPARSEABLE_GH = re.compile(
    r"\bgh\s+(pr|issue|release|label|repo|api|workflow|run|secret|variable"
    r"|cache|ruleset)\b"
)
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
SHELL_C_FLAG = re.compile(r"-[a-z]*c[a-z]*")


def normalise(command: str) -> str:
    """Turn unquoted newlines and backticks into command separators."""
    command = command.replace("\\\n", " ")
    out: list[str] = []
    quote = ""
    escaped = False
    for ch in command:
        if escaped:
            escaped = False
        elif ch == "\\" and quote != "'":
            escaped = True
        elif quote:
            if ch == quote:
                quote = ""
        elif ch in "'\"":
            quote = ch
        elif ch in "\n`":
            ch = " ; "
        out.append(ch)
    return "".join(out)


def segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(normalise(command), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    result: list[list[str]] = [[]]
    for token in lexer:
        if token in OPERATORS:
            result.append([])
        else:
            result[-1].append(token)
    return [segment for segment in result if segment]


def normalise_repo(value: str) -> str:
    value = value.lower().rstrip("/")
    for prefix in ("https://", "http://", "github.com/"):
        value = value.removeprefix(prefix)
    return value.removesuffix(".git")


def names_fork(args: list[str]) -> bool:
    fork = normalise_repo(FORK)
    for i, arg in enumerate(args):
        if arg in ("--repo", "-R") and i + 1 < len(args):
            return normalise_repo(args[i + 1]) == fork
        if arg.startswith("--repo="):
            return normalise_repo(arg.split("=", 1)[1]) == fork
    if args[:1] == ["repo"]:
        return any(normalise_repo(a) == fork for a in args[1:])
    return False


def api_problem(args: list[str]) -> str | None:
    method = ""
    fields = False
    endpoint = ""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-X", "--method") and i + 1 < len(args):
            method = args[i + 1]
            i += 2
        elif arg.startswith("--method="):
            method = arg.split("=", 1)[1]
            i += 1
        elif arg.startswith("-X") and len(arg) > 2:
            method = arg[2:].lstrip("=")
            i += 1
        elif arg in API_FIELD_FLAGS:
            fields = True
            i += 2
        elif arg.startswith(("--field=", "--raw-field=", "--input=")) or re.match(
            r"-[fF]\S", arg
        ):
            fields = True
            i += 1
        elif arg in API_VALUE_FLAGS:
            i += 2
        elif arg.startswith("-"):
            i += 1
        else:
            endpoint = endpoint or arg
            i += 1
    is_write = method.upper() not in API_READ_METHODS if method else fields
    if not is_write:
        return None
    path = endpoint.lower().split("?")[0].lstrip("/")
    path = path.removeprefix("https://api.github.com/")
    repo_path = f"repos/{normalise_repo(FORK)}"
    if path == repo_path or path.startswith(repo_path + "/"):
        return None
    return f"gh api writes must use an endpoint under repos/{FORK}"


def unwrap(tokens: list[str]) -> tuple[list[str], bool]:
    via_xargs = False
    while tokens:
        if ASSIGNMENT.match(tokens[0]):
            tokens = tokens[1:]
        elif os.path.basename(tokens[0]) in WRAPPERS:
            via_xargs = via_xargs or tokens[0] == "xargs"
            tokens = tokens[1:]
            while tokens and tokens[0].startswith("-"):
                tokens = tokens[1:]
        else:
            break
    return tokens, via_xargs


def problems_in(command: str, depth: int = 0) -> list[str]:
    try:
        parsed = segments(command)
    except ValueError:
        if UNPARSEABLE_GH.search(command) and FORK not in command.lower():
            return [f"could not parse a gh command; name {FORK} to allow it"]
        return []
    found: list[str] = []
    for segment in parsed:
        found.extend(segment_problems(segment, depth))
    return found


def segment_problems(tokens: list[str], depth: int) -> list[str]:
    tokens, via_xargs = unwrap(tokens)
    if not tokens or depth > 3:
        return []
    program = os.path.basename(tokens[0])
    if program == "eval":
        return problems_in(" ".join(tokens[1:]), depth + 1)
    if program in SHELLS:
        for i, token in enumerate(tokens[1:-1], start=1):
            if SHELL_C_FLAG.fullmatch(token):
                return problems_in(tokens[i + 1], depth + 1)
        return []
    if program != "gh":
        return []
    args = tokens[1:]
    if not args or args[0].startswith("-"):
        return [f"gh arguments come from stdin; name {FORK}"] if via_xargs else []
    group = args[0]
    if group == "api":
        problem = api_problem(args[1:])
        return [problem] if problem else []
    verb = args[1] if len(args) > 1 and not args[1].startswith("-") else ""
    if (
        group in NOT_REPO_SCOPED
        or verb in READ_VERBS
        or "--help" in args
        or "-h" in args
        or names_fork(args)
    ):
        return []
    if via_xargs and not verb:
        return [f"gh arguments come from stdin; name {FORK}"]
    return [f"gh {group} {verb} needs --repo {FORK}".replace("  ", " ")]


def main() -> int:
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    problems = problems_in(command)
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
