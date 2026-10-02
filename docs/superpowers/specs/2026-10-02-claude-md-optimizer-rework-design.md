# claude-md-optimizer rework: design

Status: draft for review. Date: 2026-10-02.

## Goal

Bring the claude-md-optimizer skill back in line with Anthropic's current
guidance, fix its known script bugs, and put tests around it. The work
lands on Rod's fork (`rodbegbie/claude-md-optimizer`) only. It is not
intended for upstream, so a rewrite of scoring semantics is acceptable.

## Success criteria

- Every claim in the skill traces to a primary Anthropic source, or is
  labelled as a heuristic.
- The script analyses the files Claude Code actually loads for a project.
- Behaviour is pinned by a pytest suite and by recorded skill scenarios.

## Constraints

- Runtime stays standard-library Python (3.13). pytest and ruff are dev
  tools, run with uv.
- The CLI is unchanged: `analyze_claude_md.py <dir> [--json]`.
- Extraction stays verbatim and needs explicit user approval.
- The licence stays MIT. The original copyright notice is kept, and Rod's
  is added alongside.
- Nothing is pushed or opened as a PR without Rod's approval.

## Findings that motivate the work

Checked against the Claude Code memory, best-practices and skills docs and
the skill authoring guide, fetched 2026-10-02.

Wrong or unsupported claims:

- The injection order is a fixed five-item list. The docs describe a
  filesystem-root-to-working-directory order, with `CLAUDE.local.md` after
  `CLAUDE.md`, managed policy first, and user rules before project rules.
- All content is re-injected on every request and compounds over a
  session. The docs describe a one-off load at session start. The skill's
  own tables disagree with each other (60k versus 30k tokens at 30 turns).
- The limits (150, 50, 30 and 250 lines) are invented. The docs say under
  200 lines per file.
- Splitting into sub-documents saves tokens. The docs say `@path` imports
  do not reduce context. Path-scoped rules, skills and nested files do.
- A directory structure and critical paths are required content. The docs
  say to leave out anything Claude can derive from the code.
- The benchmark figures (35% fewer corrections and similar) are
  untraceable to primary sources.
- U-shaped attention placement is not in Anthropic's docs.

Script bugs and gaps:

- MEMORY.md discovery takes the first file `os.walk` finds under
  `~/.claude/projects`, which may belong to another project.
- Rules are not scanned recursively.
- `paths:` frontmatter is ignored, so conditional rules inflate totals.
- `CLAUDE.local.md`, ancestor files, `AGENTS.md`, `@imports` and
  `claudeMdExcludes` are not considered.
- Block-level HTML comments, which Claude Code strips, are counted.
- MEMORY.md is checked by lines only, not the 25KB limit.
- There are no tests.

## Approach

Build the script around a model of what Claude Code loads, in three
layers, rather than patching the existing checks in place.

1. Discovery: what loads, in what order, and when.
2. Checks: small independent functions that return findings.
3. Scoring and report: a score derived from the findings.

## Layer 1: discovery

Discovery returns `LoadedFile` records with:

- path
- scope: managed, user, user-rule, ancestor, project, local,
  project-rule, nested, import or memory
- load mode: always, conditional (has `paths:` globs) or on-demand
- position in the load order
- raw text and effective text (frontmatter and block-level HTML comments
  removed)
- line count, byte count and token estimate

What it finds:

- Managed policy CLAUDE.md at the macOS and Linux paths.
- `~/.claude/CLAUDE.md` and `~/.claude/rules/**`, recursively.
- `CLAUDE.md` and `CLAUDE.local.md` in each directory from the filesystem
  root down to the working directory, with `.local` after its sibling.
- `.claude/CLAUDE.md` and `.claude/rules/**`, recursively. User rules sort
  before project rules.
- Nested `CLAUDE.md` files below the working directory, as on-demand.
- `@path` imports, expanded recursively. Each counts as its own always-on
  file. External imports are flagged because they need user approval.
- `AGENTS.md`, which loads only when no CLAUDE.md or `CLAUDE.local.md`
  exists at or above the working directory. The report says whether it is
  loaded or dormant.
- `claudeMdExcludes` from the settings files, read-only. Excluded files
  are marked and not counted. This is the only read outside the CLAUDE.md
  family.
- Auto memory at `~/.claude/projects/<project path, / replaced by ->/memory`.
  Only the first 200 lines or 25KB of MEMORY.md count as loaded. Topic
  files are on-demand.

Always-on and conditional tokens are reported separately.

Open items to verify during implementation, labelled "unverified" in the
output and the rules reference until confirmed:

- The maximum `@import` depth.
- The exact combined-size limit behind the startup warning.
- The order of project rules relative to `.claude/CLAUDE.md`. The docs say
  only that they have the same priority.

## Layer 2: checks

Each finding has an id, severity, file and line, message, suggested fix and
a source tag: `docs` with the page it comes from, or `heuristic`. The
report groups findings by tag.

Kept, as heuristics unless the docs back them:

- Vague instructions.
- Narrative paragraphs.
- Linter-territory style rules.
- Code blocks over 5 lines, with a `file:line` suggestion.
- Duplicates within a file and across files.
- References without trigger conditions.
- Non-English overhead, as an optional check shown only when detected.

