from claude_md.checks._common import loaded
from claude_md.findings import Context, Finding, Source, check
from claude_md.limits import COMBINED_LINES, FILE_LINES, MEMORY_BYTES, MEMORY_LINES
from claude_md.model import LoadedFile, LoadMode, Scope

MEMORY_DOCS = Source("docs", "https://code.claude.com/docs/en/memory")
HEURISTIC = Source("heuristic", None)

FALLBACK_COMBINED_LINES = 500


@check("size-file", MEMORY_DOCS, weight=3, cap=9)
def size_file(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    return [
        Finding(
            "size-file",
            "warning",
            file.path,
            None,
            f"{file.path} is {file.lines} lines, "
            f"{file.lines - FILE_LINES.value} over the recommended "
            f"{FILE_LINES.value}.",
            "Move rarely needed sections into path-scoped rules, or trim "
            "content Claude can derive from the codebase.",
            MEMORY_DOCS,
        )
        for file in loaded(files)
        if file.lines > FILE_LINES.value
    ]


@check("size-memory", MEMORY_DOCS, weight=3, cap=3)
def size_memory(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    found: list[Finding] = []
    for file in files:
        if file.scope != Scope.MEMORY or file.path.name != "MEMORY.md":
            continue
        if file.mode != LoadMode.ALWAYS:
            continue
        lines = len(file.raw.splitlines())
        size = len(file.raw.encode("utf-8"))
        overs = []
        if lines > MEMORY_LINES.value:
            overs.append(
                f"{lines} lines, {lines - MEMORY_LINES.value} over the "
                f"{MEMORY_LINES.value}-line limit"
            )
        if size > MEMORY_BYTES.value:
            overs.append(
                f"{size} bytes, {size - MEMORY_BYTES.value} over the "
                f"{MEMORY_BYTES.value}-byte limit"
            )
        if overs:
            found.append(
                Finding(
                    "size-memory",
                    "issue",
                    file.path,
                    None,
                    f"{file.path} is {' and '.join(overs)}; everything past "
                    "the limit is dropped at load.",
                    "Keep one line per entry, move detail into topic files, "
                    "and merge or drop stale entries.",
                    MEMORY_DOCS,
                )
            )
    return found


@check("size-always-on", HEURISTIC, weight=2, cap=2)
def size_always_on(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    total = sum(f.lines for f in files if f.mode == LoadMode.ALWAYS)
    threshold = (
        COMBINED_LINES.value if COMBINED_LINES.verified else FALLBACK_COMBINED_LINES
    )
    if total <= threshold:
        return []
    qualifier = "" if COMBINED_LINES.verified else " (unverified limit)"
    return [
        Finding(
            "size-always-on",
            "warning",
            None,
            None,
            f"Always-loaded files total {total} lines, {total - threshold} "
            f"over the {threshold}-line combined threshold{qualifier}. "
            "Claude Code warns when files that are each within 200 lines add "
            "up past a combined limit, but the docs give no number.",
            "Move content into path-scoped rules or trim it from the "
            "always-loaded files.",
            HEURISTIC,
        )
    ]
