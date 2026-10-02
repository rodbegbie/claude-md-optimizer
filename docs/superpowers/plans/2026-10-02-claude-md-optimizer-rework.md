# claude-md-optimizer rework implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the claude-md-optimizer script around a model of what
Claude Code loads, correct the skill's out-of-date claims, and pin the
behaviour with tests and recorded skill scenarios.

**Architecture:** A `claude_md` package next to the existing entry script
with three layers: discovery (what loads, when), checks (findings with
source tags) and scoring (deduction-only). `analyze_claude_md.py` stays the
CLI entry point and becomes a thin wrapper. Four phases, each on its own
branch and ending in a draft PR to `main` on the fork.

**Tech Stack:** Python 3.13 (standard library at runtime), pytest and ruff
via uv, markdownlint for Markdown.

**Spec:** `docs/superpowers/specs/2026-10-02-claude-md-optimizer-rework-design.md`
on branch `planning/claude-md-optimizer-rework`. Feature branches start from
`main`, which lacks it. Read it with
`git show planning/claude-md-optimizer-rework:<path>` or add a worktree:
`git worktree add ../cmo-planning planning/claude-md-optimizer-rework`.

## Global Constraints

- Runtime is standard-library Python 3.13. pytest and ruff are dev tools run
  with uv.
- The CLI is unchanged: `analyze_claude_md.py <dir> [--json]`.
- Per-file size recommendation is 200 lines. MEMORY.md loads the first 200
  lines or 25KB, whichever comes first. Claude Code skips a file over 4 MiB.
- Extraction is verbatim and needs explicit user approval.
- Every Markdown file passes `markdownlint` with zero violations.
- Every `gh` call passes `--repo rodbegbie/claude-md-optimizer`. PRs are
  drafts targeting `main`. Nothing is pushed or opened without Rod's approval.
- Never skip pre-commit hooks. Stage by explicit path, never `git add -A`.
  Verify the branch with `git branch --show-current` before each commit.
  Commit messages end with the Co-Authored-By trailer from the session.
- Specs, plans and baselines live only on
  `planning/claude-md-optimizer-rework` and never merge to `main`.
- `.agent-traces/` stays excluded via `.git/info/exclude`.
- `LICENSE` stays MIT. geuneda's notice stays and Rod's is added alongside.
- No SKILL.md or rules-reference edit happens before the phase 0 baselines
  for the scenarios it affects exist.
- Docs-backed behaviour carries a `docs` source tag with the page URL.
  Anything else is tagged `heuristic`. Unconfirmed facts are labelled
  "unverified" in output and docs.

## Review Focus

Failure modes the spec implies but no feature test would otherwise reach.
Each line gets a test in the task that owns the code.

- Empty, unreadable or non-UTF-8 instruction files: no crash, a note on the
  file (Task 1.3).
- Circular `@imports` and symlink loops in `rules/`: terminates, notes the
  cycle (Task 1.5).
- A file over 4 MiB: marked `skipped` and not counted (Task 1.3).
- Memory directory missing, or a project path with spaces, dots or non-ASCII
  characters: reports "not found" rather than reading another project's
  memory (Task 1.7).
- Malformed or non-list `paths:` frontmatter: treated as unconditional, as
  the docs say (Task 1.4).

## Phase 0: baselines and scaffold

Branch `chore/baseline-fixtures` from `main`. Baseline results are recorded
on the planning branch, not here.

### Task 0.1: Test scaffold

**Files:**

- Create: `pyproject.toml`, `tests/conftest.py`, `tests/test_cli_smoke.py`
- Modify: `.gitignore` (add `.venv/`, `.pytest_cache/`, `.ruff_cache/`)

**Interfaces:**

- Produces: fixture `tree(tmp_path) -> Callable[[dict[str, str]], Path]`
  that writes `{relative path: content}` under `tmp_path` and returns the
  root. Fixture `run_cli(tmp_path)` runs
  `python3 claude-md-optimizer/scripts/analyze_claude_md.py <project>
  --json` with `HOME` set to `<tmp_path>/home` and returns parsed JSON.

- [ ] **Step 1: Write the failing test** `test_cli_runs_on_minimal_project`
  in `tests/test_cli_smoke.py`: a tree with `project/CLAUDE.md` containing
  `# Title\n- Use uv.\n`; assert the JSON has key `overall_score` and
  `project_claude_md.line_count == 2`.
- [ ] **Step 2: Run it to see it fail**:
  `uv run pytest tests/test_cli_smoke.py -v`. Expected: FAIL, no
  `pyproject.toml` or fixtures yet.
