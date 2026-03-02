# CLAUDE.md Optimization Rules Reference

## Line Count Limits

| File | Max Lines | Optimal |
|------|-----------|---------|
| Project CLAUDE.md | 150 | under 100 |
| User ~/.claude/CLAUDE.md | 50 | under 30 |
| Individual .claude/rules/*.md | 30 | under 20 |
| MEMORY.md | 200 | under 100 |
| Total across all sources | 250 | under 180 |

## Instruction Capacity

- Frontier LLMs follow ~150-200 instructions with reasonable consistency
- Claude Code system prompt uses ~50 instructions
- Remaining capacity: ~100-150 instructions for CLAUDE.md + rules
- Instruction-following quality degrades linearly as count increases
- Instructions at prompt peripheries get more attention than middle ones (U-shaped attention)

## Content Tier Classification

Classify every section before optimizing:

| Tier | Criteria | Action |
|------|----------|--------|
| Essential | Used every session, unlocks core workflow, build/test commands, prohibitions | Keep inline in CLAUDE.md |
| Reference | Occasional use, detailed specs, edge cases, historical decisions | Extract to sub-document with trigger condition |
| Redundant | Duplicates existing docs, restates Claude defaults, belongs in linter config | Remove (with user approval) |

### Classification Questions
1. Is this consulted in more than 50% of sessions? -> Essential
2. Does violating this cause severe consequences? -> Essential
3. Is this a copy-paste code pattern under 5 lines? -> Essential (keep inline)
4. Can this be triggered by a specific file/task context? -> Reference
5. Is this detailed SOP, edge case handling, or historical record? -> Reference

## Progressive Disclosure Patterns

### Sub-Documentation Table
Place at the top of CLAUDE.md to link extracted content:
```
| Topic | File | When to read |
|-------|------|-------------|
| API specs | docs/api-spec.md | When modifying API endpoints |
| DB schema | docs/schema.md | When writing database queries |
```

### Trigger Conditions
Every reference document needs a trigger condition stating when to load it.
Without triggers, extracted content becomes invisible and never gets used.

BAD: "See docs/api.md for details"
GOOD: "Read docs/api.md when modifying files in src/api/ or adding new endpoints"

### Attention-Optimized Placement
LLMs exhibit U-shaped attention (primacy + recency effect):
- TOP of file: Prohibitions, critical commands, project summary
- MIDDLE of file: Informational content, directory structure, glossary
- BOTTOM of file: Reference trigger index, sub-documentation table (second copy)

## Must-Include Sections

1. **Project summary** - One-liner orientation (tech stack, purpose)
2. **Directory structure** - Key paths and what they contain
3. **Commands** - Exact build/test/lint/deploy commands with flags
4. **Prohibitions** - Explicit "DO NOT" statements (more effective than positive recommendations)
5. **Domain glossary** - 5-10 key terms (if specialized domain)
6. **Information recording principles** - Rules for where new instructions go (prevents future bloat)

## Must-Avoid Anti-Patterns

### Code Style in CLAUDE.md
- Never send an LLM to do a linter's job
- Formatting rules belong in .editorconfig, .prettierrc, .eslintrc
- LLMs are 100x more expensive than linters for this task
- Move to hooks: pre-commit formatters, post-write linters

### Inline Code Snippets
- Long code snippets become outdated quickly
- Use `file:line` references to point to authoritative source
- Exception: 3-5 line patterns that demonstrate a convention (keep inline)
- Moving short code patterns to references forces LLM to re-derive or make extra reads

### Vague Instructions
- BAD: "Format code properly", "Follow best practices", "Keep code clean"
- GOOD: "Use PascalCase for public methods", "Run `npm test` before committing"

### Narrative Paragraphs
- Claude processes bullet points more efficiently than paragraphs
- Convert multi-sentence paragraphs to concise list items
- Each instruction should be one clear directive

### Redundant Content
- Remove instructions for things Claude already does correctly
- Remove content duplicated in official documentation
- Remove instructions that contradict each other

### References Without Triggers
- Extracted content without trigger conditions is effectively deleted
- Every sub-document link needs "Read X when Y"
- Content that is never triggered wastes the extraction effort

## Structure Best Practices

### Use Imperative Form
- GOOD: "Use functional components"
- BAD: "The project uses functional components"
- GOOD: "Run tests with `npm test --coverage`"
- BAD: "Tests can be run using npm test"

### Modular Rules (.claude/rules/)
- Create separate .md files per concern (testing, security, API, frontend)
- Use glob patterns in YAML headers for auto-loading
- Performance: 40% context noise reduction, 35% relevance improvement
- Recommended: 3-5 rule files minimum

### Information Recording Principles
Add a section defining where new instructions belong to prevent future bloat:
- Always-needed rules -> CLAUDE.md
- File-type-specific rules -> .claude/rules/ with glob patterns
- Detailed procedures -> docs/ referenced by trigger conditions
- Temporary notes -> MEMORY.md (with expiry intent)

## Safety Rules for Extraction

- Always back up before modifying
- Extract content verbatim (never summarize or paraphrase during migration)
- Verify zero information loss via diff after extraction
- Keep encryption/auth unlock instructions inline (chicken-and-egg problem)
- Preserve content that CI scripts parse via regex
- Require explicit user approval before any file modification

## Performance Metrics

| Optimization | Impact |
|-------------|--------|
| Well-structured CLAUDE.md | 35% fewer corrections |
| Modular rules | 25% less setup time between sessions |
| Token optimization | 60% context savings (4500 to 1800 tokens) |
| Declared critical paths | 50% less file search time |
| Code examples (5-line) | 40% fewer corrections vs 20-line descriptions |
| Validation commands | 30% less back-and-forth |
| Repository-specific tuning | +10.87% accuracy on SWE Bench |
| Progressive disclosure | 62% line reduction with 0% info loss (typical) |

## Checklist for Optimized CLAUDE.md

- [ ] Under 150 lines (project) / 50 lines (user)
- [ ] All instructions in imperative form
- [ ] No formatting/style rules (use linter configs instead)
- [ ] No inline code snippets over 5 lines (use file:line refs)
- [ ] Short code patterns (3-5 lines) kept inline
- [ ] No vague instructions
- [ ] No duplicate content
- [ ] Key commands documented with exact flags
- [ ] Critical paths declared explicitly
- [ ] Prohibition list at top of file
- [ ] 3+ modular rule files in .claude/rules/
- [ ] Domain glossary if specialized project
- [ ] MEMORY.md under 200 lines, organized by topic
- [ ] Sub-documentation table with trigger conditions
- [ ] Information recording principles section included
- [ ] Critical content at top/bottom (U-shaped attention)
- [ ] Zero information loss verified after extraction
