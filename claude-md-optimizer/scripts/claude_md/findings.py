from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from claude_md.model import LoadedFile, LoadMode


@dataclass(frozen=True)
class Source:
    kind: Literal["docs", "heuristic"]
    url: str | None

    def __post_init__(self) -> None:
        if self.kind == "docs" and not self.url:
            raise ValueError("a docs source requires a url")
        if self.kind == "heuristic" and self.url is not None:
            raise ValueError("a heuristic source must not have a url")


@dataclass(frozen=True)
class Finding:
    check_id: str
    severity: Literal["issue", "warning", "suggestion"]
    path: Path | None
    line: int | None
    message: str
    fix: str
    source: Source


@dataclass(frozen=True)
class Context:
    project_dir: Path
    home_dir: Path


CheckFn = Callable[[list[LoadedFile], Context], list[Finding]]


@dataclass(frozen=True)
class CheckSpec:
    id: str
    source: Source
    weight: int
    cap: int
    fn: CheckFn


REGISTRY: dict[str, CheckSpec] = {}

CHECKED_MODES = frozenset({LoadMode.ALWAYS, LoadMode.CONDITIONAL})


def check(
    id: str, source: Source, weight: int, cap: int
) -> Callable[[CheckFn], CheckFn]:
    def register(fn: CheckFn) -> CheckFn:
        if id in REGISTRY:
            raise ValueError(f"duplicate check id: {id}")
        REGISTRY[id] = CheckSpec(id, source, weight, cap, fn)
        return fn

    return register


def run_checks(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    checked = [f for f in files if f.mode in CHECKED_MODES]
    results: list[Finding] = []
    for spec in REGISTRY.values():
        results.extend(spec.fn(checked, ctx))
    return results
