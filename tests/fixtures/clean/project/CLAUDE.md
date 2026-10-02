# Kettle

Small Go service that schedules brew-time reminders.

## Commands

- `go test ./...` runs the unit tests.
- `make integration` runs the integration tests; it needs Docker.

## Gotchas

- Timestamps in the `reminders` table are stored in UTC. Convert to the user's
  zone only in `internal/render`.
- The scheduler loop in `internal/sched` is single-threaded on purpose. Do not
  add goroutines there without discussing it first.
- Integration tests share one Postgres container, so give each test its own
  schema via `testdb.NewSchema(t)`.

## Conventions

- Return wrapped errors with `fmt.Errorf("doing x: %w", err)`.
- Table-driven tests go in `_test.go` files next to the code they cover.