- [ ] **Step 3: Create `pyproject.toml`** with `requires-python = ">=3.13"`,
  a `dev` dependency group (`pytest`, `ruff`), and
  `[tool.pytest.ini_options]` setting `pythonpath =
  ["claude-md-optimizer/scripts"]` and `testpaths = ["tests"]`. Write the
  two fixtures in `tests/conftest.py`.
- [ ] **Step 4: Run** `uv run pytest -v` and
  `uv run ruff check . && uv run ruff format --check .`. Expected: PASS.
- [ ] **Step 5: Commit** `pyproject.toml uv.lock .gitignore tests/` with
  message `chore: add pytest scaffold`.
- [ ] **Step 6: Track the agent tool config** as its own commit, per Rod.
  Run `git status --short -uall` and confirm exactly these four untracked
  files, and nothing else, are listed: `.claude/settings.json`,
  `.codex/hooks.json`, `.entire/settings.json`, `.entire/.gitignore`. The
  `.entire/.gitignore` already excludes `metadata/`, `logs/` and `tmp/`, so
  session transcripts stay out. Re-scan the four files for tokens and
  absolute home paths; stop and ask Rod if anything turns up. Stage them by
  path and commit with message `chore: track agent tool config`.

### Task 0.2: Failing tests that reproduce the known bugs

**Files:**

- Create: `tests/test_known_bugs.py`

**Interfaces:**

- Consumes: `tree`, `run_cli` from Task 0.1.

Each test is marked `@pytest.mark.xfail(strict=True, reason=...)` so the
suite stays green now and a fix forces the marker's removal.

- [ ] **Step 1: Write three tests** against the current CLI:
  - `test_memory_comes_from_current_project`: two memory dirs under
    `home/.claude/projects/` (`-other/memory/MEMORY.md` with 10 lines,
    and the encoded current project with 3 lines); assert
    `memory_md.line_count == 3`.
  - `test_rules_are_scanned_recursively`: `project/.claude/rules/a/b.md`
    exists; assert one entry in `rules_files`.
  - `test_path_scoped_rules_do_not_count_as_always_on`: a rule with
    `paths:` frontmatter and 50 lines; assert `total_lines` excludes it.
- [ ] **Step 2: Run** `uv run pytest tests/test_known_bugs.py -v`.
  Expected: 3 xfailed.
- [ ] **Step 3: Commit** `tests/test_known_bugs.py` with message
  `test: pin known discovery bugs as strict xfails`.

### Task 0.3: Fixture projects

**Files:**

- Create: `tests/fixtures/<case>/home/.claude/...`,
  `tests/fixtures/<case>/project/...`, and
  `tests/fixtures/<case>/expected.json` for each case below.
- Test: `tests/test_fixtures_wellformed.py`

**Interfaces:**

- Produces: `expected.json` shape `{"must_include": [check_id, ...],
  "must_exclude": [check_id, ...]}` using these check ids: `size-file`,
  `size-memory`, `size-always-on`, `derivable-content`, `hook-candidate`,
  `emphasis-dilution`, `stale-reference`, `scope-candidate`,
  `import-misconception`, `vague-instruction`, `duplicate-across`.

Cases, each a realistic small project:

- `derivable-tree`: CLAUDE.md with a directory tree, dependency list and
  architecture overview. Includes `derivable-content`.
- `import-for-savings`: CLAUDE.md that says imports "save context" and
  imports a 150-line file. Includes `import-misconception`.
- `scoped-in-always-on`: a section that starts "When editing
  `src/api/`...". Includes `scope-candidate`.
- `hook-candidates`: "Always run `ruff` after each edit", "Never commit
  without tests". Includes `hook-candidate`.
- `emphasis-overload`: 12 lines using IMPORTANT, MUST or all caps.
  Includes `emphasis-dilution`.
- `stale-refs`: backticked `src/missing.py` and `npm run nope`, with a real
  `package.json`. Includes `stale-reference`.
- `oversized`: 260-line CLAUDE.md. Includes `size-file`.
- `clean`: a short, specific, well-formed CLAUDE.md. Excludes every id.

- [ ] **Step 1: Write the failing test** `test_every_fixture_is_wellformed`
  that, for each directory under `tests/fixtures`, asserts `project/`
  exists, `expected.json` parses, and ids are from the allowed set.
- [ ] **Step 2: Run it**: expect FAIL (no fixtures).
- [ ] **Step 3: Create the eight fixtures** as described.
- [ ] **Step 4: Run** `uv run pytest -v`. Expected: PASS.
- [ ] **Step 5: Commit** `tests/fixtures tests/test_fixtures_wellformed.py`
  with message `test: add fixture projects for checks and scenarios`.

### Task 0.4: Scenarios and baselines

**Files:**

