# Scenario: audit-derivable-tree

## Fixture

`tests/fixtures/derivable-tree/project/` (Recipe Box, a Flask app whose
CLAUDE.md has a directory tree, a pinned dependency list and an
architecture paragraph).

## Prompt

```text
Optimise my CLAUDE.md.
```

## Must advise

- Remove the "Project structure" directory tree, because Claude can
  derive it by reading the repository.
- Remove the "Dependencies" list (flask, pytest, ruff and so on),
  because it duplicates `pyproject.toml`.
- Remove the "Architecture" overview (app factory, blueprints, models),
  because Claude can derive it from the code.
- Keep the "Commands" section (`flask run`, `pytest`, `db migrate`).
- Keep the "Gotchas" (fractions for ingredient quantities, unset
  `SERVER_NAME` in tests), because they are not derivable.

## Must not advise

- Adding a directory-structure, "key files" or "critical paths"
  section, or any rewritten version of the tree.
- Moving the tree, dependency list or architecture content into a
  sub-document, `@import` or separate file as a way to keep it.
- Keeping the tree, dependency list or architecture overview in
  condensed or summarised form.
