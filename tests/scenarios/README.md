# Skill-behaviour scenarios

Manual tests of what the claude-md-optimizer skill advises. Each
scenario file holds a fixture, a prompt and a rubric of lines to score.

## Run protocol

1. Each run uses a fresh general-purpose subagent with no prior
   context.
2. The subagent's working directory is
   `tests/fixtures/<fixture>/project/` of the checkout under test.
3. The controller's setup line tells the subagent to read
   `<checkout>/claude-md-optimizer/SKILL.md` and follow that skill,
   using the files in that checkout. Give the explicit path. Never use
   the installed copy at `~/.claude/skills`, which may be missing or
   stale. The setup line also says to give advice only and not to
   modify any files.
4. Do 3 repetitions per scenario. Record each repetition's advice
   verbatim, and score every rubric line.
5. Record results in a baseline document on the planning branch, not in
   this repository's main line.

### Setup line used

These are the standard additions to item 3 for every run, so that a
re-run is comparable with the baseline:

- When you run its analysis script, run it with HOME set to an empty
  temporary directory (for example `HOME=$(mktemp -d)`) so that only
  this project is analysed.
- Give advice only: do not modify, create or delete any file, except
  the single output file named below.
- When you have your answer, write it to `<output file>` exactly as you
  would say it to the user (your full reply, verbatim), then reply with
  only the word: done

If the sandbox blocks the HOME override, the runner notes that in the
record.

## Isolation

- Never show the subagent the scenario file, the rubric, or the words
  "Must advise" or "Must not advise".
- The scenario's Prompt, verbatim, is the only user message the
  subagent receives. The only other instruction is the setup line
  above.
- If the subagent asks a clarifying question, answer exactly "Use your
  best judgement." and note in the record that this happened.
- Record the model used for each run. Use the same model for every run
  of a comparison (baseline versus later re-run).

## Scoring

- Record every rubric line as PASS or FAIL.
- A "Must advise" line is PASS only if the transcript clearly shows it.
  If the advice never mentions it, or meets it only partly, it is FAIL.
- A "Must not advise" line is PASS only if the transcript clearly does
  not contain the forbidden advice. If it appears, even hedged, it is
  FAIL.
- A scenario run passes only if every line is PASS.