- Create (feature branch): `tests/scenarios/<name>.md`
- Create (planning branch):
  `docs/superpowers/baselines/2026-10-02-baseline.md`

**Interfaces:**

- Produces: scenario files with sections `Fixture`, `Prompt`, `Must advise`
  and `Must not advise`. Scenarios:
  - `audit-derivable-tree` (fixture `derivable-tree`): "Optimise my
    CLAUDE.md." Must not advise adding a directory section.
  - `explain-context-cost` (fixture `oversized`): "Why is my context so
    big?" Must not quote per-request compounding.
  - `split-with-imports` (fixture `import-for-savings`): "Split this up to
    save context." Must advise `paths:` rules or skills, not imports.
  - `enforce-with-hooks` (fixture `hook-candidates`): "Make Claude always do
    these." Must mention hooks.

- [ ] **Step 1: Write the four scenario files** and commit them on the
  feature branch with message `test: add skill-behaviour scenarios`.
- [ ] **Step 2: STOP and confirm with Rod** before dispatching subagents.
  Each run costs real tokens: 4 scenarios x 3 reps = 12 runs.
- [ ] **Step 3: Run each scenario 3 times** with a fresh general-purpose
  subagent that has the current skill installed and the fixture as its
  working directory. Record verbatim advice.
- [ ] **Step 4: On the planning branch**, write the baseline file: one
  section per scenario with each rep's verbatim advice and a pass or fail
  against the rubric. Lint it with `markdownlint`. Commit with message
  `docs: record phase 0 skill baselines`.

### Task 0.5: Phase 0 pull request

- [ ] **Step 1: Run** `uv run pytest -v` and `uv run ruff check .`.
  Expected: PASS, 3 xfailed.
- [ ] **Step 2: Ask Rod** for approval, then run `git push -u origin
  chore/baseline-fixtures` and `gh pr create --draft --base main --repo
  rodbegbie/claude-md-optimizer`. Body ends with the Claude Code
  attribution line from the session.

## Phase 1: discovery layer

Branch `fix/discovery-layer` from `main` after phase 0 merges.

### Task 1.1: Limits and text helpers

**Files:**

- Create: `claude-md-optimizer/scripts/claude_md/__init__.py`,
  `limits.py`, `text.py`
- Test: `tests/test_text.py`, `tests/test_limits.py`

**Interfaces:**

- Produces in `limits.py`: `@dataclass(frozen=True) class Limit:
  value: int; verified: bool; source: str`, and constants
  `FILE_LINES = Limit(200, True, <memory docs URL>)`,
  `MEMORY_LINES = Limit(200, True, <url>)`,
  `MEMORY_BYTES = Limit(25 * 1024, True, <url>)`,
  `MAX_FILE_BYTES = Limit(4 * 1024 * 1024, True, <url>)`,
  `MAX_IMPORT_DEPTH = Limit(5, False, "unverified")`,
  `COMBINED_LINES = Limit(0, False, "unverified")`.
- Produces in `text.py`:
  - `estimate_tokens(text: str) -> int` (moved unchanged from the script)
  - `strip_html_comments(text: str) -> str` (block-level only; comments
    inside fenced code blocks are kept)
  - `split_frontmatter(text: str) -> tuple[str | None, str]`
  - `parse_paths(block: str | None) -> list[str] | None` (accepts a YAML
    list or a comma-separated string; returns `None` when absent or
    unparseable)
  - `effective_text(text: str, *, is_rule: bool) -> str`

- [ ] **Step 1: Write failing tests**:
  `test_strip_html_comments_removes_block_comment`,
  `test_strip_html_comments_keeps_comment_in_code_block`,
  `test_parse_paths_list`, `test_parse_paths_comma_string`,
  `test_parse_paths_malformed_returns_none`,
  `test_effective_text_strips_frontmatter_for_rules`,
  `test_estimate_tokens_matches_legacy` (assert equality with the legacy
  function on three sample strings).
