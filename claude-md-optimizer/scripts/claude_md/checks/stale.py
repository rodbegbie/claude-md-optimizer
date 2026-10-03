import json
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path

from claude_md.checks._common import loaded
from claude_md.checks._markdown import prose_lines
from claude_md.findings import Context, Finding, Source, check
from claude_md.model import LoadedFile, Scope

HEURISTIC = Source("heuristic", None)

CHECKED_SCOPES = frozenset(
    [Scope.PROJECT, Scope.LOCAL, Scope.PROJECT_RULE, Scope.NESTED]
)
EXTENSIONS = frozenset(
    [
        "py",
        "js",
        "ts",
        "tsx",
        "jsx",
        "mjs",
        "cjs",
        "go",
        "rs",
        "md",
        "json",
        "yaml",
        "yml",
        "toml",
        "sh",
        "bash",
        "zsh",
        "rb",
        "java",
        "kt",
        "swift",
        "c",
        "h",
        "cpp",
        "hpp",
        "cs",
        "php",
        "sql",
        "css",
        "scss",
        "html",
        "txt",
        "cfg",
        "ini",
        "lock",
        "proto",
        "gradle",
        "xml",
    ]
)
AMBIGUOUS_BARE = frozenset(["js"])
GENERATED_DIRS = frozenset(
    [
        "node_modules",
        "dist",
        "build",
        "out",
        "target",
        "coverage",
        "vendor",
        "venv",
        ".venv",
        "env",
        ".git",
        ".next",
        ".nuxt",
        ".cache",
        ".tox",
        ".gradle",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    ]
)
NOT_IN_REPOSITORIES = frozenset(["MEMORY.md"])
MAX_TOKEN_LENGTH = 300
SCAN_LIMIT = 20000
MAX_FILE_BYTES = 1_000_000

PNPM_YARN_BUILTINS = frozenset(
    [
        "install",
        "i",
        "add",
        "remove",
        "rm",
        "uninstall",
        "update",
        "up",
        "upgrade",
        "run",
        "exec",
        "dlx",
        "create",
        "init",
        "test",
        "t",
        "start",
        "build",
        "dev",
        "lint",
        "link",
        "unlink",
        "publish",
        "pack",
        "audit",
        "outdated",
        "list",
        "ls",
        "why",
        "store",
        "config",
        "cache",
        "dedupe",
        "prune",
        "rebuild",
        "patch",
        "import",
        "info",
        "workspace",
        "workspaces",
        "global",
        "version",
        "set",
        "node",
        "env",
        "help",
        "login",
        "logout",
        "whoami",
        "tag",
        "team",
        "bin",
        "licenses",
        "fetch",
        "deploy",
        "doctor",
        "setup",
        "self-update",
        "approve-builds",
    ]
)
NPM_RUN_FLAGS = frozenset(["--if-present", "--silent", "-s", "--ignore-scripts"])
MAKE_SOURCES = ("Makefile", "makefile", "GNUmakefile")

_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_UNVERIFIABLE = re.compile(r"[\s*?\[\]{}<>$|;\"'!(),=\\^&%@\x00]")
_LINE_SUFFIX = re.compile(r":\d+(?:[-:]\d+)*$")
_COMMAND_BREAK = re.compile(r"&&|\|\||[;|]")
_SCRIPT_NAME = re.compile(r"^[A-Za-z0-9_][\w:.\-]*$")
_MAKE_TARGET = re.compile(r"^[A-Za-z0-9_][\w.\-/]*$")
_MAKE_RULE = re.compile(r"^([^\t #:=][^:=#]*?):(?!=)(.*)$")
_MAKE_INCLUDE = re.compile(r"^\s*(?:-|s)?include\b")

STALE_FIX = (
    "Update the reference to the current name, or remove it if it no longer applies."
)


@dataclass(frozen=True)
class _Package:
    path: Path
    scripts: frozenset[str]
    dependencies: frozenset[str]


@dataclass
class _Run:
    root: str
    _names: set[str] | None = field(default=None, init=False)
    _scanned: bool = field(default=False, init=False)
    _packages: dict[str, _Package | None] = field(default_factory=dict, init=False)
    _makefiles: dict[str, tuple[Path, frozenset[str]] | None] = field(
        default_factory=dict, init=False
    )

    def names(self) -> set[str] | None:
        if not self._scanned:
            self._scanned = True
            self._names = _scan_names(self.root)
        return self._names

    def package(self, directories: list[str]) -> _Package | None:
        for directory in directories:
            if directory not in self._packages:
                self._packages[directory] = _load_package(directory, self.root)
            if self._packages[directory] is not None:
                return self._packages[directory]
        return None

    def makefile(self, directories: list[str]) -> tuple[Path, frozenset[str]] | None:
        for directory in directories:
            if directory not in self._makefiles:
                self._makefiles[directory] = _load_makefile(directory)
            if self._makefiles[directory] is not None:
                return self._makefiles[directory]
        return None


