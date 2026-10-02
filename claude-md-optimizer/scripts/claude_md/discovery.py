import json
import os
import re
import sys
from pathlib import Path, PurePath

from claude_md.limits import (
    MAX_FILE_BYTES,
    MAX_IMPORT_DEPTH,
    MEMORY_BYTES,
    MEMORY_LINES,
)
from claude_md.model import LoadedFile, LoadMode, Scope
from claude_md.text import effective_text, parse_paths, split_frontmatter

PRUNED_DIRS = frozenset({"node_modules", "__pycache__", "venv", ".venv"})
PROJECT_LEVEL_SCOPES = frozenset(
    {Scope.PROJECT, Scope.ANCESTOR, Scope.LOCAL, Scope.PROJECT_RULE}
)
EXPANDING_SCOPES = PROJECT_LEVEL_SCOPES | {
    Scope.MANAGED,
    Scope.USER,
    Scope.USER_RULE,
    Scope.AGENTS,
}
CLAUDE_FAMILY = ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md")
AGENTS_FAMILY = ("AGENTS.md", ".claude/AGENTS.md")
DORMANT_AGENTS_NOTE = (
    "AGENTS.md not loaded: a CLAUDE.md exists at or above the working directory"
)
TRAILING_PUNCTUATION = ".,;:!?)]}'\""
DEPTH_NOTE = "import depth limit reached"
_FENCE = re.compile(r"^\s*(```|~~~)")
_CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1")
_IMPORT = re.compile(r"(?<!\S)@(\S+)")
_EXTENSION = re.compile(r"\.\w+$")


def default_managed_dir() -> Path | None:
    if sys.platform == "darwin":
        return Path("/Library/Application Support/ClaudeCode")
    if sys.platform.startswith("linux"):
        return Path("/etc/claude-code")
    return None


def discover(
    project_dir: Path, home_dir: Path, managed_dir: Path | None = None
) -> list[LoadedFile]:
    project = project_dir.resolve()
    loader = _Loader(project, home_dir, _read_excludes(project, home_dir))
    has_claude = any(
        (directory / name).is_file()
        for directory in [project, *project.parents]
        for name in CLAUDE_FAMILY
    )
    _discover_memory_files(loader, project, home_dir, managed_dir, has_claude)
    _discover_auto_memory(loader, home_dir)
    _discover_nested(loader, project, has_claude)
    return loader.files


class _Loader:
    def __init__(self, project: Path, home_dir: Path, excludes: list[str]) -> None:
        self.files: list[LoadedFile] = []
        self._seen: set[Path] = set()
        self._imports: dict[Path, tuple[LoadedFile, int]] = {}
        self._project = project
        self._home = home_dir
        self._excludes = excludes

    def add(
        self,
        path: Path,
        scope: Scope,
        mode: LoadMode = LoadMode.ALWAYS,
        *,
        is_rule: bool = False,
    ) -> LoadedFile | None:
        if not path.exists():
            return None
        key = path.resolve()
        if key in self._seen:
            return None
        self._seen.add(key)
        loaded = _read(path, scope, mode, order=len(self.files), is_rule=is_rule)
        self.files.append(loaded)
        if scope != Scope.MANAGED:
            pattern = self._matching_exclude(path, key)
            if pattern is not None:
                loaded.mode = LoadMode.EXCLUDED
                _note(loaded, f"excluded by claudeMdExcludes: {pattern}")
        if scope in EXPANDING_SCOPES and loaded.mode == LoadMode.ALWAYS:
            self._expand(loaded, scope in PROJECT_LEVEL_SCOPES, hop=0, chain=(key,))
        return loaded

    @property
    def project(self) -> Path:
        return self._project

    def add_memory(self, path: Path, mode: LoadMode) -> LoadedFile:
        loaded = _read(path, Scope.MEMORY, mode, order=len(self.files))
        self._seen.add(path.resolve())
        self.files.append(loaded)
        return loaded

    def _matching_exclude(self, path: Path, resolved: Path) -> str | None:
        candidates = (resolved, PurePath(os.path.abspath(path)))
        for pattern in self._excludes:
            expanded = (
                str(self._home / pattern[2:]) if pattern.startswith("~/") else pattern
            )
            if any(candidate.full_match(expanded) for candidate in candidates):
                return pattern
        return None

    def _expand(
        self,
        importer: LoadedFile,
        project_level: bool,
        hop: int,
        chain: tuple[Path, ...],
    ) -> None:
        importer.notes[:] = [n for n in importer.notes if not n.startswith(DEPTH_NOTE)]
        child_hop = hop + 1
        for raw_token in _import_tokens(importer.text):
            token = raw_token.rstrip(TRAILING_PUNCTUATION)
            target = self._resolve(importer.path, raw_token)
            if target is None:
                if _looks_like_path(token):
                    _note(importer, f"import target missing: @{token}")
                continue
            key = target.resolve()
            if key in chain:
                _note(importer, f"circular import: @{token}")
                continue
            if child_hop > MAX_IMPORT_DEPTH.value:
                _note(importer, f"{DEPTH_NOTE}: @{token}")
                continue
            if key in self._seen:
                known = self._imports.get(key)
                if known is not None and child_hop < known[1]:
                    self._imports[key] = (known[0], child_hop)
                    if known[0].mode == LoadMode.ALWAYS:
                        self._expand(known[0], project_level, child_hop, (*chain, key))
                continue
            imported = self.add(target, Scope.IMPORT)
            if imported is None:
                continue
            imported.imported_by = importer.path
            imported.external = project_level and not key.is_relative_to(self._project)
            self._imports[key] = (imported, child_hop)
            if imported.mode == LoadMode.ALWAYS:
                self._expand(imported, project_level, child_hop, (*chain, key))

    def _resolve(self, importer: Path, token: str) -> Path | None:
        stripped = token.rstrip(TRAILING_PUNCTUATION)
        for candidate in dict.fromkeys([token, stripped]):
            if candidate == "~" or candidate.startswith("~/"):
                path = self._home / candidate[2:]
            else:
                path = Path(os.path.normpath(importer.parent / candidate))
            if path.is_file():
                return path
        return None


