# Changelog

## Unreleased

Scores are not comparable with earlier versions. The old score deducted per
issue, warning and suggestion, and added bonuses for structure such as
trigger conditions and prohibitions sections. The new score has no bonuses
and caps the deduction for each check, so the same file can score very
differently.

### Changed

- The analyser models what Claude Code actually loads: managed, user,
  ancestor, project and local files, rules (including `paths:` rules),
  nested files, `@` imports, `AGENTS.md` as a fallback, `claudeMdExcludes`
  and auto memory.
- Findings are tagged `docs` (with the Anthropic page URL) or `heuristic`.
  Limits the docs do not confirm are reported as unverified.
- The per-file size recommendation is Anthropic's 200 lines. The old 150,
  50 and 30 line limits are gone.
- The skill `description` states triggers only.
- `SKILL.md` and the rules reference are rewritten to match Anthropic's
  current memory docs. Claims about recurring per-request cost and about
  imports loading on demand are removed.
- The README is rewritten, and the example report comes from the current
  analyser.

### Added

- A pytest suite with fixture projects and recorded skill scenarios.
- Checks for derivable content, hook candidates, emphasis dilution, scope
  candidates, import misconceptions, stale references and possible
  conflicts.
- The `LICENSE` file names the fork's maintainer alongside the original
  author.

### Removed

- The "8-priority" workflow and the claim that instruction following
  "degrades linearly".