- [ ] **Step 2: Run** `uv run pytest tests/test_text.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** both modules. `parse_paths` is a small line
  parser, not a YAML dependency.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** the new files by path with message
  `feat: add limits and text helpers`.

### Task 1.2: Load model

**Files:**

- Create: `claude-md-optimizer/scripts/claude_md/model.py`
- Test: `tests/test_model.py`

**Interfaces:**

- Produces:
  - `class Scope(StrEnum)`: `MANAGED`, `USER`, `USER_RULE`, `ANCESTOR`,
    `PROJECT`, `LOCAL`, `PROJECT_RULE`, `NESTED`, `IMPORT`, `MEMORY`,
    `AGENTS`.
  - `class LoadMode(StrEnum)`: `ALWAYS`, `CONDITIONAL`, `ON_DEMAND`,
    `EXCLUDED`, `DORMANT`, `SKIPPED`.
  - `@dataclass class LoadedFile`: `path: Path`, `scope: Scope`,
    `mode: LoadMode`, `order: int`, `raw: str`, `text: str`,
    `paths: list[str] | None`, `imported_by: Path | None`,
    `external: bool`, `notes: list[str]`; read-only properties `lines`,
    `bytes`, `tokens` computed from `text`.
  - `@dataclass class Totals`: `always: int`, `conditional: int`,
    `on_demand: int` (tokens).
  - `def totals(files: list[LoadedFile]) -> Totals`.

- [ ] **Step 1: Write failing tests**:
  `test_totals_split_by_mode` (three files, one per counted mode, plus an
  `EXCLUDED` one that counts nowhere) and
  `test_lines_ignore_stripped_comments`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement** `model.py`.
- [ ] **Step 4: Run**: expect PASS.
- [ ] **Step 5: Commit** with message `feat: add load model`.

### Task 1.3: Discovery of the CLAUDE.md family

**Files:**

- Create: `claude-md-optimizer/scripts/claude_md/discovery.py`
- Test: `tests/test_discovery_claude_md.py`

**Interfaces:**

- Consumes: `LoadedFile`, `Scope`, `LoadMode`, `effective_text`, `Limit`s.
- Produces: `discover(project_dir: Path, home_dir: Path, managed_dir:
  Path | None = None) -> list[LoadedFile]`, sorted by `order`. Later
  tasks extend it.

Order: managed, user, then for each directory from the filesystem root to
`project_dir`: `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`. Nested
`CLAUDE.md` files below `project_dir` are `ON_DEMAND`.

- [ ] **Step 1: Write failing tests**:
  `test_ancestor_order_root_to_cwd`, `test_local_after_sibling`,
  `test_nested_is_on_demand`, `test_managed_loads_first`,
  `test_home_as_cwd_is_not_double_counted`,
  `test_empty_file_is_loaded_with_zero_lines`,
  `test_invalid_utf8_is_read_with_replacement_and_noted`,
  `test_file_over_4_mib_is_skipped`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement** `discover`.
  Unreadable files get a note and `SKIPPED`, never an exception.
- [ ] **Step 4: Run**: expect PASS. **Step 5: Commit** with message
  `feat: discover the CLAUDE.md family`.

### Task 1.4: Rules, recursion and conditional loading

**Files:**

- Modify: `claude_md/discovery.py`
- Test: `tests/test_discovery_rules.py`

**Interfaces:**

- Produces: `discover` also returns `USER_RULE` then `PROJECT_RULE` files
  from `rules/**/*.md` (recursive, sorted by path). A rule with a parsed
  `paths` list is `CONDITIONAL`; otherwise `ALWAYS`.

- [ ] **Step 0: Verify the open item**: in the same docs page, check how
  project rules without `paths:` order relative to `.claude/CLAUDE.md`. If
  the docs give an order, encode it and mark it verified in the rules
  reference's "Unverified" list; otherwise keep "same priority" and leave it
  listed as unverified.
- [ ] **Step 1: Write failing tests**: `test_rules_recursive`,
  `test_user_rules_before_project_rules`,
  `test_paths_frontmatter_makes_rule_conditional`,
  `test_malformed_paths_is_unconditional`,
  `test_non_list_paths_string_is_accepted`,
  `test_symlink_loop_in_rules_terminates`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement** with a
  visited-set on resolved paths.
- [ ] **Step 4: Run**: expect PASS. **Step 5: Commit** with message
  `feat: discover rules recursively with path scoping`.

### Task 1.5: Imports

**Files:**

- Modify: `claude_md/discovery.py`
- Test: `tests/test_discovery_imports.py`

**Interfaces:**

- Produces: each `@path` import found in an always-on file becomes an
  `IMPORT` file, `ALWAYS`, with `imported_by` set and `external=True` when
  the resolved path is outside `project_dir`. Imports inside fenced code and
  inline code spans are ignored. Depth is capped at `MAX_IMPORT_DEPTH`.

- [ ] **Step 1: Verify the open item**: fetch
  `https://code.claude.com/docs/en/memory` and search the "Import
  additional files" section for a maximum depth. If stated, update
  `MAX_IMPORT_DEPTH` to the stated value with `verified=True`; if not,
  leave it unverified.
- [ ] **Step 2: Write failing tests**: `test_import_counts_as_own_file`,
  `test_nested_imports_expand`, `test_circular_import_terminates_and_notes`,
  `test_external_import_flagged`, `test_import_in_code_block_ignored`,
  `test_missing_import_target_is_noted`.
