import re

from claude_md.checks._common import loaded
from claude_md.checks._markdown import prose_lines
from claude_md.findings import Context, Finding, Source, check
from claude_md.model import LoadedFile

BEST_PRACTICES = Source("docs", "https://code.claude.com/docs/en/best-practices")

EMPHASIS_LINE_LIMIT = 5

_ABSOLUTE = re.compile(
    r"\b(always|never|before\s+(?:every|each)|after\s+(?:every|each))\b",
    re.IGNORECASE,
)
_RUN_VERB = re.compile(r"\b(?:run|runs|running|execute|executing)\b", re.IGNORECASE)
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_KEYWORD = re.compile(r"\b(?:IMPORTANT|MUST|NEVER)\b")
_CAPS_RUN = re.compile(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b")
MIN_SHOUTED_RUN = 3
ACRONYMS = frozenset(
    [
        "HTTP",
        "HTTPS",
        "API",
        "URL",
        "URI",
        "JSON",
        "YAML",
        "TOML",
        "XML",
        "HTML",
        "CSS",
        "SQL",
        "CLI",
        "SDK",
        "CPU",
        "GPU",
        "IDE",
        "CI",
        "CD",
        "PR",
        "ID",
        "UI",
        "UX",
        "MCP",
        "LLM",
        "OS",
        "SSH",
        "TLS",
        "DNS",
        "TCP",
        "UDP",
        "REST",
        "AWS",
        "GCP",
        "PDF",
        "CSV",
        "UTF",
        "ASCII",
        "EOF",
        "TODO",
        "README",
    ]
)

HOOK_FIX = (
    "If this must happen every time, set up a hook for it (PreToolUse, "
    "PostToolUse or Stop, whichever fits) so it is enforced rather than "
    "requested, and keep CLAUDE.md for guidance."
)
EMPHASIS_FIX = (
    "Reserve emphasis for the one or two rules that matter most, and move "
    "rules that must happen every time into hooks."
)


@check("hook-candidate", BEST_PRACTICES, weight=1, cap=3)
def hook_candidate(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    return [
        Finding(
            "hook-candidate",
            "suggestion",
            file.path,
            number,
            f"{file.path}:{number} states a must-happen rule around a command. "
            "Instructions in CLAUDE.md are guidance, so a rule that has to "
            "run every time is better enforced with a hook.",
            HOOK_FIX,
            BEST_PRACTICES,
        )
        for file in loaded(files)
        for number, line in prose_lines(file.source_text)
        if _is_hook_candidate(line)
    ]


def _is_hook_candidate(line: str) -> bool:
    if not _ABSOLUTE.search(line):
        return False
    runs = bool(_RUN_VERB.search(line))
    return any(
        not span.endswith("/") and (runs or " " in span.strip())
        for span in _CODE_SPAN.findall(line)
    )


@check("emphasis-dilution", BEST_PRACTICES, weight=1, cap=3)
def emphasis_dilution(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for file in loaded(files):
        lines = [n for n, line in prose_lines(file.source_text) if _is_emphatic(line)]
        if len(lines) > EMPHASIS_LINE_LIMIT:
            findings.append(
                Finding(
                    "emphasis-dilution",
                    "suggestion",
                    file.path,
                    lines[0],
                    f"{file.path}:{lines[0]} is the first of {len(lines)} lines "
                    "using IMPORTANT, MUST, NEVER or runs of capitals. Heavy "
                    "emphasis dilutes the instructions that really matter; the "
                    f"threshold of {EMPHASIS_LINE_LIMIT} lines is a heuristic.",
                    EMPHASIS_FIX,
                    BEST_PRACTICES,
                )
            )
    return findings


def _is_emphatic(line: str) -> bool:
    if _KEYWORD.search(line):
        return True
    for run in _CAPS_RUN.findall(line):
        streak = 0
        for word in run.split():
            streak = 0 if word in ACRONYMS else streak + 1
            if streak >= MIN_SHOUTED_RUN:
                return True
    return False
