#!/usr/bin/env python3
"""
Analyze CLAUDE.md files and report optimization metrics.
Checks line counts, structure quality, anti-patterns, progressive disclosure,
attention placement, and provides actionable scores.
"""

import sys
import os
import re
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class FileAnalysis:
    path: str
    exists: bool = False
    line_count: int = 0
    char_count: int = 0
    estimated_tokens: int = 0
    heading_count: int = 0
    list_item_count: int = 0
    paragraph_line_count: int = 0
    code_block_lines: int = 0
    code_snippet_count: int = 0
    imperative_ratio: float = 0.0
    has_prohibitions: bool = False
    has_commands_section: bool = False
    has_directory_structure: bool = False
    has_project_summary: bool = False
    has_sub_doc_table: bool = False
    has_trigger_conditions: bool = False
    has_info_recording_principles: bool = False
    attention_score: str = "unknown"
    issues: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)


@dataclass
class AnalysisReport:
    project_claude_md: Optional[FileAnalysis] = None
    user_claude_md: Optional[FileAnalysis] = None
    rules_files: list = field(default_factory=list)
    memory_md: Optional[FileAnalysis] = None
    total_lines: int = 0
    total_estimated_tokens: int = 0
    overall_score: int = 0
    summary: list = field(default_factory=list)


# Anti-pattern keywords that suggest content better handled by linters/formatters
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

# Patterns suggesting vague/weak instructions
VAGUE_PATTERNS = [
    r"(format|write|style)\s*(code|it)?\s*properly",
    r"follow\s*best\s*practices",
    r"keep\s*(code|it)\s*clean",
    r"write\s*good\s*(code|tests)",
    r"be\s*careful\s*with",
    r"try\s*to\s*(avoid|use|keep)",
]

# Imperative verb starters (good pattern)
IMPERATIVE_STARTERS = [
    "use", "run", "add", "create", "install", "configure", "set", "enable",
    "disable", "avoid", "never", "always", "prefer", "include", "exclude",
    "check", "verify", "test", "build", "deploy", "commit", "push",
    "do not", "don't", "ensure", "keep", "make", "write", "read",
    "follow", "apply", "remove", "delete", "update", "replace",
]

# Prohibition indicators
PROHIBITION_PATTERNS = [
    r"do\s*not\b", r"don'?t\b", r"never\b", r"must\s*not\b",
    r"prohibited", r"forbidden", r"avoid\b", r"DO\s*NOT",
]

# Trigger condition patterns (for progressive disclosure)
TRIGGER_PATTERNS = [
    r"(read|see|refer to|check)\s+[`\"]?[\w/.-]+[`\"]?\s+(when|if|before|after|for)",
    r"when\s+(modifying|editing|working|changing|adding|creating)\s+",
]