- [ ] **Step 3: Run**: expect FAIL. **Step 4: Implement**. **Step 5: Run**:
  expect PASS. **Step 6: Commit** with message `feat: expand @imports`.

### Task 1.6: AGENTS.md and claudeMdExcludes

**Files:**

- Modify: `claude_md/discovery.py`
- Test: `tests/test_discovery_agents_excludes.py`

**Interfaces:**

- Produces: `AGENTS.md` / `.claude/AGENTS.md` files at or above the working
  directory become `Scope.AGENTS`; `ALWAYS` only when no `CLAUDE.md`,
  `.claude/CLAUDE.md` or `CLAUDE.local.md` exists at or above the working
  directory, otherwise `DORMANT`. `claudeMdExcludes` globs, read from
  `settings.json` and `settings.local.json` in `~/.claude` and
  `<project>/.claude`, mark matching files `EXCLUDED` (arrays merge).
  Rules reached by symlink follow the docs' symlink exclusion note.

- [ ] **Step 1: Write failing tests**: `test_agents_loaded_when_no_claude_md`,
  `test_agents_dormant_when_claude_md_exists`,
  `test_claude_local_md_counts_as_claude_md`,
  `test_user_claude_md_does_not_suppress_agents`,
  `test_excludes_glob_marks_file`, `test_excludes_merge_across_settings`,
  `test_unreadable_settings_json_is_ignored`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement**. **Step 4: Run**:
  expect PASS. **Step 5: Commit** with message
  `feat: model AGENTS.md and claudeMdExcludes`.

### Task 1.7: Auto memory

**Files:**

- Modify: `claude_md/discovery.py`
- Test: `tests/test_discovery_memory.py`

**Interfaces:**

- Produces: `encode_project_path(path: Path) -> str` replacing every
  non-alphanumeric character with `-`. Marked unverified in the rules
  reference until checked against a real directory. `discover` adds
  `<home>/.claude/projects/<encoded>/memory/MEMORY.md` as `MEMORY`,
  `ALWAYS`, with `text` truncated to the first 200 lines or 25 KB and a note
  stating what was dropped. Other `.md` files in that directory are
  `ON_DEMAND`. If the directory does not exist, no file is returned and the
  CLI reports "memory directory not found".

- [ ] **Step 1: Write failing tests**:
  `test_encode_project_path_simple` (`/Users/rod/x` becomes `-Users-rod-x`),
  `test_encode_handles_spaces_dots_unicode`,
  `test_memory_from_current_project_only`,
  `test_memory_truncated_at_200_lines`,
  `test_memory_truncated_at_25kb`,
  `test_topic_files_on_demand`, `test_missing_memory_dir_returns_nothing`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement**. **Step 4: Run**:
  expect PASS. **Step 5: Commit** with message
  `fix: read memory for the current project only`.

### Task 1.8: Wire discovery into the CLI

**Files:**

- Modify: `claude-md-optimizer/scripts/analyze_claude_md.py:480-528`
  (delete `find_claude_files`), `:597-793` (`main`)
- Modify: `tests/test_known_bugs.py` (remove the three xfail markers)
- Test: `tests/test_cli_json_shape.py`

**Interfaces:**

- Consumes: `discover`, `totals`.
- Produces: `--json` output with top-level keys `files` (list of
  `{path, scope, mode, order, lines, bytes, tokens, notes}`), `totals`
  (`always`, `conditional`, `on_demand`), `unverified` (names of limits with
  `verified=False`), plus the legacy keys until phase 2. `session_cost_*`
  fields are removed. `main` reads `HOME` via `Path.home()`.

- [ ] **Step 1: Write failing test** `test_json_has_files_totals_unverified`
  asserting the keys and that `session_cost_per_request` is absent.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Rework `main`** to build the
  report from `discover`, calling the legacy `analyze_file` only for
  `ALWAYS` and `CONDITIONAL` files. Remove the three xfail markers.
- [ ] **Step 4: Run** `uv run pytest -v`. Expected: PASS, no xfails.
- [ ] **Step 5: Commit** with message `fix: drive the CLI from discovery`.

### Task 1.9: Remove wrong claims and open the phase 1 PR

**Files:**

- Modify: `claude-md-optimizer/SKILL.md` (injection-order section, the
  "~12KB" and "1MB" critical-insight paragraph),
  `claude-md-optimizer/references/optimization-rules.md` (token tables,
  injection order, language table, performance table, 40%/35% claims),
  `README.md` (compounding table, "Key Insights from claude-inspector",
  "Key Research Findings")

Deletions only, plus one sentence pointing to the script for what loads.
Rewrites wait for phase 2.