@check("stale-reference", HEURISTIC, weight=2, cap=4)
def stale_reference(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    run = _Run(os.path.normpath(str(ctx.project_dir)))
    findings: list[Finding] = []
    for file in loaded(files):
        if file.scope not in CHECKED_SCOPES:
            continue
        directory = os.path.normpath(str(file.path.parent))
        for number, line in prose_lines(file.text):
            seen: set[str] = set()
            for span in _CODE_SPAN.findall(line):
                for problem in _span_problems(span, directory, run):
                    if problem not in seen:
                        seen.add(problem)
                        findings.append(_finding(file, number, problem))
    return findings


def _finding(file: LoadedFile, number: int, problem: str) -> Finding:
    return Finding(
        "stale-reference",
        "suggestion",
        file.path,
        number,
        f"{file.path}:{number} {problem}",
        STALE_FIX,
        HEURISTIC,
    )


def _span_problems(span: str, directory: str, run: _Run) -> list[str]:
    problems = _command_problems(span, directory, run)
    if problems is not None:
        return problems
    cleaned = _clean_path(span)
    if cleaned is None:
        return []
    return _path_problems(*cleaned, directory, run)


def _command_problems(span: str, directory: str, run: _Run) -> list[str] | None:
    problems: list[str] = []
    is_command = False
    for segment in _COMMAND_BREAK.split(span):
        words = segment.split()
        if not words or words[0] not in ("npm", "pnpm", "yarn", "make"):
            continue
        is_command = True
        directories = list(dict.fromkeys([directory, run.root]))
        if words[0] == "make":
            problems += _make_problems(words, directories, run)
        else:
            problems += _script_problems(words, directories, run)
    return problems if is_command else None


def _first_positional(words: list[str], allowed_flags: frozenset[str]) -> str | None:
    for word in words:
        if word.startswith("-"):
            if word not in allowed_flags:
                return None
            continue
        return word if _SCRIPT_NAME.match(word) else None
    return None


def _script_problems(words: list[str], directories: list[str], run: _Run) -> list[str]:
    tool = words[0]
    if len(words) < 2:
        return []
    explicit_run = words[1] in (("run", "run-script") if tool == "npm" else ("run",))
    if tool == "npm" and not explicit_run:
        return []
    if explicit_run:
        name = _first_positional(words[2:], NPM_RUN_FLAGS)
    elif words[1] in PNPM_YARN_BUILTINS:
        return []
    else:
        name = _first_positional(words[1:2], frozenset())
    if name is None:
        return []
    package = run.package(directories)
    if package is None or name in package.scripts:
        return []
    if not explicit_run and (name in package.dependencies or "." in name):
        return []
    command = " ".join(words[: 3 if explicit_run else 2])
    return [f"runs `{command}`, but {name} is not a script in {package.path}."]


def _make_problems(words: list[str], directories: list[str], run: _Run) -> list[str]:
    if any(word.startswith("-") for word in words[1:]):
        return []
    targets = [
        word for word in words[1:] if "=" not in word and _MAKE_TARGET.match(word)
    ]
    if not targets:
        return []
    makefile = run.makefile(directories)
    if makefile is None:
        return []
    path, defined = makefile
    return [
        f"runs `make {target}`, but no target named {target} is defined in {path}."
        for target in targets
        if target not in defined
    ]


def _path_problems(
    token: str, needs_anchor: bool, directory: str, run: _Run
) -> list[str]:
    root = run.root
    bases = [root]
    if directory != root:
        bases.append(directory)
    if token.startswith("/"):
        normal = os.path.normpath(token)
        if not _within(normal, root):
            return []
        parts = _relative_parts(normal, root)
        if _exists(root, parts):
            return []
        return [_missing_path(token, root, [])]
    if needs_anchor and not any(_exists(base, [token.split("/")[0]]) for base in bases):
        return []
    candidates = []
    for base in bases:
        joined = os.path.normpath(os.path.join(base, token))
        if _within(joined, root):
            candidates.append(_relative_parts(joined, root))
    if not candidates or any(_exists(root, parts) for parts in candidates):
        return []
    if "/" not in token:
        names = run.names()
        if names is None or token in names:
            return []
    return [_missing_path(token, root, bases[1:])]


def _missing_path(token: str, root: str, extra: list[str]) -> str:
    where = f"under the project directory {root}"
    if extra:
        where += f" or relative to {extra[0]}"
    return f"refers to `{token}`, which was not found {where}."


def _clean_path(span: str) -> tuple[str, bool] | None:
    """Return (path, needs_anchor), or None when the span is not a checkable path.

    A bare "a/b" with no extension may be prose such as "and/or", so it is only
    checked when its first segment exists (needs_anchor).
    """
    token = span.strip()
    if not token or len(token) > MAX_TOKEN_LENGTH or token.startswith("~"):
        return None
    if _UNVERIFIABLE.search(token) or "://" in token or "..." in token:
        return None
    token = _LINE_SUFFIX.sub("", token).split("#", 1)[0]
    if not token or ":" in token or token == "/":
        return None
    parts = [p for p in token.split("/") if p not in ("", ".")]
    if not parts or any(p in GENERATED_DIRS for p in parts):
        return None
    name = parts[-1]
    if name.startswith(".env") or ".local" in name or name in NOT_IN_REPOSITORIES:
        return None
    if parts[0].startswith(".") and parts[0] not in (".", "..", ".github"):
        return None
    extension = _extension(name)
    known = extension in EXTENSIONS
    if "/" not in token:
        suffix_pattern = name.startswith("_")
        bare = known and extension not in AMBIGUOUS_BARE and not suffix_pattern
        return (token, False) if bare else None
    explicit = known or token.endswith("/") or token.startswith(("./", "../", "/"))
    domain_like = "." in parts[0][1:] and not token.startswith(("./", "../", "/"))
    return token.rstrip("/"), domain_like or not explicit


def _extension(name: str) -> str | None:
    stem, dot, extension = name.rpartition(".")
    return extension.lower() if dot and stem else None


def _within(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _relative_parts(path: str, root: str) -> list[str]:
    relative = path[len(root) :].strip(os.sep)
    return [p for p in relative.split(os.sep) if p]


def _exists(root: str, parts: list[str]) -> bool:
    """True when the path exists or cannot be verified; never follows symlinks."""
    current = root
    for index, part in enumerate(parts):
        current = os.path.join(current, part)
        try:
            mode = os.lstat(current).st_mode
        except (FileNotFoundError, NotADirectoryError):
            return False
        except (OSError, ValueError):
            return True
        if stat.S_ISLNK(mode) and index < len(parts) - 1:
            return True
    return True


def _scan_names(root: str) -> set[str] | None:
    names: set[str] = set()
    count = 0
    for _, directories, filenames in os.walk(root):
        directories[:] = [d for d in directories if d not in GENERATED_DIRS]
        count += len(directories) + len(filenames)
        if count > SCAN_LIMIT:
            return None
        names.update(directories)
        names.update(filenames)
    return names


def _read_regular(path: str) -> str | None:
    try:
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except (OSError, ValueError):
        return None


def _load_package(directory: str, root: str) -> _Package | None:
    if not _within(directory, root):
        return None
    path = os.path.join(directory, "package.json")
    text = _read_regular(path)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict) or "workspaces" in data:
        return None
    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict):
        return None
    if _read_regular(os.path.join(directory, "pnpm-workspace.yaml")) is not None:
        return None
    dependencies: set[str] = set()
    for key in ("dependencies", "devDependencies", "optionalDependencies"):
        section = data.get(key)
        if isinstance(section, dict):
            dependencies.update(section)
    return _Package(Path(path), frozenset(scripts), frozenset(dependencies))


def _load_makefile(directory: str) -> tuple[Path, frozenset[str]] | None:
    for name in MAKE_SOURCES:
        path = os.path.join(directory, name)
        text = _read_regular(path)
        if text is None:
            continue
        targets = _make_targets(text)
        return None if targets is None else (Path(path), targets)
    return None


def _make_targets(text: str) -> frozenset[str] | None:
    targets: set[str] = set()
    for line in text.splitlines():
        if _MAKE_INCLUDE.match(line):
            return None
        match = _MAKE_RULE.match(line)
        if not match:
            continue
        names = match.group(1).split()
        if match.group(1).strip() == ".PHONY":
            names += match.group(2).split()
        if any(c in n for n in names for c in "%$()"):
            return None
        targets.update(names)
    return frozenset(targets)
