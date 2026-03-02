# claude-md-optimizer

A Claude Code skill that analyzes and optimizes your `CLAUDE.md` files for maximum effectiveness.

Built on research from [Anthropic](https://code.claude.com/docs/en/best-practices), [HumanLayer](https://www.humanlayer.dev/blog/writing-a-good-claude-md), [Arize](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/), [Dometrain](https://dometrain.com/blog/creating-the-perfect-claudemd-for-claude-code/), and learnings from existing tools like [wrsmith108/claude-md-optimizer](https://github.com/wrsmith108/claude-md-optimizer) and [daymade/claude-code-skills](https://github.com/daymade/claude-code-skills).

## What It Does

- **Automated scoring** (0-100) with detailed breakdown per file
- **Anti-pattern detection** - linter-territory content, vague instructions, code bloat, duplicate lines
- **Progressive disclosure analysis** - checks for sub-doc tables, trigger conditions, content tier classification
- **Attention placement scoring** - verifies critical content is at top/bottom (LLM U-shaped attention)
- **Essential section detection** - prohibitions, commands, directory structure, info recording principles
- **Safe restructuring** - verbatim extraction only, zero information loss verification, user approval required

## What Makes This Different

| Feature | This skill | wrsmith108 | daymade |
|---------|-----------|------------|---------|
| Automated scoring (0-100) | Yes | No | No |
| Anti-pattern regex detection | Yes | No | No |
| Progressive disclosure workflow | Yes | Yes | Yes |
| Attention placement analysis | Yes | No | Yes (principle) |
| Content tier classification | Yes | Yes | Yes |
| Trigger condition detection | Yes | No | Yes (principle) |
| Info recording principles | Yes | No | Yes |
| Safety rules (verbatim, 0% loss) | Yes | Yes | Yes |
| Standalone analysis script | Yes | No | No |

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
- Short code patterns moved to references (keep 3-5 line patterns inline)
- Narrative paragraphs (convert to bullet-point lists)
- Vague directives ("follow best practices", "keep code clean")
- Duplicate content across files
- Missing essential sections (commands, prohibitions, structure)
- References without trigger conditions (effectively invisible content)
- Critical instructions buried in the middle (poor attention placement)

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
2. Present a detailed report with scores and feature detection
3. Classify content into Essential/Reference/Redundant tiers
4. Suggest and apply optimizations (with your approval, verbatim extraction only)
5. Re-run analysis to show before/after improvement with zero information loss

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
    Attention placement: poor
    Features: commands, dir-structure
    ISSUES (2):
      [!] Project CLAUDE.md has 245 lines (recommended: under 150).
      [!] Linter-territory content detected. Move formatting rules to linter configs.
    WARNINGS (3):
      [~] Heavy use of paragraph text. Convert to bullet lists.
      [~] Code blocks use 45/245 lines (18%). Use file:line references.
      [~] Vague instruction found: 'follow best practices'.
    SUGGESTIONS (3):
      [*] No trigger conditions found. Add 'Read X when modifying Y' patterns.
      [*] Attention placement is poor. Place prohibitions at top, refs at bottom.
      [*] No 'information recording principles' section found.

------------------------------------------------------------
  TOTALS: 312 lines | ~3600 tokens

  [!] Total lines (312) exceeds recommended maximum (250).

  OPTIMIZATION SCORE: 38/100
  Rating: Needs attention - major optimization needed
============================================================
```

## Optimization Workflow

The skill follows a 7-priority optimization order:

1. **Remove bloat** - Default behavior instructions, duplicates, linter content, vague directives
2. **Restructure** - Paragraphs to bullets, imperative form, inline code to file:line refs
3. **Progressive disclosure** - Classify Essential/Reference/Redundant, extract with trigger conditions
4. **Attention placement** - Prohibitions at top, reference index at bottom (U-shaped attention)
5. **Add essentials** - Project summary, commands, prohibitions, domain glossary
6. **Modularize** - Extract to .claude/rules/ with glob patterns
7. **Future-proof** - Add information recording principles to prevent re-bloating

## Research Sources

- [Anthropic - Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [HumanLayer - Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
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
| Progressive disclosure | 62% line reduction, 0% info loss |

## License

MIT