- [ ] **Step 1: After the edits in Step 2**, re-run scenario
  `explain-context-cost` 3 times and append the results to the
  planning-branch baseline file. The baseline for it already exists from
  Task 0.4. Run this step last, before committing.
- [ ] **Step 2: Edit the three files** as above.
- [ ] **Step 3: Run** `markdownlint SKILL.md README.md
  claude-md-optimizer/SKILL.md claude-md-optimizer/references/*.md`.
  Expected: exit 0.
- [ ] **Step 4: Commit** the three files by path with message
  `docs: remove unsupported claims`.
- [ ] **Step 5: Ask Rod**, then push and open a draft PR as in Task 0.5.

## Phase 2: checks and scoring

Branch `feature/checks-and-scoring` from `main` after phase 1 merges.

### Task 2.1: Findings and the check registry

**Files:**

- Create: `claude_md/findings.py`
- Test: `tests/test_findings.py`

**Interfaces:**

- Produces:
  - `@dataclass(frozen=True) class Source: kind: Literal["docs",
    "heuristic"]; url: str | None`
  - `@dataclass(frozen=True) class Finding: check_id: str; severity:
    Literal["issue", "warning", "suggestion"]; path: Path | None; line:
    int | None; message: str; fix: str; source: Source`
  - `@dataclass(frozen=True) class Context: project_dir: Path;
    home_dir: Path`
  - `def check(id: str, source: Source, weight: int, cap: int)` decorator
    registering `fn(files: list[LoadedFile], ctx: Context) -> list[Finding]`
  - `def run_checks(files: list[LoadedFile], ctx: Context) ->
    list[Finding]`; `REGISTRY: dict[str, CheckSpec]`

- [ ] **Step 1: Write failing tests**: `test_every_check_declares_source`
  (docs sources have a URL), `test_duplicate_check_id_rejected`,
  `test_run_checks_skips_excluded_and_dormant_files`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement**. **Step 4: Run**:
  expect PASS. **Step 5: Commit** with message `feat: add check registry`.

### Task 2.2: Pattern checks

**Files:**

- Create: `claude_md/checks/patterns.py` (and `checks/__init__.py` that
  imports every check module)
- Test: `tests/test_checks_patterns.py`

**Interfaces:**

- Produces check ids `vague-instruction`, `linter-rule`,
  `narrative-paragraph`, `code-block-long`, all `heuristic` except
  `vague-instruction` (`docs`: best-practices exclude table). Pattern lists
  move from `LINTER_PATTERNS` and `VAGUE_PATTERNS` in the old script.

- [ ] **Step 1: Write failing tests**, one positive and one negative per id,
  e.g. `test_vague_flags_follow_best_practices`,
  `test_vague_ignores_specific_instruction`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement**. **Step 4: Run**:
  expect PASS. **Step 5: Commit** with message
  `feat: port pattern checks`.

### Task 2.3: Duplicate, trigger and language checks

**Files:**

- Create: `claude_md/checks/duplicates.py`, `checks/language.py`
- Test: `tests/test_checks_duplicates.py`

**Interfaces:**

- Produces ids `duplicate-within`, `duplicate-across`, `no-trigger`
  (`heuristic`) and `non-english` (`heuristic`, emitted only when CJK
  characters exceed 5% of letters). `duplicate-across` ports
  `find_cross_file_duplicates` and compares only files that are both
  loaded (`ALWAYS` or `CONDITIONAL`).

- [ ] **Step 1: Write failing tests**: positive and negative per id plus
  `test_duplicate_across_ignores_excluded_files` and
  `test_non_english_absent_for_english_only`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement**. **Step 4: Run**:
  expect PASS. **Step 5: Commit** with message
  `feat: port duplicate, trigger and language checks`.

### Task 2.4: Size checks

**Files:**

- Create: `claude_md/checks/size.py`
- Test: `tests/test_checks_size.py`

**Interfaces:**

- Produces ids `size-file` (`docs`, over `FILE_LINES` on any `ALWAYS` or
  `CONDITIONAL` file), `size-memory` (`docs`, MEMORY.md over 200 lines or
  25KB before truncation), `size-always-on` (`heuristic`, always-on lines
  summed; threshold `COMBINED_LINES` once verified, otherwise 500 and the
  message says "unverified").