Changed:

- The per-file size limit is the docs' 200 lines (`docs`).
- MEMORY.md is checked against 200 lines or 25KB (`docs`).
- The always-on total is a labelled heuristic until the combined limit is
  confirmed.

Removed:

- The 30-line rule-file cap and the "3+ rule files" target.
- The must-include sections (directory structure, critical paths,
  prohibitions at top, information-recording section).
- The additive score bonuses.
- U-shaped attention scoring.

Inverted:

- Derivable content (directory trees, dependency lists, architecture
  overviews, file-by-file descriptions) is flagged as a candidate to cut
  (`docs`).

New:

- Hook candidates: "always", "never", "before every commit" and similar
  rules that should be hooks (`docs`).
- Emphasis dilution: too many IMPORTANT, MUST or all-caps lines (`docs`
  for the principle, heuristic for the threshold).
- Stale references: backticked paths that do not exist, and `npm run` or
  `make` targets missing from `package.json` or the Makefile. Conservative:
  anything unverifiable is skipped.
- Scope candidates: always-on sections that apply only to certain paths.
  The fix is a `paths:` rule or a nested CLAUDE.md (`docs`).
- Import misconception: a note where imports are used to save context.
- Possible conflicts: a low-confidence cross-scope check. Stretch goal,
  dropped if noisy.

## Layer 3: scoring

The score starts at 100 and only goes down. Each check has a weight and a
per-check cap, with lower caps for heuristic findings. The report prints
every deduction. Nothing is added for structure. Scores are not
comparable with earlier versions, and the README and CHANGELOG say so.

## Skill content

SKILL.md (176 lines now, target under 100):

- Description: triggers only, under 500 characters. It covers requests to
  audit, trim or restructure CLAUDE.md, rules or MEMORY.md, and Claude
  ignoring instructions or showing a startup size warning.
- Workflow: run the script, read findings grouped by source tag, choose a
  destination for each piece of content, apply with approval, then re-run
  and confirm with `/context`. The built-in `/doctor` is mentioned as a
  complement.
- Destination table: needed every session stays in CLAUDE.md; path-specific
  goes to a `paths:` rule or nested CLAUDE.md; occasional task knowledge to
  a skill; must-happen-every-time to a hook; derivable content is deleted
  with approval; maintainer notes become HTML comments; personal
  per-project notes go in `CLAUDE.local.md`.
- Safety rules are kept: approval, backups, verbatim extraction, zero
  information loss, unlock instructions inline, CI-parsed content kept.
- Removed: the injection-order section, the Target Metrics table and the
  compounding claims. Thresholds live only in the script.

`references/optimization-rules.md` becomes a table of contents plus:

- What loads and when.
- Why size matters.
- Writing instructions that stick.
- Destinations.
- Anti-patterns, each tagged `[docs]` or `[heuristic]`.
- Unverified items.
- Sources, with one "last verified" line.

README (231 lines, target about 100): what it does, install, usage, a
regenerated example from a real fixture run, how scoring works, a short
differences-from-upstream note, and credit to the original author. A
`CHANGELOG.md` is added.

## Testing

Script tests use pytest, written test-first, in a top-level `tests/`
directory outside the skill folder. Fake home and project trees are built
in `tmp_path`.

- Discovery: load order, always versus conditional, `paths:` parsing,
  recursion, imports, memory path encoding, the AGENTS.md rule and
  `claudeMdExcludes`.
- Checks: one positive and one negative case each.
- Scoring: deductions, caps and determinism.
- CLI: one test pinning the `--json` shape.
- Meta: every check declares a source tag.

Skill-behaviour scenarios pair a fixture project with a prompt and a rubric
of what the agent must and must not advise. They are run by hand with
subagents against the current skill first (the baseline) and again after
each phase. Results are recorded in the planning docs, not in the skill.
Per `superpowers:writing-skills`, no SKILL.md edit happens before its
baseline exists.

## Phases and git workflow

- Phase 0, branch `chore/baseline-fixtures`: fixtures, baselines, pytest
  scaffold, and failing tests that reproduce the known bugs.
- Phase 1, branch `fix/discovery-layer`: discovery layer, bug fixes, and
  removal of the wrong claims.
- Phase 2, branch `feature/checks-and-scoring`: checks, scoring, the
  rewritten rules reference, and SKILL.md cut down.
- Phase 3, branch `chore/docs-and-description`: description, tables of
  contents, README and CHANGELOG.

- Each phase branches from `main` on the fork and ends with a draft PR to
  `main` on `rodbegbie/claude-md-optimizer` for Rod's review. Every `gh`
  call passes `--repo rodbegbie/claude-md-optimizer`, because `gh`
  defaults to the upstream repo after forking.
- This spec and the plans live on
  `planning/claude-md-optimizer-rework` and never merge to `main`.
- Commit often, never skip pre-commit hooks, and stage files by explicit
  path. Commits carry the Co-Authored-By trailer.
- `.agent-traces/` is excluded locally through `.git/info/exclude`.

## Out of scope

- Upstream PRs to the original author.
- Automating the subagent scenarios.
- Changing the CLI arguments.
