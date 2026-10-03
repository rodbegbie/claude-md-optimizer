import re

from claude_md.checks._common import loaded
from claude_md.checks._markdown import (
    fenced_blocks,
    paragraph_lines,
    prose_lines,
)
from claude_md.findings import Context, Finding, Source, check
from claude_md.model import LoadedFile

BEST_PRACTICES = Source("docs", "https://code.claude.com/docs/en/best-practices")
HEURISTIC = Source("heuristic", None)

LINTER_PATTERNS = [
    r"indent(ation)?\s*(size|with|using)?\s*\d",
    r"(tab|space)s?\s*(for|as)\s*indent",
    r"semicolon",
    r"trailing\s*(comma|whitespace|space)",
    r"single\s*quotes?\s*(vs|or|over)\s*double",
    r"double\s*quotes?\s*(vs|or|over)\s*single",
    r"max\s*line\s*length",
    r"prettier",
    r"eslint\s*(rule|config)",
]

VAGUE_PATTERNS = [
    r"(format|write|style)\s*(code|it)?\s*properly",
    r"follow\s*best\s*practices",
    r"keep\s*(code|it)\s*clean",
    r"write\s*good\s*(code|tests)",
    r"be\s*careful\s*with",
    r"try\s*to\s*(avoid|use|keep)",
]

MAX_CODE_BLOCK_LINES = 5
MIN_NARRATIVE_LINES = 3


@check("vague-instruction", BEST_PRACTICES, weight=3, cap=9)
def vague_instruction(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    found: list[Finding] = []
    for file in loaded(files):
        for number, line in prose_lines(file.source_text):
            lowered = line.lower()
            for pattern in VAGUE_PATTERNS:
                match = re.search(pattern, lowered)
                if match:
                    found.append(
                        Finding(
                            "vague-instruction",
                            "warning",
                            file.path,
                            number,
                            f"{file.path}:{number} has a vague instruction: "
                            f"'{match.group()}'.",
                            "Replace it with a specific, verifiable directive, "
                            "such as the exact command or convention to follow.",
                            BEST_PRACTICES,
                        )
                    )
                    break
    return found


@check("linter-rule", HEURISTIC, weight=2, cap=6)
def linter_rule(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    found: list[Finding] = []
    for file in loaded(files):
        hit = next(
            (
                (number, match.group())
                for number, line in prose_lines(file.source_text)
                for pattern in LINTER_PATTERNS
                if (match := re.search(pattern, line.lower()))
            ),
            None,
        )
        if hit:
            number, text = hit
            found.append(
                Finding(
                    "linter-rule",
                    "issue",
                    file.path,
                    number,
                    f"{file.path}:{number} states a formatting rule "
                    f"('{text}') that a linter or formatter normally enforces.",
                    "Move the rule into the formatter or linter config and "
                    "remove it from this file.",
                    HEURISTIC,
                )
            )
    return found


@check("narrative-paragraph", HEURISTIC, weight=1, cap=3)
def narrative_paragraph(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    return [
        Finding(
            "narrative-paragraph",
            "suggestion",
            file.path,
            run[0],
            f"{file.path}:{run[0]} contains a prose paragraph of {len(run)} lines.",
            "Rewrite it as short bullet points, one instruction each.",
            HEURISTIC,
        )
        for file in loaded(files)
        for run in _prose_runs(file.source_text)
        if len(run) >= MIN_NARRATIVE_LINES
    ]


def _prose_runs(text: str) -> list[list[int]]:
    runs: list[list[int]] = []
    for number, _ in paragraph_lines(text):
        if runs and number == runs[-1][-1] + 1:
            runs[-1].append(number)
        else:
            runs.append([number])
    return runs


@check("code-block-long", HEURISTIC, weight=1, cap=3)
def code_block_long(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    return [
        Finding(
            "code-block-long",
            "suggestion",
            file.path,
            block.start,
            f"{file.path}:{block.start} contains a code block of {block.length} lines "
            f"(over {MAX_CODE_BLOCK_LINES}).",
            "Point to the real file as file:line instead of pasting the code.",
            HEURISTIC,
        )
        for file in loaded(files)
        for block in fenced_blocks(file.source_text)
        if block.length > MAX_CODE_BLOCK_LINES
    ]
