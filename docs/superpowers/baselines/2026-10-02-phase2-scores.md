# Phase 2 scores

Scored strictly against the rubrics in tests/scenarios/*.md and README.md 'Scoring'. A run passes only if every line is PASS.

## audit-clean-file

Scorer note: A2 is vacuous in all reps: no CLAUDE.md edit is proposed; only an optional hook idea, which names an existing Gotchas bullet and adds no section. Scored PASS on the literal wording.

### Rep 1

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | File already in good shape, little/no change | PASS | Your CLAUDE.md is in good shape, so I recommend leaving it as it is |
| A2 | Any change is a small edit tied to a named existing line | PASS | no edits proposed; only optional PreToolUse hook idea tied to the 'do not add goroutines in internal/sched' bullet |
| N1 | No directory-structure/key files/critical paths section | PASS | no mention |
| N2 | No prohibitions/glossary/info-recording section | PASS | no mention |
| N3 | No sub-doc table/trigger index/split/imports/rules | PASS | 'Nothing applies only to some paths, so no paths: rule or nested CLAUDE.md is needed' |
| N4 | No score-only or missing-section justification | PASS | scores 100/100, not used as justification |
| N5 | No rewrite of existing lines without functional reason | PASS | 'I'm making no changes' |

**Run verdict: PASS**

Notes (unscored): HOME override: not stated as blocked ('the sandbox allowed this when done through a Python subprocess'). Facts OK. Harmful: none.

### Rep 2

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | File already in good shape, little/no change | PASS | Your CLAUDE.md is in good shape, so I recommend no changes |
| A2 | Any change is a small edit tied to a named existing line | PASS | no edits; optional hook idea for error-wrapping/test layout lines (not a CLAUDE.md edit) |
| N1 | No directory-structure/key files/critical paths section | PASS | no mention |
| N2 | No prohibitions/glossary/info-recording section | PASS | no mention |
| N3 | No sub-doc table/trigger index/split/imports/rules | PASS | 'nothing is path-specific enough to need a paths: rule' |
| N4 | No score-only or missing-section justification | PASS | 'score is this tool's own measure' |
| N5 | No rewrite of existing lines without functional reason | PASS | 'Adding sections, reformatting or splitting it would have no functional benefit' |

**Run verdict: PASS**

Notes (unscored): HOME override: blocked in shell, worked via Python subprocess. Facts OK. Harmful: none.

### Rep 3

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | File already in good shape, little/no change | PASS | Your CLAUDE.md is in good shape, so I'd leave it alone |
| A2 | Any change is a small edit tied to a named existing line | PASS | no edits; optional hook on the goroutines gotcha, 'I wouldn't push it' |
| N1 | No directory-structure/key files/critical paths section | PASS | no mention |
| N2 | No prohibitions/glossary/info-recording section | PASS | no mention |
| N3 | No sub-doc table/trigger index/split/imports/rules | PASS | 'Nothing is path-specific enough to need a paths: rule or a nested CLAUDE.md' |
| N4 | No score-only or missing-section justification | PASS | score described as tool's own measure |
| N5 | No rewrite of existing lines without functional reason | PASS | 'I suggest no changes' |

**Run verdict: PASS**

Notes (unscored): HOME override: blocked by worktree guard, worked via Python subprocess. Facts OK. Harmful: none.

**audit-clean-file tally: 3/3 runs passed**

## audit-derivable-tree

### Rep 1

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Remove Project structure tree | PASS | 'Delete the Project structure section (lines 5-27)' |
| A2 | Remove Dependencies list | PASS | 'Delete the Dependencies section (lines 29-38)' |
| A3 | Remove Architecture overview | PASS | 'Delete the Architecture paragraph (lines 40-48)' |
| A4 | Keep Commands | PASS | Keep as is: 'Commands' |
| A5 | Keep Gotchas | PASS | Keep as is: 'Gotchas' |
| N1 | No new structure/key files/critical paths section or rewritten tree | PASS | 'Nothing else needs adding, reordering or splitting' |
| N2 | No moving tree/deps/architecture to sub-doc/import/file as a way to keep it | PASS | 'I'd delete it outright rather than condense it or move it to another file' |
| N3 | No condensed/summarised tree, deps or architecture kept (decision lines allowed) | PASS | only optional 'SQLite in development, Postgres in production' line kept (allowed decision line) |

**Run verdict: PASS**

Notes (unscored): HOME override blocked in shell, done via Python subprocess. Facts OK. Harmful: none (optional hook/test for fractions rule is fine).

### Rep 2

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Remove Project structure tree | PASS | 'Delete Project structure (lines 5-26)' |
| A2 | Remove Dependencies list | PASS | 'Delete Dependencies (lines 28-37)' |
| A3 | Remove Architecture overview | PASS | 'Delete the prose in Architecture (lines 39-48)' |
| A4 | Keep Commands | PASS | Keep as is: 'Commands (lines 50-54)' |
| A5 | Keep Gotchas | PASS | Keep as is: 'Gotchas (lines 56-60)' |
| N1 | No new structure/key files/critical paths section or rewritten tree | PASS | no new sections proposed |
| N2 | No moving tree/deps/architecture to sub-doc/import/file as a way to keep it | PASS | 'drop it completely rather than condense it or move it to another file'; 'I haven't created any imports or sub-documents' |
| N3 | No condensed/summarised tree, deps or architecture kept (decision lines allowed) | PASS | only optional SQLite/Postgres single line kept (allowed) |

**Run verdict: PASS**

Notes (unscored): HOME override blocked in shell, done via Python subprocess. Facts OK. Harmful: none.

### Rep 3

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Remove Project structure tree | PASS | 'Lines 5-26 ... I suggest deleting the whole section, not condensing it or moving it elsewhere' |
| A2 | Remove Dependencies list | PASS | 'Lines 28-37 ... I suggest deleting the section' |
| A3 | Remove Architecture overview | PASS | 'Lines 39-48, Architecture ... I suggest deleting it' |
| A4 | Keep Commands | PASS | 'The Commands section (lines 50-54) ... leave them alone' |
| A5 | Keep Gotchas | PASS | 'The Gotchas section (lines 56-60)' kept |
| N1 | No new structure/key files/critical paths section or rewritten tree | PASS | no new sections proposed |
| N2 | No moving tree/deps/architecture to sub-doc/import/file as a way to keep it | PASS | no relocation proposed; deletion only |
| N3 | No condensed/summarised tree, deps or architecture kept (decision lines allowed) | PASS | only optional SQLite/Postgres single line kept (allowed) |

**Run verdict: PASS**

Notes (unscored): HOME override blocked in shell (worktree guard), done via Python subprocess. Facts OK. Harmful: none.

**audit-derivable-tree tally: 3/3 runs passed**

## enforce-with-hooks

### Rep 1

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Use hooks (PostToolUse/PreToolUse) for must-happen rules | PASS | PostToolUse on Edit|Write for ruff check; PreToolUse on Bash for git commit; PreToolUse blocking _generated |
| A2 | State CLAUDE.md is advisory, not enforced | PASS | 'It is context, not enforced configuration ... Only a hook runs every time' |
| N1 | No claim that stronger wording/caps/MUST guarantees compliance | PASS | 'no wording such as Always or Never guarantees Claude follows it' |
| N2 | No emphatic-CLAUDE.md-only mechanism without hooks | PASS | hooks are the mechanism |

**Run verdict: PASS**

Notes (unscored): HOME override: worked (not blocked). Facts OK. Minor: PostToolUse ruff hook does not spell out exit code 2/JSON needed to feed failures back (the commit hook does). Harmful: none.

### Rep 2

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Use hooks (PostToolUse/PreToolUse) for must-happen rules | PASS | PostToolUse, Stop, PreToolUse hooks with exit code 2 |
| A2 | State CLAUDE.md is advisory, not enforced | PASS | 'A CLAUDE.md line can't guarantee that ... Until the hooks exist, the lines in CLAUDE.md are only advisory' |
| N1 | No claim that stronger wording/caps/MUST guarantees compliance | PASS | 'no wording or emphasis makes it certain' |
| N2 | No emphatic-CLAUDE.md-only mechanism without hooks | PASS | hooks are the mechanism |

**Run verdict: PASS**

Notes (unscored): HOME override: worked (not blocked). Facts OK. Harmful: none.

### Rep 3

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Use hooks (PostToolUse/PreToolUse) for must-happen rules | PASS | table of PostToolUse/Stop/PreToolUse hooks in .claude/settings.json |
| A2 | State CLAUDE.md is advisory, not enforced | PASS | 'CLAUDE.md is the wrong tool ... no wording or emphasis guarantees Claude follows it'; 'the CLAUDE.md line is only advisory' |
| N1 | No claim that stronger wording/caps/MUST guarantees compliance | PASS | explicit denial |
| N2 | No emphatic-CLAUDE.md-only mechanism without hooks | PASS | hooks are the mechanism |

**Run verdict: PASS**

Notes (unscored): HOME override: blocked in Bash, worked via Python subprocess. Facts OK. Harmful: none.

**enforce-with-hooks tally: 3/3 runs passed**

## explain-context-cost

Scorer note: A3 is judged met in all reps by the instruction to run /context to confirm what loaded (rubric wording 'Check what actually loaded with /context'). A1 is met by the 200-line comparison plus advice to shrink; rep1 states most directly that the moves bring it under 200.

### Rep 1

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Get CLAUDE.md under ~200 lines (file is 260) | PASS | '260 lines ... 60 lines over Anthropic's recommended 200'; moving ~100 lines 'would bring you under 200 lines' |
| A2 | Move path-specific sections to paths: rules / nested CLAUDE.md / skills | PASS | 'Move area-specific sections into path-scoped rules (.claude/rules/*.md with paths: frontmatter)': Frontend, Database, Testing, Reports, Manifests... |
| A3 | Check loaded content with /context | PASS | 'Run /context in a real session to see them'; 'run /context in a new session' |
| N1 | No claim CLAUDE.md is re-injected every request | PASS | 'This loads once at session start. It is not a cost that repeats on every request.' |
| N2 | No cost-compounds-per-turn claim | PASS | same quote; no per-turn growth claimed |
| N3 | No fixed 150/100/50-line limit as official | PASS | only the 200-line recommendation |

**Run verdict: PASS**

Notes (unscored): HOME override: analyser run with empty HOME, block not mentioned. Facts OK (imports load at launch). Harmful: none. Payments not named but rubric says 'for example'.

### Rep 2

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Get CLAUDE.md under ~200 lines (file is 260) | PASS | '260 lines ... 60 over Anthropic's recommended 200'; advises moving most detail out |
| A2 | Move path-specific sections to paths: rules / nested CLAUDE.md / skills | PASS | 'Move domain detail to path-scoped rules ... .claude/rules/ with a paths: frontmatter' (Payments, Frontend, Database, Manifests listed) |
| A3 | Check loaded content with /context | PASS | 'ask you to run /context in a new session to confirm'; 'If your /context shows much more...' |
| N1 | No claim CLAUDE.md is re-injected every request | PASS | 'loads once at session start. That cost does not recur on every request' |
| N2 | No cost-compounds-per-turn claim | PASS | 'does not ... grow with the number of turns' |
| N3 | No fixed 150/100/50-line limit as official | PASS | only the 200-line recommendation |

**Run verdict: PASS**

Notes (unscored): HOME override: inline blocked, done via Python subprocess. Facts OK (block HTML comments are stripped: correct). Harmful: none, though moving nearly every domain section (Bookings, Pricing) to rules is aggressive.

### Rep 3

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Get CLAUDE.md under ~200 lines (file is 260) | PASS | '260 lines ... 60 lines over Anthropic's recommended 200 per file'; options to move sections out |
| A2 | Move path-specific sections to paths: rules / nested CLAUDE.md / skills | PASS | 'Move area-specific sections into paths: rules under .claude/rules/' (Payments, Frontend, Database, Manifests, Reports...); skills for Local setup/Release |
| A3 | Check loaded content with /context | PASS | 'run /context in a fresh session to confirm the Memory files list' |
| N1 | No claim CLAUDE.md is re-injected every request | PASS | 'the cost is paid once, when the session starts. It does not grow with each turn' |
| N2 | No cost-compounds-per-turn claim | PASS | 'It does not grow with each turn' |
| N3 | No fixed 150/100/50-line limit as official | PASS | only the 200-line recommendation |

**Run verdict: PASS**

Notes (unscored): HOME override: blocked and NOT worked around; totals therefore include Rod's personal ~/.claude files (answer says so). Facts OK. Harmful: none.

**explain-context-cost tally: 3/3 runs passed**

## split-with-imports

### Rep 1

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Use path-scoped rules / nested CLAUDE.md / skills to cut always-loaded context | PASS | 'a rule file in .claude/rules/ with paths: frontmatter would load them only when Claude works on matching files' |
| A2 | State @docs/conventions.md loads at launch, so import does not reduce context | PASS | 'An @path import loads at launch, together with the file that imports it' |
| A3 | Correct the 'loaded on demand' claim | PASS | 'Both halves are wrong ... reword those two lines' |
| N1 | No splitting into more @imports/sub-docs to save context | PASS | 'no further splitting or new sub-documents are worth doing' |
| N2 | No describing existing import as saving context/lazy | PASS | 'Keeping the import is fine; just don't count on it to save tokens' |

**Run verdict: PASS**

Notes (unscored): HOME override: worked (not blocked). Facts OK. Harmful: none.

### Rep 2

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Use path-scoped rules / nested CLAUDE.md / skills to cut always-loaded context | PASS | 'move the path-specific sections into .claude/rules/ files with paths: frontmatter' (Parsing, Testing, CLI, Reports) |
| A2 | State @docs/conventions.md loads at launch, so import does not reduce context | PASS | 'loads at session start, together with CLAUDE.md. Both files are always-on' |
| A3 | Correct the 'loaded on demand' claim | PASS | 'CLAUDE.md lines 13-14 ... That is incorrect'; fix wording |
| N1 | No splitting into more @imports/sub-docs to save context | PASS | 'Don't create further imports or sub-documents to cut context' |
| N2 | No describing existing import as saving context/lazy | PASS | 'Just don't expect it to shrink anything' |

**Run verdict: PASS**

Notes (unscored): HOME override: not mentioned. Facts OK. Harmful: none.

### Rep 3

| Id | Rubric line | Verdict | Evidence |
| --- | --- | --- | --- |
| A1 | Use path-scoped rules / nested CLAUDE.md / skills to cut always-loaded context | PASS | 'Path-scoped rules in .claude/rules/ with paths: frontmatter' (Parsing, Testing) |
| A2 | State @docs/conventions.md loads at launch, so import does not reduce context | PASS | 'An @path import loads at session start, together with the file that imports it. So the split saved nothing' |
| A3 | Correct the 'loaded on demand' claim | PASS | 'lines 13-14 of CLAUDE.md are wrong'; replace the sentence |
| N1 | No splitting into more @imports/sub-docs to save context | PASS | 'I wouldn't add new imports or sub-documents to shrink context' |
| N2 | No describing existing import as saving context/lazy | PASS | 'So the split saved nothing' |

**Run verdict: PASS**

Notes (unscored): HOME override: blocked in Bash, worked via Python subprocess. Facts OK. Harmful: none. Ambiguity: it says a plain 'see docs/conventions.md' pointer 'would load nothing by itself' - explanatory, not advice to split for savings, so N1 scored PASS.

**split-with-imports tally: 3/3 runs passed**

## Overall

**15/15 runs passed.**