def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token for English."""
    return len(text) // 4


def check_attention_placement(lines: list, content_lower: str) -> str:
    """
    Check if critical content is placed at beginning/end (U-shaped attention).
    Returns: 'good', 'fair', or 'poor'.
    """
    if len(lines) < 20:
        return "good"

    top_20pct = "\n".join(lines[:len(lines) // 5]).lower()
    bottom_20pct = "\n".join(lines[-len(lines) // 5:]).lower()
    middle = "\n".join(lines[len(lines) // 5: -len(lines) // 5]).lower()

    # Check if prohibitions are near the top
    top_has_prohibitions = any(re.search(p, top_20pct) for p in PROHIBITION_PATTERNS)

    # Check if commands are near the top
    top_has_commands = bool(re.search(r"(```|`[a-z]+ )", top_20pct))

    # Check if reference index is near the bottom
    bottom_has_refs = bool(re.search(r"(reference|see also|sub-doc|trigger|when to read)", bottom_20pct))

    score = 0
    if top_has_prohibitions:
        score += 1
    if top_has_commands:
        score += 1
    if bottom_has_refs:
        score += 1

    if score >= 2:
        return "good"
    if score >= 1:
        return "fair"
    return "poor"


def analyze_file(filepath: str) -> FileAnalysis:
    analysis = FileAnalysis(path=filepath)

    if not os.path.exists(filepath):
        analysis.exists = False
        return analysis

    analysis.exists = True
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
        lines = content.splitlines()

    analysis.line_count = len(lines)
    analysis.char_count = len(content)
    analysis.estimated_tokens = estimate_tokens(content)

    content_lower = content.lower()

    in_code_block = False
    paragraph_buffer = []
    list_items = 0
    headings = 0
    code_blocks = 0
    code_block_lines = 0
    imperative_lines = 0
    instruction_lines = 0

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            if in_code_block:
                code_blocks += 1
            continue

        if in_code_block:
            code_block_lines += 1
            continue

        if stripped.startswith("#"):
            headings += 1
            continue

        if stripped.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
            list_items += 1
            instruction_lines += 1
            lower = stripped.lstrip("-*0123456789. ").lower()
            if any(lower.startswith(v) for v in IMPERATIVE_STARTERS):
                imperative_lines += 1
            continue

        if stripped:
            paragraph_buffer.append(stripped)
            instruction_lines += 1
        else:
            if len(paragraph_buffer) >= 3:
                analysis.paragraph_line_count += len(paragraph_buffer)
            paragraph_buffer = []

    if len(paragraph_buffer) >= 3:
        analysis.paragraph_line_count += len(paragraph_buffer)

    analysis.heading_count = headings
    analysis.list_item_count = list_items
    analysis.code_block_lines = code_block_lines
    analysis.code_snippet_count = code_blocks
    analysis.imperative_ratio = (imperative_lines / instruction_lines) if instruction_lines > 0 else 0

    # Check for essential sections
    analysis.has_prohibitions = any(re.search(p, content_lower) for p in PROHIBITION_PATTERNS)
    analysis.has_commands_section = bool(re.search(r"(command|build|test|lint|deploy|run)", content_lower)) and bool(re.search(r"`[a-z]+ ", content))
    analysis.has_directory_structure = bool(re.search(r"(directory|structure|folder|src/|lib/|app/)", content_lower))
    analysis.has_project_summary = analysis.line_count > 0 and len(lines[0].strip()) > 10

    # Check for progressive disclosure features
    analysis.has_sub_doc_table = bool(re.search(r"\|.*\|.*\|.*when", content_lower))
    analysis.has_trigger_conditions = any(re.search(p, content_lower) for p in TRIGGER_PATTERNS)
    analysis.has_info_recording_principles = bool(re.search(
        r"(information\s*recording|where\s*(new|to)\s*(instructions?|rules?)\s*(go|belong)|adding\s*new\s*(rules?|instructions?))",
        content_lower
    ))

    # Attention placement analysis
    analysis.attention_score = check_attention_placement(lines, content_lower)

    # --- Anti-pattern checks ---
    for pattern in LINTER_PATTERNS:
        if re.search(pattern, content_lower):
            analysis.issues.append(
                f"Linter-territory content detected (pattern: '{pattern}'). "
                "Move formatting rules to linter configs instead."
            )
            break

    for pattern in VAGUE_PATTERNS:
        match = re.search(pattern, content_lower)
        if match:
            analysis.warnings.append(
                f"Vague instruction found: '{match.group()}'. "
                "Replace with specific, actionable directives."
            )

    # --- Line count checks ---
    if "rules" in filepath.lower():
        if analysis.line_count > 30:
            analysis.warnings.append(
                f"Rule file has {analysis.line_count} lines (recommended: under 30). "
                "Split into more focused rule files."
            )
    elif ".claude/CLAUDE.md" in filepath or "/.claude/" in filepath:
        if analysis.line_count > 50:
            analysis.issues.append(
                f"User-level CLAUDE.md has {analysis.line_count} lines (recommended: under 50)."
            )
    else:
        if analysis.line_count > 150:
            analysis.issues.append(
                f"Project CLAUDE.md has {analysis.line_count} lines (recommended: under 150). "
                "Risk of silent truncation and instruction loss."
            )

    # --- Structure checks ---
    if analysis.paragraph_line_count > analysis.line_count * 0.3 and analysis.line_count > 20:
        analysis.warnings.append(
            "Heavy use of paragraph text. Claude processes bullet points more efficiently. "
            "Convert narrative paragraphs to concise list items."
        )

    if analysis.code_block_lines > analysis.line_count * 0.25 and analysis.line_count > 20:
        analysis.warnings.append(
            f"Code blocks use {analysis.code_block_lines}/{analysis.line_count} lines "
            f"({analysis.code_block_lines * 100 // analysis.line_count}%). "
            "Consider using file:line references instead of inline code snippets."
        )

    if analysis.heading_count == 0 and analysis.line_count > 10:
        analysis.issues.append(
            "No headings found. Use markdown headings (##) to structure sections."
        )

    if analysis.imperative_ratio < 0.3 and instruction_lines > 10:
        analysis.suggestions.append(
            f"Imperative ratio is {analysis.imperative_ratio:.0%}. "
            "Use imperative form ('Use X' not 'We use X') for better instruction-following."
        )

    # --- Duplicate content ---
    seen_lines = {}
    for line in lines:
        stripped = line.strip().lower()
        if len(stripped) > 20:
            seen_lines[stripped] = seen_lines.get(stripped, 0) + 1
    duplicates = {k: v for k, v in seen_lines.items() if v > 1}
    if duplicates:
        analysis.warnings.append(
            f"Found {len(duplicates)} duplicate lines. Remove redundancy to save context tokens."
        )

    # --- Progressive disclosure checks (only for project CLAUDE.md) ---
    if analysis.line_count > 80 and "rules" not in filepath.lower():
        if not analysis.has_trigger_conditions:
            analysis.suggestions.append(
                "No trigger conditions found. Add 'Read X when modifying Y' patterns "
                "for referenced documents to enable progressive disclosure."
            )
        if not analysis.has_sub_doc_table and analysis.line_count > 120:
            analysis.suggestions.append(
                "No sub-documentation table found. Consider adding a reference table "
                "at the top linking to extracted detailed content."
            )

    # --- Attention placement check ---
    if analysis.attention_score == "poor" and analysis.line_count > 30:
        analysis.suggestions.append(
            "Attention placement is poor. Place prohibitions and commands at the top, "
            "reference index at the bottom. LLMs have U-shaped attention (strongest at edges)."
        )
    elif analysis.attention_score == "fair" and analysis.line_count > 50:
        analysis.suggestions.append(
            "Attention placement is fair. Consider moving critical prohibitions closer to the top."
        )

    # --- Missing essentials check ---
    if analysis.line_count > 20 and "rules" not in filepath.lower() and "memory" not in filepath.lower():
        if not analysis.has_prohibitions:
            analysis.suggestions.append(
                "No prohibition statements found. Add explicit 'DO NOT' rules - "
                "they prevent errors more effectively than positive recommendations."
            )
        if not analysis.has_commands_section:
            analysis.suggestions.append(
                "No build/test commands found. Add exact commands with flags "
                "to reduce back-and-forth (30% improvement)."
            )

    # --- Future-proofing check ---
    if analysis.line_count > 80 and not analysis.has_info_recording_principles and "rules" not in filepath.lower():
        analysis.suggestions.append(
            "No 'information recording principles' section found. Add rules for "
            "where new instructions belong to prevent future bloat."
        )

    return analysis


def find_claude_files(project_dir: str, home_dir: str) -> dict:
    """Find all CLAUDE.md related files."""
    files = {}

    # Project CLAUDE.md
    project_claude = os.path.join(project_dir, "CLAUDE.md")
    if os.path.exists(project_claude):
        files["project_claude_md"] = project_claude

    # Project .claude/CLAUDE.md
    dot_claude = os.path.join(project_dir, ".claude", "CLAUDE.md")
    if os.path.exists(dot_claude):
        files["dot_claude_md"] = dot_claude

    # User-level CLAUDE.md
    user_claude = os.path.join(home_dir, ".claude", "CLAUDE.md")
    if os.path.exists(user_claude):
        files["user_claude_md"] = user_claude

    # Rules files
    rules_dir = os.path.join(project_dir, ".claude", "rules")
    if os.path.isdir(rules_dir):
        for f in sorted(os.listdir(rules_dir)):
            if f.endswith(".md"):
                files[f"rule_{f}"] = os.path.join(rules_dir, f)

    user_rules_dir = os.path.join(home_dir, ".claude", "rules")
    if os.path.isdir(user_rules_dir):
        for f in sorted(os.listdir(user_rules_dir)):
            if f.endswith(".md"):
                files[f"user_rule_{f}"] = os.path.join(user_rules_dir, f)

    # MEMORY.md
    memory_candidates = [
        os.path.join(project_dir, ".claude", "MEMORY.md"),
    ]
    memory_base = os.path.join(home_dir, ".claude", "projects")
    if os.path.isdir(memory_base):
        for dirpath, dirnames, filenames in os.walk(memory_base):
            if "MEMORY.md" in filenames:
                files["memory_md"] = os.path.join(dirpath, "MEMORY.md")
                break

    for mc in memory_candidates:
        if os.path.exists(mc):
            files["memory_md"] = mc
            break

    return files


def calculate_score(report: AnalysisReport) -> int:
    """Calculate overall optimization score (0-100)."""
    score = 100
    total_issues = 0
    total_warnings = 0
    total_suggestions = 0

    all_analyses = []
    if report.project_claude_md:
        all_analyses.append(report.project_claude_md)
    if report.user_claude_md:
        all_analyses.append(report.user_claude_md)
    all_analyses.extend(report.rules_files)
    if report.memory_md:
        all_analyses.append(report.memory_md)

    for a in all_analyses:
        total_issues += len(a.issues)
        total_warnings += len(a.warnings)
        total_suggestions += len(a.suggestions)

    score -= total_issues * 15
    score -= total_warnings * 5
    score -= total_suggestions * 2

    # Bonus for good structure
    if report.total_lines <= 250:
        score += 5
    if len(report.rules_files) >= 3:
        score += 5

    # Bonus for progressive disclosure features
    primary = report.project_claude_md or report.user_claude_md
    if primary and primary.exists:
        if primary.has_trigger_conditions:
            score += 3
        if primary.has_sub_doc_table:
            score += 3
        if primary.has_info_recording_principles:
            score += 2
        if primary.attention_score == "good":
            score += 3
        elif primary.attention_score == "fair":
            score += 1
        if primary.has_prohibitions:
            score += 2
        if primary.has_commands_section:
            score += 2

    return max(0, min(100, score))


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    home_dir = os.path.expanduser("~")
    output_json = "--json" in sys.argv

    files = find_claude_files(project_dir, home_dir)

    report = AnalysisReport()
    total_lines = 0
    total_tokens = 0

    for key, filepath in files.items():
        analysis = analyze_file(filepath)
        total_lines += analysis.line_count
        total_tokens += analysis.estimated_tokens

        if key == "project_claude_md" or key == "dot_claude_md":
            report.project_claude_md = analysis
        elif key == "user_claude_md":
            report.user_claude_md = analysis
        elif key == "memory_md":
            report.memory_md = analysis
        elif key.startswith("rule_") or key.startswith("user_rule_"):
            report.rules_files.append(analysis)

    report.total_lines = total_lines
    report.total_estimated_tokens = total_tokens
    report.overall_score = calculate_score(report)

    if output_json:
        print(json.dumps(asdict(report), indent=2, default=str))
        return

    # Pretty print report
    print("=" * 60)
    print("  CLAUDE.md Optimization Analysis Report")
    print("=" * 60)
    print()

    def print_file_section(title: str, analysis: FileAnalysis):
        status = "OK" if analysis.exists else "NOT FOUND"
        print(f"  {title}: {analysis.path}")
        print(f"    Status: {status}")
        if not analysis.exists:
            return
        print(f"    Lines: {analysis.line_count} | Tokens: ~{analysis.estimated_tokens} | Headings: {analysis.heading_count}")
        print(f"    List items: {analysis.list_item_count} | Paragraph lines: {analysis.paragraph_line_count} | Code block lines: {analysis.code_block_lines}")
        print(f"    Imperative ratio: {analysis.imperative_ratio:.0%}")
        print(f"    Attention placement: {analysis.attention_score}")

        features = []
        if analysis.has_prohibitions:
            features.append("prohibitions")
        if analysis.has_commands_section:
            features.append("commands")
        if analysis.has_directory_structure:
            features.append("dir-structure")
        if analysis.has_sub_doc_table:
            features.append("sub-doc-table")
        if analysis.has_trigger_conditions:
            features.append("trigger-conditions")
        if analysis.has_info_recording_principles:
            features.append("info-principles")
        if features:
            print(f"    Features: {', '.join(features)}")
        else:
            print(f"    Features: none detected")

        if analysis.issues:
            print(f"    ISSUES ({len(analysis.issues)}):")
            for issue in analysis.issues:
                print(f"      [!] {issue}")
        if analysis.warnings:
            print(f"    WARNINGS ({len(analysis.warnings)}):")
            for w in analysis.warnings:
                print(f"      [~] {w}")
        if analysis.suggestions:
            print(f"    SUGGESTIONS ({len(analysis.suggestions)}):")
            for s in analysis.suggestions:
                print(f"      [*] {s}")
        print()

    if report.project_claude_md:
        print_file_section("Project CLAUDE.md", report.project_claude_md)
    else:
        print("  Project CLAUDE.md: Not found")
        print()

    if report.user_claude_md:
        print_file_section("User CLAUDE.md", report.user_claude_md)
    else:
        print("  User-level CLAUDE.md (~/.claude/CLAUDE.md): Not found")
        print()

    if report.rules_files:
        print(f"  Modular Rules ({len(report.rules_files)} files):")
        for rf in report.rules_files:
            print(f"    - {os.path.basename(rf.path)}: {rf.line_count} lines", end="")
            if rf.issues or rf.warnings:
                print(f" [{len(rf.issues)} issues, {len(rf.warnings)} warnings]", end="")
            print()
            for issue in rf.issues:
                print(f"        [!] {issue}")
            for w in rf.warnings:
                print(f"        [~] {w}")
        print()
    else:
        print("  Modular Rules: None found (recommended: 3+ files in .claude/rules/)")
        print()

    if report.memory_md:
        print_file_section("MEMORY.md", report.memory_md)

    print("-" * 60)
    print(f"  TOTALS: {report.total_lines} lines | ~{report.total_estimated_tokens} tokens")
    print()

    # Thresholds
    if report.total_lines > 250:
        print(f"  [!] Total lines ({report.total_lines}) exceeds recommended maximum (250).")
    elif report.total_lines > 180:
        print(f"  [~] Total lines ({report.total_lines}) is above optimal range (under 180).")
    else:
        print(f"  [OK] Total lines ({report.total_lines}) within optimal range.")

    if len(report.rules_files) < 3:
        print(f"  [~] Only {len(report.rules_files)} rule files. Consider adding more for modular context loading.")

    print()
    print(f"  OPTIMIZATION SCORE: {report.overall_score}/100")
    if report.overall_score >= 80:
        print("  Rating: Excellent")
    elif report.overall_score >= 60:
        print("  Rating: Good - minor improvements possible")
    elif report.overall_score >= 40:
        print("  Rating: Fair - significant optimization recommended")
    else:
        print("  Rating: Needs attention - major optimization needed")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
