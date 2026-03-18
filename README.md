# claude-md-optimizer

A Claude Code skill that analyzes and optimizes your `CLAUDE.md` files for maximum effectiveness.

Built on research from [Anthropic](https://code.claude.com/docs/en/best-practices), [HumanLayer](https://www.humanlayer.dev/blog/writing-a-good-claude-md), [Arize](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/), [Dometrain](https://dometrain.com/blog/creating-the-perfect-claudemd-for-claude-code/), and insights from [claude-inspector](https://github.com/kangraemin/claude-inspector) (MITM proxy analysis of Claude Code API traffic).

## What It Does

- **Automated scoring** (0-100) with detailed breakdown per file
- **Anti-pattern detection** - linter-territory content, vague instructions, code bloat, duplicate lines
- **Progressive disclosure analysis** - checks for sub-doc tables, trigger conditions, content tier classification
- **Attention placement scoring** - verifies critical content is at top/bottom (LLM U-shaped attention)
- **Essential section detection** - prohibitions, commands, directory structure, info recording principles
- **Non-English content detection** - identifies CJK content with token overhead estimation (30-50% savings when converted to English)
- **Cross-file duplicate detection** - finds content repeated between global, project, and rule files
- **Session cost estimation** - calculates per-request and cumulative token cost over a session
- **Injection order awareness** - optimizes content placement based on Claude Code's config loading order
- **Safe restructuring** - verbatim extraction only, zero information loss verification, user approval required

## Key Insights from claude-inspector

[claude-inspector](https://github.com/kangraemin/claude-inspector) revealed how Claude Code actually processes your config:

- **Every API request** includes ALL CLAUDE.md content (~12KB overhead)
- **Message history accumulates** - after 30 turns, overhead exceeds 1MB
- **Injection order**: global CLAUDE.md -> global rules -> project CLAUDE.md -> project rules -> Memory
- **Non-English content** uses 30-50% more tokens than equivalent English
- **Skills persist** in context until `/clear` is used
- **MCP tools are lazy-loaded** - unused ones cost minimal tokens

These insights drove the v2 improvements: language optimization, session cost tracking, and injection-order-aware attention placement.

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
| Non-English detection & token overhead | Yes | No | No |
| Cross-file duplicate detection | Yes | No | No |
| Session cost estimation | Yes | No | No |
| Injection order awareness | Yes | No | No |
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
- Every byte compounds: a 250-line CLAUDE.md costs ~1,000 tokens/request, accumulating to ~60,000 tokens over 30 turns

### Token Compounding Effect

| CLAUDE.md Size | Per-Request Cost | After 30 Turns |
|---------------|-----------------|----------------|
| 100 lines (~1.5KB) | ~400 tokens | ~24,000 tokens |
| 250 lines (~4KB) | ~1,000 tokens | ~60,000 tokens |
| 500 lines (~8KB) | ~2,000 tokens | ~120,000 tokens |

### Language Efficiency

| Language | Avg Tokens/Instruction | vs English |
|----------|----------------------|------------|
| English | ~15 tokens | baseline |
| Korean | ~22 tokens | +47% |
| Japanese | ~25 tokens | +67% |
| Chinese | ~20 tokens | +33% |

### Anti-Patterns Detected

- **Non-English instructions** where English would save 30-50% tokens
- **Cross-file duplicates** (same content in global + project files)
- Code style/formatting rules (belong in linters, not CLAUDE.md)
- Inline code snippets over 5 lines (use `file:line` references instead)
- Short code patterns moved to references (keep 3-5 line patterns inline)
- Narrative paragraphs (convert to bullet-point lists)
- Vague directives ("follow best practices", "keep code clean")
- Missing essential sections (commands, prohibitions, structure)
- References without trigger conditions (effectively invisible content)
- Critical instructions buried in the middle (poor attention placement)
- Global prohibitions repeated in project files (already well-attended via injection order)

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
2. Present a detailed report with scores, language analysis, and session cost
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
    Non-English: 45% (320 chars, ~400 extra tokens)
    Features: commands, dir-structure
    ISSUES (3):
      [!] Project CLAUDE.md has 245 lines (recommended: under 150).
      [!] Non-English content is 45% (~400 extra tokens per request).
      [!] Linter-territory content detected. Move formatting rules to linter configs.
    WARNINGS (3):
      [~] Heavy use of paragraph text. Convert to bullet lists.
      [~] Code blocks use 45/245 lines (18%). Use file:line references.
      [~] Vague instruction found: 'follow best practices'.

  CROSS-FILE DUPLICATES (2 found):
    [!] "- use pascalcase for public methods and pro..."
        Found in: CLAUDE.md, coding-style.md

------------------------------------------------------------
  TOTALS: 312 lines | ~3600 tokens

  SESSION COST ESTIMATE:
    Per request: ~3600 tokens (injected into every API call)
    After 30 turns: ~216,000 tokens (accumulated in message history)
    [!] High session cost. Consider reducing total content or using /clear.

  LANGUAGE OVERHEAD: ~800 extra tokens/request from non-English content
    Converting to English would save ~48,000 tokens over 30 turns

  [!] Total lines (312) exceeds recommended maximum (250).

  OPTIMIZATION SCORE: 22/100
  Rating: Needs attention - major optimization needed
============================================================
```

## Optimization Workflow

The skill follows an 8-priority optimization order:

0. **Language optimization** - Convert non-English instructions to English (30-50% token savings)
1. **Remove bloat** - Default behavior instructions, duplicates, linter content, vague directives
2. **Restructure** - Paragraphs to bullets, imperative form, inline code to file:line refs
3. **Progressive disclosure** - Classify Essential/Reference/Redundant, extract with trigger conditions
4. **Attention placement** - Injection-order-aware: front-load project files, don't duplicate global prohibitions
5. **Add essentials** - Project summary, commands, prohibitions, domain glossary
6. **Modularize** - Extract to .claude/rules/ with glob patterns
7. **Future-proof** - Add information recording principles, recommend periodic `/clear`

## Research Sources

- [Anthropic - Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [HumanLayer - Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [Arize - CLAUDE.md Best Practices with Prompt Learning](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/)
- [Dometrain - Creating the Perfect CLAUDE.md](https://dometrain.com/blog/creating-the-perfect-claudemd-for-claude-code/)
- [claude-inspector - MITM Proxy Analysis of Claude Code](https://github.com/kangraemin/claude-inspector)

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
| English conversion (CJK) | 30-50% token reduction per request |

## License

MIT
