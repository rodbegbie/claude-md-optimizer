# claude-md-optimizer

A Claude Code skill that analyzes and optimizes your `CLAUDE.md` files for maximum effectiveness.

Based on extensive research from [Anthropic's official docs](https://code.claude.com/docs/en/best-practices), [HumanLayer](https://www.humanlayer.dev/blog/writing-a-good-claude-md), [Builder.io](https://www.builder.io/blog/claude-md-guide), [SFEIR Institute](https://institute.sfeir.com/en/claude-code/claude-code-memory-system-claude-md/optimization/), [Arize](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/), and [Dometrain](https://dometrain.com/blog/creating-the-perfect-claudemd-for-claude-code/).

## What It Does

- Scans all your CLAUDE.md related files (project, user-level, rules, memory)
- Scores your configuration 0-100
- Detects anti-patterns (linter-territory content, vague instructions, code bloat)
- Provides actionable optimization recommendations
- Restructures files following proven best practices

## Key Optimization Rules

| File | Max Lines | Optimal |
|------|-----------|---------|
| Project `CLAUDE.md` | 150 | under 100 |
| User `~/.claude/CLAUDE.md` | 50 | under 30 |
| Individual `.claude/rules/*.md` | 30 | under 20 |
| `MEMORY.md` | 200 | under 100 |
| **Total across all sources** | **250** | **under 180** |

### Why These Limits Matter

- Frontier LLMs follow ~150-200 instructions with reasonable consistency
- Claude Code's system prompt already uses ~50 instructions
- Instruction-following quality **degrades linearly** as count increases
- A well-structured CLAUDE.md reduces corrections by **35%** and saves **60%** context tokens

### Anti-Patterns Detected

- Code style/formatting rules (belong in linters, not CLAUDE.md)
- Inline code snippets over 5 lines (use `file:line` references instead)
- Narrative paragraphs (convert to bullet-point lists)
- Vague directives ("follow best practices", "keep code clean")
- Duplicate content across files
- Missing essential sections (commands, prohibitions, structure)

## Installation

### Option 1: Download and extract

1. Download `claude-md-optimizer.zip` from [Releases](https://github.com/geuneda/claude-md-optimizer/releases)
2. Extract to `~/.claude/skills/`

### Option 2: Clone this repo

```bash
git clone https://github.com/geuneda/claude-md-optimizer.git ~/.claude/skills/claude-md-optimizer
```

### Option 3: Manual setup

Copy the `claude-md-optimizer/` directory into your `~/.claude/skills/` folder.

## Usage

In Claude Code, simply say:

```
Optimize my CLAUDE.md
```

or

```
Review my claude config and score it
```

The skill will:
1. Run the analysis script on your project
2. Present a detailed report with scores
3. Suggest and apply optimizations (with your approval)
4. Re-run analysis to show before/after improvement

### Standalone Analysis Script

You can also run the analysis script directly:

```bash
python3 ~/.claude/skills/claude-md-optimizer/scripts/analyze_claude_md.py /path/to/project
```

Add `--json` for machine-readable output.

## Example Output

```
============================================================
  CLAUDE.md Optimization Analysis Report
============================================================

  Project CLAUDE.md: /project/CLAUDE.md
    Status: OK
    Lines: 245 | Tokens: ~2800 | Headings: 8
    List items: 42 | Paragraph lines: 68 | Code block lines: 45
    Imperative ratio: 35%
    ISSUES (2):
      [!] Project CLAUDE.md has 245 lines (recommended: <150).
      [!] Linter-territory content detected. Move formatting rules to linter configs.
    WARNINGS (3):
      [~] Heavy use of paragraph text. Convert to bullet lists.
      [~] Code blocks use 45/245 lines (18%). Use file:line references.
      [~] Vague instruction found: 'follow best practices'.

------------------------------------------------------------
  TOTALS: 312 lines | ~3600 tokens

  [!] Total lines (312) exceeds recommended maximum (250).

  OPTIMIZATION SCORE: 38/100
  Rating: Needs attention - major optimization needed
============================================================
```

## Research Sources

This skill is built on findings from these key sources:

- [Anthropic - Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [HumanLayer - Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [Builder.io - How to Write a Good CLAUDE.md File](https://www.builder.io/blog/claude-md-guide)
- [SFEIR Institute - CLAUDE.md Optimization Guide](https://institute.sfeir.com/en/claude-code/claude-code-memory-system-claude-md/optimization/)
- [Arize - CLAUDE.md Best Practices with Prompt Learning](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/)
- [Dometrain - Creating the Perfect CLAUDE.md](https://dometrain.com/blog/creating-the-perfect-claudemd-for-claude-code/)

### Key Research Findings

| Optimization | Measured Impact |
|-------------|----------------|
| Well-structured CLAUDE.md | 35% fewer corrections |
| Modular rules (.claude/rules/) | 25% less setup time |
| Token optimization | 60% context savings |
| Declared critical paths | 50% less file search time |
| Short code examples (5-line) | 40% fewer corrections vs long descriptions |
| Validation commands | 30% less back-and-forth |
| Repository-specific tuning | +10.87% accuracy on SWE Bench |

## License

MIT
