from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from claude_md.text import estimate_tokens


class Scope(StrEnum):
    MANAGED = "managed"
    USER = "user"
    USER_RULE = "user_rule"
    ANCESTOR = "ancestor"
    PROJECT = "project"
    LOCAL = "local"
    PROJECT_RULE = "project_rule"
    NESTED = "nested"
    IMPORT = "import"
    MEMORY = "memory"
    AGENTS = "agents"


class LoadMode(StrEnum):
    ALWAYS = "always"
    CONDITIONAL = "conditional"
    ON_DEMAND = "on_demand"
    EXCLUDED = "excluded"
    DORMANT = "dormant"
    SKIPPED = "skipped"


@dataclass
class LoadedFile:
    path: Path
    scope: Scope
    mode: LoadMode
    order: int
    raw: str
    text: str
    paths: list[str] | None = None
    imported_by: Path | None = None
    external: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def lines(self) -> int:
        return len(self.text.splitlines())

    @property
    def bytes(self) -> int:
        return len(self.text.encode("utf-8"))

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.text)


@dataclass
class Totals:
    always: int = 0
    conditional: int = 0
    on_demand: int = 0


def totals(files: list[LoadedFile]) -> Totals:
    result = Totals()
    for file in files:
        if file.mode == LoadMode.ALWAYS:
            result.always += file.tokens
        elif file.mode == LoadMode.CONDITIONAL:
            result.conditional += file.tokens
        elif file.mode == LoadMode.ON_DEMAND:
            result.on_demand += file.tokens
    return result
