# Scenario: split-with-imports

## Fixture

`tests/fixtures/import-for-savings/project/` (Ledgerly, a CLAUDE.md
that imports `@docs/conventions.md` and claims this saves context and
loads on demand).

## Prompt

```text
Split this up to save context.
```

## Must advise

- Use path-scoped rules (`.claude/rules/` files with `paths:`
  frontmatter), nested CLAUDE.md files or skills to cut always-loaded
  context.
- State that `@docs/conventions.md` is loaded at launch together with
  CLAUDE.md, so the import does not reduce context.
- Correct the CLAUDE.md claim that the import is "loaded on demand".

## Must not advise

- Splitting content into more `@imports` or sub-documents as a way to
  save context.
- Describing the existing `@docs/conventions.md` import as saving
  context or loading lazily.
