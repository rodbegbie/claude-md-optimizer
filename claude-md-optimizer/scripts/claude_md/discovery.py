import os
import sys
from pathlib import Path

from claude_md.limits import MAX_FILE_BYTES
from claude_md.model import LoadedFile, LoadMode, Scope
from claude_md.text import effective_text, parse_paths, split_frontmatter

PRUNED_DIRS = frozenset({"node_modules", "__pycache__", "venv", ".venv"})


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
    loader = _Loader()
    _discover_memory_files(loader, project, home_dir, managed_dir)
    _discover_nested(loader, project)
    return loader.files


class _Loader:
    def __init__(self) -> None:
        self.files: list[LoadedFile] = []
        self._seen: set[Path] = set()

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
        return loaded


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


def _discover_memory_files(
    loader: _Loader, project: Path, home_dir: Path, managed_dir: Path | None
) -> None:
    if managed_dir is not None:
        loader.add(managed_dir / "CLAUDE.md", Scope.MANAGED)
    loader.add(home_dir / ".claude" / "CLAUDE.md", Scope.USER)
    _discover_rules(loader, home_dir / ".claude" / "rules", Scope.USER_RULE)
    for directory in reversed([project, *project.parents]):
        is_project = directory == project
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


def _discover_nested(loader: _Loader, project: Path) -> None:
    for current, dirnames, filenames in os.walk(project):
        dirnames[:] = sorted(
            d for d in dirnames if not d.startswith(".") and d not in PRUNED_DIRS
        )
        if Path(current) != project and "CLAUDE.md" in filenames:
            loader.add(Path(current) / "CLAUDE.md", Scope.NESTED, LoadMode.ON_DEMAND)