def _read(
    path: Path, scope: Scope, mode: LoadMode, order: int, *, is_rule: bool = False
) -> LoadedFile:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return _skipped(
            path, scope, order, f"skipped: unreadable ({type(exc).__name__})"
        )
    if len(data) > MAX_FILE_BYTES.value:
        return _skipped(path, scope, order, "skipped: larger than 4 MiB")
    raw = data.decode("utf-8-sig", errors="replace")
    notes = ["invalid UTF-8 replaced"] if "�" in raw else []
    paths = None
    if is_rule:
        paths = parse_paths(split_frontmatter(raw)[0])
        mode = LoadMode.ALWAYS if paths is None else LoadMode.CONDITIONAL
    return LoadedFile(
        path=path,
        scope=scope,
        mode=mode,
        order=order,
        raw=raw,
        text=effective_text(raw, is_rule=is_rule),
        paths=paths,
        notes=notes,
    )


def _note(file: LoadedFile, note: str) -> None:
    if note not in file.notes:
        file.notes.append(note)


def _import_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        match = _FENCE.match(line)
        if match:
            if fence is None:
                fence = match.group(1)
            elif fence == match.group(1):
                fence = None
            continue
        if fence is None:
            tokens.extend(_IMPORT.findall(_CODE_SPAN.sub(" ", line)))
    return tokens


def _looks_like_path(token: str) -> bool:
    return "/" in token or bool(_EXTENSION.search(token))


def _skipped(path: Path, scope: Scope, order: int, note: str) -> LoadedFile:
    return LoadedFile(
        path=path,
        scope=scope,
        mode=LoadMode.SKIPPED,
        order=order,
        raw="",
        text="",
        notes=[note],
    )


