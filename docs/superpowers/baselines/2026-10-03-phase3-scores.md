# Phase 3 scenario re-run

Task 3.1, step 5. Checks that the triggers-only description and the
README, CHANGELOG and LICENSE edits did not change the skill's advice.

## Setup

- Checkout under test: branch `chore/docs-and-description` at `184cead`.
- Protocol: `tests/scenarios/README.md`. Fresh general-purpose subagent
  per run, explicit path to the checkout's `SKILL.md`, `HOME` set to an
  empty temporary directory, advice only.
- Model: `sonnet` alias, the same as the Phase 2 runs.
- Repetitions: 1 per scenario. The plan asks for one each. Phase 2 used
  three.
- Scenarios: 5. The plan says four, but `tests/scenarios/` holds five.
- No clarifying questions were asked in any run.
- Raw advice is in `phase3-runs/<scenario>-rep1.txt`.

## Scores

| Scenario | Must advise | Must not advise | Result |
| --- | --- | --- | --- |
| audit-clean-file | 2/2 | 0 violations | PASS |
| audit-derivable-tree | 5/5 | 0 violations | PASS |
| enforce-with-hooks | 2/2 | 0 violations | PASS |
| explain-context-cost | 3/3 | 0 violations | PASS |
| split-with-imports | 3/3 | 0 violations | PASS |

5 of 5 scenario runs pass.

## Notes

- audit-derivable-tree offered to keep one line recording
  "SQLite in development, Postgres in production". The rubric allows it.
- audit-clean-file mentioned an optional `PreToolUse` hook for the
  scheduler rule and said no file change was needed. The rubric does not
  forbid that.
- explain-context-cost said every section "costs context whether or not
  the task touches it" at session start. It made no per-request or
  per-turn claim.

## Limits of this check

- Each run is given the path to `SKILL.md`, so it does not test whether
  the new `description` makes Claude Code select the skill from a user
  request. Selection is untested. It needs the skill installed and a fresh
  session.
- One repetition per scenario shows no more than that the rubric still
  holds on this sample.
