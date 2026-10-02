# Ledgerly conventions

Detailed conventions for contributors and agents.

## Naming

- Use snake_case for functions and variables.
- Use PascalCase for classes.
- Name parsers after the bank: `monzo.py`, `starling.py`.
- Prefix private helpers with an underscore.
- Avoid single-letter names outside comprehensions.
- Boolean names start with is_, has_ or should_.
- Constants are UPPER_SNAKE_CASE at module top.
- Test names describe behaviour: `test_rejects_negative_balance`.

## Money

- Store amounts as integer pence.
- Convert to pounds only when rendering.
- Never compare money with floats.
- Use `Decimal` for interest calculations, then round half-even.
- Currency codes are ISO 4217 strings.
- Reject mixed-currency arithmetic with `CurrencyMismatch`.
- Round at the final step only, not in between.
- Display negatives with a leading minus, not brackets.

## Parsing

- Each parser exposes `parse(path) -> list[Transaction]`.
- Parsers never touch the database.
- Skip header rows by name, not by position.
- Normalise merchant names to title case.
- Strip card-number fragments from descriptions.
- Report unparseable rows through `ParseWarning`.
- Dates are parsed to `datetime.date` immediately.
- Keep a sample CSV for each parser in `tests/data/`.

## Errors

- Raise domain errors from `ledgerly/errors.py`.
- Catch exceptions only where you can act on them.
- Include the offending file name in error messages.
- Do not swallow exceptions with bare `except`.
- CLI commands convert domain errors to exit codes.
- Exit code 2 means bad input, 3 means parse failure.
- Log at warning level for skipped rows.
- Never log full account numbers.

## Testing

- One behaviour per test.
- Use `tmp_path` for any file output.
- Prefer real CSV samples over mocks.
- Parametrise parser tests across sample files.
- Do not assert on log output unless the log is the feature.
- Keep tests independent of the current date.
- Freeze time with `time-machine` where needed.
- Name fixtures after what they provide, not how.

## CLI

- Commands live in `ledgerly/cli.py` using `argparse`.
- Each subcommand has a `--dry-run` flag.
- Print summaries to stdout and warnings to stderr.
- Use plain text tables; no colour when not a TTY.
- Accept a directory or a single file wherever a path is expected.
- Return exit code 0 only when every file parsed.
- Keep help text to one line per option.
- Document new flags in the README.

## Reports

- Monthly summaries group by category then merchant.
- Sort categories by absolute spend, descending.
- Show the month-on-month change as a percentage.
- Round percentages to one decimal place.
- Uncategorised spend is listed last.
- Reports are pure functions of a transaction list.
- Write output via `write_report(stream)` for testability.
- Include a totals row even for empty months.

## Git

- Commit messages use the imperative mood.
- Keep commits focused on one change.
- Rebase before opening a pull request.
- Do not commit sample data containing real account details.
- Squash fixup commits before review.
- Branch names follow `feature/short-description`.
- Tag releases as `vMAJOR.MINOR.PATCH`.
- Update the changelog in the same pull request.

## Typing

- Annotate every public function.
- Use `X | None`, not `Optional[X]`.
- Prefer `Sequence` over `list` in parameters.
- Use frozen dataclasses for value objects.
- Avoid `Any`; use a protocol if needed.
- Run `mypy --strict` on `ledgerly/` in CI.
- Do not silence type errors without a reason in a comment.
- Use `TypedDict` for parsed JSON, never plain dicts.

## Documentation

- Docstrings explain why, not what.
- Keep the README example in sync with the CLI.
- Describe each parser's quirks in its module docstring.
- Link to the bank's format notes where they exist.
- Write changelog entries for user-visible changes only.
- Avoid TODO comments without an issue number.
- Diagrams go in `docs/img/`.
- Prefer examples over prose in guides.

## Dependencies

- Keep runtime dependencies to a minimum.
- Pin versions in `uv.lock` and commit it.
- Justify each new dependency in the pull request.
- Prefer the standard library for CSV and dates.
- Dev-only tools go in the dev group.
- Review dependency updates weekly.
- Remove unused imports before committing.
- Do not vendor third-party code.

## Style

- Format with `ruff format`.
- Lines are at most 88 characters.
- Use f-strings over `.format`.
- Prefer early returns to nested conditionals.
- Keep functions under 40 lines where practical.
- Use comprehensions only when they stay readable.
- Imports are grouped: stdlib, third-party, local.
- Avoid mutable default arguments.

## Security

- Never commit real statements or account numbers.
- Redact sort codes in test samples.
- Keep the import directory out of cloud-synced folders.
- Do not send transaction data to third-party services.
- Store API tokens in the system keychain, not in config files.
- Treat every CSV as untrusted input.

## Performance

- Stream large CSV files; do not read them whole.
- Batch database inserts in groups of 500.
- Index transactions by date and account.
- Avoid per-row queries inside parsers.
- Profile before optimising.
- Cache merchant lookups for the duration of one import.