def _settings_dicts(project: Path, home_dir: Path) -> list[dict]:
    found: list[dict] = []
    for base in (home_dir, project):
        for name in ("settings.json", "settings.local.json"):
            try:
                data = json.loads((base / ".claude" / name).read_text("utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(data, dict):
                found.append(data)
    return found


def _read_excludes(project: Path, home_dir: Path) -> list[str]:
    merged: dict[str, None] = {}
    for data in _settings_dicts(project, home_dir):
        entries = data.get("claudeMdExcludes")
        if isinstance(entries, list):
            merged.update((e, None) for e in entries if isinstance(e, str))
    return list(merged)


def encode_project_path(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def find_git_root(project_dir: Path) -> Path | None:
    try:
        start = project_dir.resolve()
        for directory in (start, *start.parents):
            git = directory / ".git"
            if git.is_dir():
                return directory
            if git.exists():
                return _linked_worktree_root(git) or directory
    except (OSError, ValueError):
        return None
    return None


def _linked_worktree_root(git_file: Path) -> Path | None:
    try:
        first = git_file.read_text("utf-8").splitlines()[0]
    except (OSError, ValueError, IndexError):
        return None
    if not first.startswith("gitdir:"):
        return None
    try:
        gitdir = (git_file.parent / first.removeprefix("gitdir:").strip()).resolve()
    except (OSError, ValueError):
        return None
    common = gitdir.parent.parent
    if gitdir.parent.name == "worktrees" and common.name == ".git":
        return common.parent
    return None


def memory_dir(project_dir: Path, home_dir: Path) -> Path:
    project = project_dir.resolve()
    chosen: Path | None = None
    for data in _settings_dicts(project, home_dir):
        value = data.get("autoMemoryDirectory")
        if not isinstance(value, str):
            continue
        if value.startswith("~/"):
            chosen = home_dir / value[2:]
        elif os.path.isabs(value):
            chosen = Path(value)
    if chosen is not None:
        return chosen
    root = find_git_root(project) or project
    return home_dir / ".claude" / "projects" / encode_project_path(root) / "memory"


def _truncate_memory(text: str) -> tuple[str, str | None]:
    lines = text.splitlines(keepends=True)
    by_lines = "".join(lines[: MEMORY_LINES.value])
    by_bytes = text.encode()[: MEMORY_BYTES.value].decode("utf-8", errors="ignore")
    if len(by_bytes) < len(by_lines):
        kept, limit = by_bytes, f"{MEMORY_BYTES.value} bytes"
    else:
        kept, limit = by_lines, f"{MEMORY_LINES.value} lines"
    if kept == text:
        return text, None
    dropped = len(lines) - len(kept.splitlines())
    return kept, f"truncated: only the first {limit} load; {dropped} lines dropped"


def _discover_auto_memory(loader: _Loader, home_dir: Path) -> None:
    directory = memory_dir(loader.project, home_dir)
    try:
        topics = sorted(p for p in directory.glob("*.md") if p.is_file())
    except OSError:
        return
    index = directory / "MEMORY.md"
    if index in topics:
        topics.remove(index)
        loaded = loader.add_memory(index, LoadMode.ALWAYS)
        if loaded.mode == LoadMode.ALWAYS:
            loaded.text, note = _truncate_memory(loaded.text)
            if note:
                _note(loaded, note)
    for path in topics:
        loader.add_memory(path, LoadMode.ON_DEMAND)


def _discover_memory_files(
    loader: _Loader,
    project: Path,
    home_dir: Path,
    managed_dir: Path | None,
    has_claude: bool,
) -> None:
    if managed_dir is not None:
        loader.add(managed_dir / "CLAUDE.md", Scope.MANAGED)
    loader.add(home_dir / ".claude" / "CLAUDE.md", Scope.USER)
    _discover_rules(loader, home_dir / ".claude" / "rules", Scope.USER_RULE)
    for directory in reversed([project, *project.parents]):
        is_project = directory == project
        for name in AGENTS_FAMILY:
            path = directory / name
            if has_claude:
                dormant = loader.add(path, Scope.AGENTS, LoadMode.DORMANT)
                if dormant is not None:
                    _note(dormant, DORMANT_AGENTS_NOTE)
            else:
                loader.add(path, Scope.AGENTS)
        loader.add(
            directory / "CLAUDE.md", Scope.PROJECT if is_project else Scope.ANCESTOR
        )
        if is_project:
            loader.add(directory / ".claude" / "CLAUDE.md", Scope.PROJECT)
            _discover_rules(loader, directory / ".claude" / "rules", Scope.PROJECT_RULE)
        loader.add(directory / "CLAUDE.local.md", Scope.LOCAL)


def _discover_rules(loader: _Loader, rules_dir: Path, scope: Scope) -> None:
    visited: set[Path] = set()
    found: list[Path] = []
    for current, dirnames, filenames in os.walk(rules_dir, followlinks=True):
        real = Path(current).resolve()
        if real in visited:
            dirnames[:] = []
            continue
        visited.add(real)
        found.extend(Path(current) / n for n in filenames if n.endswith(".md"))
    for path in sorted(found, key=lambda p: p.relative_to(rules_dir).as_posix()):
        loader.add(path, scope, is_rule=True)


def _discover_nested(loader: _Loader, project: Path, has_claude: bool) -> None:
    agents: list[Path] = []
    for current, dirnames, filenames in os.walk(project):
        dirnames[:] = sorted(
            d for d in dirnames if not d.startswith(".") and d not in PRUNED_DIRS
        )
        directory = Path(current)
        if directory == project:
            continue
        if "CLAUDE.md" in filenames:
            loader.add(directory / "CLAUDE.md", Scope.NESTED, LoadMode.ON_DEMAND)
        if (
            not has_claude
            and "AGENTS.md" in filenames
            and not any((directory / name).is_file() for name in CLAUDE_FAMILY)
        ):
            agents.append(directory / "AGENTS.md")
    for path in agents:
        loader.add(path, Scope.AGENTS, LoadMode.ON_DEMAND)
