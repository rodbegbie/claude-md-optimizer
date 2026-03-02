# CLAUDE.md Optimization Rules Reference

## Line Count Limits

| File | Max Lines | Optimal |
|------|-----------|---------|
| Project CLAUDE.md | 150 | <100 |
| User ~/.claude/CLAUDE.md | 50 | <30 |
| Individual .claude/rules/*.md | 30 | <20 |
| MEMORY.md | 200 | <100 |
| Total across all sources | 250 | <180 |

## Instruction Capacity

- Frontier LLMs follow ~150-200 instructions with reasonable consistency
- Claude Code system prompt uses ~50 instructions
- Remaining capacity: ~100-150 instructions for CLAUDE.md + rules
- Instruction-following quality degrades linearly as count increases
- Instructions at prompt peripheries get more attention than middle ones

## Must-Include Sections

1. **Project summary** - One-liner orientation (tech stack, purpose)
2. **Directory structure** - Key paths and what they contain
3. **Commands** - Exact build/test/lint/deploy commands with flags
4. **Prohibitions** - Explicit "DO NOT" statements (more effective than positive recommendations)
5. **Domain glossary** - 5-10 key terms (if specialized domain)

## Must-Avoid Anti-Patterns

### Code Style in CLAUDE.md
- Never send an LLM to do a linter's job
- Formatting rules belong in .editorconfig, .prettierrc, .eslintrc
- LLMs are 100x more expensive than linters for this task
- Move to hooks: pre-commit formatters, post-write linters

### Inline Code Snippets
- Code snippets become outdated quickly
- Use `file:line` references to point to authoritative source
- Exception: 3-5 line examples that demonstrate a pattern

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

### Progressive Disclosure
- CLAUDE.md contains only universal, always-needed instructions
- Detailed specs go in separate files referenced by path
- Use: "Read `docs/api-spec.md` when modifying API endpoints"

### Prohibitions Format
- "DO NOT" statements prevent errors better than positive recommendations
- Place critical prohibitions near the top of the file
- Be specific: "Never modify files in /config/production/" not "Be careful with configs"

## Performance Metrics

| Optimization | Impact |
|-------------|--------|
| Well-structured CLAUDE.md | 35% fewer corrections |
| Modular rules | 25% less setup time between sessions |
| Token optimization | 60% context savings (4500 -> 1800 tokens) |
| Declared critical paths | 50% less file search time |
| Code examples (5-line) | 40% fewer corrections vs 20-line descriptions |
| Validation commands | 30% less back-and-forth |

## Checklist for Optimized CLAUDE.md

- [ ] Under 150 lines (project) / 50 lines (user)
- [ ] All instructions in imperative form
- [ ] No formatting/style rules (use linter configs instead)
- [ ] No inline code snippets >5 lines (use file:line refs)
- [ ] No vague instructions
- [ ] No duplicate content
- [ ] Key commands documented with exact flags
- [ ] Critical paths declared explicitly
- [ ] Prohibition list included
- [ ] 3+ modular rule files in .claude/rules/
- [ ] Domain glossary if specialized project
- [ ] MEMORY.md under 200 lines, organized by topic