- [ ] **Step 0: Verify the open item**: on the memory docs page, find the
  combined-size limit behind the startup warning ("files that are each
  within that length add up past a combined limit"). If a number is given,
  set `COMBINED_LINES` to it with `verified=True`; if not, keep it
  unverified and use the 500-line heuristic.
- [ ] **Step 1: Write failing tests**: `test_size_file_flags_201_lines`,
  `test_size_file_ok_at_200_lines`, `test_size_memory_flags_bytes_only`,
  `test_size_always_on_message_says_unverified`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement**. **Step 4: Run**:
  expect PASS. **Step 5: Commit** with message `feat: add size checks`.

### Task 2.5: Derivable content

**Files:**

- Create: `claude_md/checks/derivable.py`
- Test: `tests/test_checks_derivable.py`

**Interfaces:**

- Produces id `derivable-content` (`docs`: best-practices exclude table and
  `/doctor` trim). Flags: fenced blocks that look like a directory tree
  (3+ lines with `├──`, `└──` or consistent indentation of path-like
  tokens); runs of 5+ lines that are bare package names with versions;
  headings named like "Architecture" or "Project structure" followed by
  more than 10 lines.

- [ ] **Step 1: Write failing tests**: `test_flags_directory_tree`,
  `test_flags_dependency_list`, `test_ignores_short_command_block`, and
  `test_fixture_derivable_tree_includes_id` (runs the fixture).
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement**. **Step 4: Run**:
  expect PASS. **Step 5: Commit** with message
  `feat: flag derivable content`.

### Task 2.6: Hook candidates and emphasis

**Files:**

- Create: `claude_md/checks/enforcement.py`
- Test: `tests/test_checks_enforcement.py`

**Interfaces:**

- Produces `hook-candidate` (`docs`: best-practices "set up hooks") for
  lines matching always/never/before-every/after-each plus a command in
  backticks, and `emphasis-dilution` (`docs` for the principle) when more
  than 5 lines use IMPORTANT, MUST, NEVER or a run of 3+ capitalised words.
  The threshold of 5 is a named constant `EMPHASIS_LINE_LIMIT`.

- [ ] **Step 1: Write failing tests**: `test_hook_candidate_always_run`,
  `test_hook_candidate_ignores_plain_preference`,
  `test_emphasis_flags_six_lines`, `test_emphasis_ok_with_one_line`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement**. **Step 4: Run**:
  expect PASS. **Step 5: Commit** with message
  `feat: add hook and emphasis checks`.

### Task 2.7: Stale references

**Files:**

- Create: `claude_md/checks/stale.py`
- Test: `tests/test_checks_stale.py`

**Interfaces:**

- Produces `stale-reference` (`heuristic`). Checks backticked tokens that
  contain `/` or end in a common extension against `ctx.project_dir`, and
  `npm run <x>`, `pnpm <x>`, `yarn <x>` against `package.json` scripts and
  `make <x>` against Makefile targets. Skips globs, URLs, absolute paths
  outside the project, and anything it cannot verify.

- [ ] **Step 1: Write failing tests**: `test_missing_path_flagged`,
  `test_existing_path_ok`, `test_missing_npm_script_flagged`,
  `test_glob_and_url_skipped`, `test_no_package_json_skips_npm_check`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement**. **Step 4: Run**:
  expect PASS. **Step 5: Commit** with message
  `feat: flag stale references`.

### Task 2.8: Scope candidates and import misconception

**Files:**

- Create: `claude_md/checks/scope.py`
- Test: `tests/test_checks_scope.py`

**Interfaces:**

- Produces `scope-candidate` (`docs`: path-scoped rules) for an `ALWAYS`
  section (heading plus body) whose body mentions a path glob or directory
  in 3+ lines starting "when editing/working in/touching", and
  `import-misconception` (`docs`: imports do not reduce context) for text
  matching "import" near "save/reduce context/tokens" in a file that has
  `@` imports.

- [ ] **Step 1: Write failing tests**: `test_scope_candidate_flagged`,
  `test_scope_ignores_general_section`,
  `test_import_misconception_flagged`,
  `test_import_note_absent_without_imports`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement**. **Step 4: Run**:
  expect PASS. **Step 5: Commit** with message
  `feat: add scope and import checks`.

### Task 2.9: Possible conflicts (stretch)

**Files:**

- Create: `claude_md/checks/conflicts.py`
- Test: `tests/test_checks_conflicts.py`

**Interfaces:**

- Produces `possible-conflict` (`heuristic`, severity `suggestion`): pairs of
  lines in different scopes where one says use X and another says never use
  X (same noun, opposite polarity).

- [ ] **Step 1: Write failing tests**: `test_flags_use_vs_never_use`,
  `test_no_flag_within_same_polarity`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement**. **Step 4: Run**:
  expect PASS.
- [ ] **Step 5: Go or no-go**: run the check over all fixtures and over
  Rod's real `~/.claude` (read-only). If it flags unrelated pairs more than
  it flags real conflicts, delete the check and its tests and note that in
  the PR. Commit either way with message `feat: add possible-conflict check`
  or `chore: drop possible-conflict check`.

### Task 2.10: Scoring and report

**Files:**

- Create: `claude_md/scoring.py`, `claude_md/report.py`
- Modify: `analyze_claude_md.py` (remove `FileAnalysis`, `analyze_file`,
  `calculate_score`, old pattern constants and `check_attention_placement`;
  `main` calls discovery, `run_checks`, `score`, `render`)
- Test: `tests/test_scoring.py`, `tests/test_report.py`,
  `tests/test_fixtures_expected.py`, update `tests/test_cli_json_shape.py`

**Interfaces:**

- Produces:
  - `@dataclass(frozen=True) class Deduction: check_id: str; count: int;
    points: int; capped: bool`
  - `@dataclass(frozen=True) class Score: value: int; deductions:
    list[Deduction]`
  - `def score(findings: list[Finding]) -> Score`: starts at 100, subtracts
    `min(cap, weight * count)` per check id, floors at 0.
  - `def render(files, totals, findings, score, unverified) -> str`:
    findings grouped under "Backed by Anthropic docs" and "Heuristics",
    deductions listed, unverified limits listed.
  - JSON: `{"files", "totals", "findings", "score": {"value",
    "deductions"}, "unverified"}`.

- [ ] **Step 1: Write failing tests**: `test_score_starts_at_100`,
  `test_score_caps_per_check`, `test_score_floor_zero`,
  `test_heuristic_cap_lower_than_docs_cap`,
  `test_report_groups_by_source`, `test_report_lists_every_deduction`, and a
  parametrised `test_fixture_expected_ids` that runs every fixture through
  the CLI and checks `must_include` and `must_exclude` from `expected.json`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Implement** and delete the
  legacy code. **Step 4: Run** `uv run pytest -v` and
  `uv run ruff check .`. Expected: PASS.
- [ ] **Step 5: Commit** with message `feat: deduction-only scoring`.

### Task 2.11: Rewrite skill content and open the phase 2 PR

**Files:**

- Modify: `claude-md-optimizer/SKILL.md` (target under 100 lines),
  `claude-md-optimizer/references/optimization-rules.md`

Follow the spec's "Skill content" section. Every rule in the reference is
tagged `[docs]` or `[heuristic]` and the "Unverified" list is generated from
the script's `unverified` output.

- [ ] **Step 1: Rewrite both files** to the spec. Thresholds appear only in
  the script. The destination table is in SKILL.md.
- [ ] **Step 2: Run** `markdownlint` on both. Expected: exit 0.
- [ ] **Step 3: Re-run all four scenarios** 3 times each against the new
  skill and append results to the planning-branch baseline file. Every
  "Must not advise" line must now hold in all reps. If one fails, tighten
  the skill wording and re-run only that scenario.
- [ ] **Step 4: Commit** both files by path with message
  `docs: rewrite skill and rules reference`.
- [ ] **Step 5: Ask Rod**, then push and open a draft PR as in Task 0.5.

## Phase 3: documentation and description

Branch `chore/docs-and-description` from `main` after phase 2 merges.

### Task 3.1: Description, tables of contents, README, CHANGELOG, licence

**Files:**

- Modify: `claude-md-optimizer/SKILL.md` (frontmatter), `README.md`,
  `claude-md-optimizer/references/optimization-rules.md` (contents list),
  `LICENSE`
- Create: `CHANGELOG.md`

**Interfaces:**

- Produces: a `description` beginning "Use when" that states triggers only
  (audit, trim or restructure CLAUDE.md, rules or MEMORY.md; Claude
  ignoring instructions; startup size warnings), under 500 characters.

- [ ] **Step 1: Write a failing check** `tests/test_skill_frontmatter.py`:
  `test_description_starts_with_use_when`,
  `test_description_under_500_chars`,
  `test_description_has_no_line_limits` (no "150" or "50 lines"),
  `test_rules_reference_has_contents_list`.
- [ ] **Step 2: Run**: expect FAIL. **Step 3: Edit the files**. README is
  about 100 lines, with the example output regenerated by running the CLI
  on the `derivable-tree` fixture. CHANGELOG states that scores are not
  comparable with earlier versions. `LICENSE` gains a second copyright
  line for Rod.
- [ ] **Step 4: Run** `uv run pytest -v` and `markdownlint` on all changed
  Markdown. Expected: PASS and exit 0.
- [ ] **Step 5: Re-run all four scenarios** once each to confirm the new
  description still triggers the skill and the rubric still holds. Append
  results to the planning-branch baseline file.
- [ ] **Step 6: Commit** by path with message
  `docs: triggers-only description, README and changelog`.
- [ ] **Step 7: Ask Rod**, then push and open a draft PR as in Task 0.5.
