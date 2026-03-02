---
name: claude-md-optimizer
description: Analyze and optimize CLAUDE.md files for Claude Code. This skill should be used when the user wants to improve their CLAUDE.md configuration, reduce context token waste, fix anti-patterns, or restructure their Claude Code instructions for maximum effectiveness. Triggers on requests like "optimize my CLAUDE.md", "review my claude config", "improve claude instructions", "clean up CLAUDE.md", or "make my CLAUDE.md more effective". Enforces proven limits (150 lines project, 50 lines user, 250 total) and scores files 0-100.
---

# CLAUDE.md Optimizer

## Overview

Analyze, score, and optimize CLAUDE.md files and related configuration (.claude/rules/, MEMORY.md)
to maximize Claude Code's instruction-following quality while minimizing context token usage.

## Safety Rules

- Never modify files without explicit user approval
- Extract content verbatim when moving to sub-documents (never summarize or paraphrase)
- Verify zero information loss after every extraction
- Back up original files before restructuring
- Skip optimization if CLAUDE.md is already under 80 lines and well-structured

## Workflow

### Step 1: Analyze Current State

Run the analysis script to get a baseline score and identify issues:

```bash
python3 scripts/analyze_claude_md.py <project-dir>
```

Pass `--json` for machine-readable output. If no project directory is specified, the current
working directory is used. The script scans:

- Project-level `CLAUDE.md` (root or `.claude/CLAUDE.md`)
- User-level `~/.claude/CLAUDE.md`
- All `.claude/rules/*.md` files (project and user level)
- `MEMORY.md` files

Present the analysis report to the user, highlighting the score and top issues.

### Step 2: Review Optimization Rules

Read `references/optimization-rules.md` for the complete set of rules, limits, and best practices.
Use this reference to identify which optimizations apply to the user's specific files.

### Step 3: Apply Optimizations

Apply the following optimizations in priority order, always confirming changes with the user:

**Priority 1 - Remove bloat (highest impact)**
- Delete instructions Claude already follows by default
- Remove content duplicated across files
- Remove content that belongs in linter/formatter configs (.editorconfig, .prettierrc, .eslintrc)
- Remove vague/non-actionable instructions ("follow best practices", "keep code clean")

**Priority 2 - Restructure for efficiency**
- Convert paragraph text to bullet-point lists
- Rewrite instructions in imperative form ("Use X" not "We use X")
- Replace inline code snippets (over 5 lines) with file:line references
- Keep short code patterns (3-5 lines) inline - moving them forces re-derivation
- Move task-specific content to .claude/rules/ with appropriate glob patterns

**Priority 3 - Apply progressive disclosure**
- Categorize content: Essential (every session), Reference (occasional), Redundant (remove)
- Move Reference content to sub-documents via verbatim extraction
- Add a Sub-Documentation Table at the top of CLAUDE.md with links
- Add trigger conditions to each reference ("Read X when modifying Y")
- Keep Essential content inline, never extract it

**Priority 4 - Optimize attention placement**
- Place critical prohibitions and key commands at the top of the file
- Place reference trigger index at the bottom
- LLMs have U-shaped attention: strongest at beginning and end, weakest in middle
- Put less critical informational content in the middle sections

**Priority 5 - Add missing essentials**
- Add project summary one-liner if missing
- Add key directory paths if missing
- Add exact build/test/lint commands with flags if missing
- Add explicit prohibitions ("DO NOT" list) if missing
- Add domain glossary (5-10 terms) if specialized project

**Priority 6 - Modularize**
- Extract concern-specific rules into .claude/rules/ files
- Add YAML glob headers to rule files for targeted loading
- Target 3-5 rule files for optimal modular coverage

**Priority 7 - Future-proof**
- Add an "Information Recording Principles" section to prevent future bloat
- Define what belongs in CLAUDE.md vs rules/ vs docs/ vs code comments
- Establish a pattern for where new instructions should go

### Step 4: Validate

Run the analysis script again on the optimized files to verify improvement:

```bash
python3 scripts/analyze_claude_md.py <project-dir>
```

Verification checklist:
- Score improved from baseline
- Zero information loss (all content either kept inline, moved to sub-doc, or intentionally removed with user approval)
- Essential content still inline
- All sub-document links are valid relative paths
- CI/build scripts that parse CLAUDE.md still work

Present before/after comparison: line counts, token estimates, and score.

## Target Metrics

| Metric | Target |
|--------|--------|
| Project CLAUDE.md | under 150 lines |
| User CLAUDE.md | under 50 lines |
| Rule files | under 30 lines each, 3-5 files |
| MEMORY.md | under 200 lines |
| Total all sources | under 250 lines |
| Optimization score | 80+ |
| Information loss | 0% |

## Key Anti-Patterns to Fix

- Formatting/style rules that belong in linters (eslint, prettier, editorconfig)
- Inline code blocks over 5 lines (replace with file:line references)
- Narrative paragraphs (convert to bullet lists)
- Vague directives ("follow best practices", "keep code clean")
- Duplicate content across files
- Instructions for default Claude behavior
- Reference content without trigger conditions
- Critical instructions buried in the middle of the document

## Resources

- `scripts/analyze_claude_md.py` - Analysis and scoring tool (0-100 score, anti-pattern detection)
- `references/optimization-rules.md` - Complete optimization rules, limits, progressive disclosure patterns, and checklist
