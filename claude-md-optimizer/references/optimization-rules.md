# CLAUDE.md Optimization Rules Reference

Every rule carries a tag. `[docs]` means an Anthropic page in
[Sources](#sources) states it. `[heuristic]` means it is this tool's own
judgement. Numeric thresholds for heuristics live only in the analyser.

## Contents

- [What loads and when](#what-loads-and-when)
- [Why size matters](#why-size-matters)
- [Writing instructions that stick](#writing-instructions-that-stick)
- [Destinations](#destinations)
- [Anti-patterns](#anti-patterns)
- [Unverified items](#unverified-items)
- [Sources](#sources)

## What loads and when

- [docs] `CLAUDE.md` and `CLAUDE.local.md` in the working directory and
  every directory above it load at launch, ordered from the filesystem root
  down. Within a directory, `CLAUDE.local.md` comes after `CLAUDE.md`.
- [docs] Files are concatenated; none overrides another.
- [docs] `.claude/rules/` is searched recursively. A rule without `paths:`
  frontmatter loads at launch with the same priority as
  `.claude/CLAUDE.md`.
- [docs] A rule with `paths:` loads when Claude uses the Read, Write or Edit
  tool on a matching file.
- [docs] A `CLAUDE.md` in a subdirectory loads when Claude reads files in
  that subdirectory.
- [docs] `@path` imports are expanded and loaded at launch alongside the
  file that contains them, up to four hops deep.
- [docs] The first 200 lines or 25KB of `MEMORY.md`, whichever comes
  first, load at session start. Memory topic files are read on demand.
- [docs] Claude Code loads a CLAUDE.md file of up to 4 MiB in full and
  skips a larger one.
- [docs] Block-level HTML comments in CLAUDE.md are stripped before the
  content reaches Claude. Comments inside code blocks are kept.
- [docs] A skill's description is always in context. Its full content
  loads when it is invoked and then stays in the conversation across turns.
- [docs] After `/compact`, Claude re-reads the project-root CLAUDE.md from
  disk. A nested CLAUDE.md or path-scoped rule can be missing until it
  loads again.
- [docs] `/context` lists the loaded instruction files under Memory files.

## Why size matters

- [docs] Anthropic recommends under 200 lines per CLAUDE.md file. Longer
  files consume more context and reduce adherence.
- [docs] "Bloated CLAUDE.md files cause Claude to ignore your actual
  instructions." If Claude keeps breaking a rule it has, the file is
  probably too long and the rule is getting lost.
- [docs] Claude Code warns at startup and in `/status` when a file is over
  the recommended length, and when files within it add up past a combined
  limit. Each CLAUDE.md, rules file and `@path` import counts separately.
- [docs] Splitting into `@path` imports helps organisation. Imported files
  load at launch, so the total that loads stays the same.
- [docs] Path-scoped rules, nested CLAUDE.md files and skills keep content
  out of the session until it is relevant.
- [heuristic] The analyser's always-on total is a rough signal only,
  because the combined limit is not documented.

## Writing instructions that stick

- [docs] For each line, ask whether removing it would cause Claude to make
  mistakes. If not, cut it.
- [docs] Be specific: "Use 2-space indentation" works better than "format
  code nicely".
- [docs] Group related instructions under headings and bullets; organised
  sections are easier to follow than dense paragraphs.
- [docs] If two instructions contradict each other, Claude may pick one
  arbitrarily. Remove or reconcile conflicts across all loaded files.
- [docs] Include commands Claude cannot guess, style rules that differ from
  defaults, test instructions, repository etiquette, project-specific
  architectural decisions, environment quirks and gotchas.
- [docs] Leave out what Claude can work out from the code, standard
  conventions, detailed API docs, fast-changing information, tutorials,
  file-by-file descriptions and self-evident advice.
- [docs] CLAUDE.md is context, not enforced configuration. Use a hook for
  anything that must happen every time.
- [docs] Emphasis such as "IMPORTANT" can help a single line that Claude
  keeps skipping. If many lines are emphasised, none stands out.
- [heuristic] Do not reorder a file to put rules at its top or bottom.
  Anthropic's docs say nothing about position in a file affecting
  adherence, and this tool does not score placement.

## Destinations

| Content | Destination | Tag |
| --- | --- | --- |
| Needed in every session | CLAUDE.md | [docs] |
| Applies to some paths only | `paths:` rule or nested CLAUDE.md | [docs] |
| Occasional task knowledge | A skill | [docs] |
| Must happen every time | A hook | [docs] |
| Derivable from the code | Delete, with approval | [docs] |
| Notes for human maintainers | Block-level HTML comment | [docs] |
| Personal notes for one project | `CLAUDE.local.md` | [docs] |
| Linter-enforceable style | Linter or formatter config | [heuristic] |

- [docs] Derivable content includes directory layouts, dependency lists and
  architecture overviews. `/doctor` proposes cutting these and keeps
  pitfalls, rationale and conventions that differ from tool defaults.
- [heuristic] When deleting derivable content, keep at most a line that
  records a decision or constraint the code cannot show.
- [heuristic] A plain pointer to another file is not loaded by Claude Code;
  Claude reads the file only if it decides to. Prefer the mechanisms above.

## Anti-patterns

Each entry gives the analyser's check id and its source tag.

- [docs] `size-file`: a file over the recommended 200 lines.
- [docs] `size-memory`: MEMORY.md past its 200-line or 25KB load window;
  the rest is not loaded.
- [heuristic] `size-always-on`: a large always-on total across files.
- [docs] `derivable-content`: a directory tree, dependency list or other
  content Claude can read from the code.
- [docs] `vague-instruction`: generic advice about quality or care that
  gives Claude nothing specific to do.
- [docs] `hook-candidate`: an "always", "never" or "before every commit"
  rule that only a hook can guarantee.
- [docs] `emphasis-dilution`: many lines using IMPORTANT, MUST or capitals.
- [docs] `scope-candidate`: an always-on section that applies only to some
  paths.
- [docs] `import-misconception`: text claiming an `@path` import loads on
  demand or shrinks what loads.
- [heuristic] `linter-rule`: formatting rules a linter or formatter can
  enforce.
- [heuristic] `narrative-paragraph`: a long prose paragraph of
  instructions.
- [heuristic] `code-block-long`: a long pasted code block; point to the
  real file as `file:line` instead.
- [heuristic] `duplicate-within`: the same line repeated in one file.
- [heuristic] `duplicate-across`: the same line in more than one loaded
  file.
- [heuristic] `no-trigger`: a pointer to another document with no
  condition saying when to read it.
- [heuristic] `non-english`: CJK text in instructions, which may use more
  tokens. Domain terms, proper nouns and exact user-facing strings stay as
  they are.
- [heuristic] `stale-reference`: a backticked path, `npm run` script or
  `make` target that does not exist.
- [heuristic] `possible-conflict`: two loaded files that may give opposite
  instructions. Low confidence; confirm by reading both lines.

## Unverified items

The analyser reports these limits as unverified (its `unverified` output):

- `COMBINED_LINES`: the combined size behind the startup warning.

Other facts this tool relies on but could not confirm in the docs:

- How project rules are ordered against `.claude/CLAUDE.md`, ancestor
  files and `CLAUDE.local.md`. The docs say only that unscoped rules have
  the same priority as `.claude/CLAUDE.md`.
- Whether a `.claude/CLAUDE.md` in an ancestor directory loads. The
  AGENTS.md section implies it counts; the loading section names only
  `CLAUDE.md` and `CLAUDE.local.md`.
- Which memory directory a linked git worktree uses. The analyser maps it
  to the main repository's directory.
- Where MEMORY.md sits in the load order.
- Whether "25KB" means 25 × 1024 bytes. The analyser assumes so.
- Which `autoMemoryDirectory` setting wins when several scopes set it.
- The `/config` "Project instructions" setting for AGENTS.md is not read.

## Sources

- Memory: <https://code.claude.com/docs/en/memory>
- Best practices: <https://code.claude.com/docs/en/best-practices>
- Skills: <https://code.claude.com/docs/en/skills>
- Commands: <https://code.claude.com/docs/en/commands>
- Hooks: <https://code.claude.com/docs/en/hooks-guide>

Last verified: 2026-10-02
