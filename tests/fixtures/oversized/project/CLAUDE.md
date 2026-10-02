# Harbourlight

## Overview

- Harbourlight is a Django monolith that runs the booking system for a small ferry company.
- It serves a public booking site, a staff admin and a JSON API for the mobile app.
- Production runs on a single Postgres instance with Redis for caching and Celery.

## Commands

- `uv run python manage.py runserver` starts the dev server.
- `uv run pytest -n auto` runs tests in parallel.
- `uv run python manage.py makemigrations --check` verifies migrations are current.
- `uv run ruff check --fix .` lints and fixes.
- `docker compose up db redis` starts backing services.
- `uv run celery -A harbourlight worker -l info` starts a worker.
- `uv run python manage.py loaddata fixtures/demo.json` seeds demo data.
- `make docs` builds the Sphinx documentation.

## Bookings

- A booking has one or more passengers and zero or more vehicles.
- Capacity is checked inside a transaction with `select_for_update` on the sailing.
- Holds expire after 15 minutes via a Celery beat task.
- Cancellations within 48 hours of departure are non-refundable.
- Refunds are issued through the payment provider wrapper, never directly.
- Booking references are six characters from an unambiguous alphabet.
- Booking references are never reused, even for cancelled bookings.
- Group bookings over 20 passengers need staff approval.
- Foot passengers and vehicles have separate capacity pools per sailing.
- Dog and bicycle supplements are line items, not booking flags.

## Pricing

- Prices come from `FareTable` rows effective on the sailing date.
- Peak surcharges apply on Fridays and Saturdays from May to September.
- Child fares apply to ages 5 to 15 inclusive.
- Under-fives travel free but still count towards the manifest.
- Vehicle fares are by length band, not by vehicle type.
- Discount codes are validated in `pricing.discounts`, one code per booking.
- All prices are in pence; VAT is included in displayed fares.
- Prices are computed by `quote_booking`, never in a template.
- Fare changes need a new `FareTable` row, never an update to an old one.
- Currency conversion for the mobile app happens client-side.

## Timetables

- Sailings are generated from `Timetable` templates by a nightly task.
- Weather cancellations are recorded as `SailingStatus.CANCELLED` with a reason.
- A sailing that has bookings is cancelled and notified, not deleted.
- Times are stored in Europe/London local time with an explicit zone.
- Clock changes are handled by `zoneinfo`, not manual offsets.
- The generator is idempotent; running it twice creates no duplicates.
- Winter timetables start on the last Sunday of October.
- Special sailings are created in the admin with a custom template.

## Notifications

- Emails are sent via the `notify` app using templated messages.
- SMS is used only for sailing cancellations and delays.
- Every notification is logged in `NotificationLog` with the provider response.
- Failed sends retry with exponential backoff, maximum five attempts.
- Marketing email goes only to people with the consent flag.
- Unsubscribe links are signed and expire after 30 days.
- Template changes need a screenshot in the pull request.
- Test emails go to the console backend in development.

## API

- The API lives in `api/` and uses Django REST Framework.
- The API is versioned in the URL: `/api/v1/`.
- Serializers validate; views orchestrate; services do the work.
- Pagination is cursor-based for lists that can grow without bound.
- Errors use the shape `{"code": ..., "detail": ...}`.
- Authentication is token based; tokens rotate every 90 days.
- Rate limits are 60 requests per minute per token.
- Breaking changes require a new API version.
- Every endpoint has a drf-spectacular decorator.
- Mobile clients pin to a minimum API version in their settings.

## Database

- Migrations are squashed once a year, in January.
- Deployed migrations are never edited.
- Indexes are added in a separate migration from the column they cover.
- Data migrations use `RunPython` with a reverse function.
- Large backfills run as management commands, not migrations.
- Foreign keys use `PROTECT` unless there is a clear reason.
- Soft-delete is used for passengers; hard delete is used for sessions.
- Raw SQL lives in `db/queries/` with a test for each query.
- Timestamps use `timezone.now`, never `datetime.now`.
- Read replicas are not configured, so there are no database routers.

## Testing

- Tests live next to the app in `tests/` directories.
- Use `pytest-django` with the `db` fixture only when needed.
- Factories are in `tests/factories.py` using factory_boy.
- Mock the payment provider at the HTTP boundary with `responses`.
- Time-sensitive tests use `time-machine`.
- Unit tests use the dummy cache rather than Redis.
- End-to-end tests run with Playwright in a separate CI job.
- Flaky tests are quarantined with a marker and an issue link.
- Tests should read as examples of the feature.
- Coverage is tracked but not gated.

## Security

- Secrets come from environment variables, never from the repo.
- Passenger names and dates of birth are personal data and are not logged.
- Database access goes through the ORM or parameterised queries only.
- CSRF protection stays on for every non-API view.
- Admin access requires two-factor authentication.
- File uploads are limited to 5 MB and scanned before storage.
- Dependency alerts are triaged within a week.
- Payment card data never touches our servers.
- Session cookies are secure and HTTP-only in production.
- Changes to `settings/production.py` need two reviewers.

## Deployment

- Deploys run from GitHub Actions on merge to `main`.
- Migrations run before the new code is switched in.
- Static files are served from S3 behind a CDN.
- Feature flags are managed in `flags.py` and removed after two releases.
- Rollback is a redeploy of the previous image tag.
- Celery workers are restarted after each deploy.
- The staging booking flow is checked before a production deploy is approved.
- Maintenance mode is a flag in Redis, not a code change.
- Sentry release tracking is configured in the deploy workflow.
- Database backups are verified monthly by restoring to staging.

## Frontend

- Public pages use Django templates with HTMX for partial updates.
- JavaScript lives under `static/js/` with no build step.
- CSS uses a small utility set in `static/css/utilities.css`.
- All forms need a visible label and an error message region.
- Images have alt text; decorative images use an empty alt.
- The first two booking steps work without JavaScript.
- Layouts are checked at 360 pixel width before 1280.
- The shared date picker component is the only date picker.
- Colours come from CSS custom properties in `tokens.css`.
- Icons are inline SVG from `templates/icons/`.

## Support

- Support tickets arrive in the shared inbox and are triaged daily.
- Refund requests over 200 pounds need a second approver.

## Glossary

- A sailing is one scheduled crossing; a timetable is the template that generates it.
- A manifest is the final passenger and vehicle list sent to the harbour master.

## Release process

- Release candidates are cut on Thursdays and soak on staging until Monday.
- The changelog is generated from pull request titles.

## Observability

- Dashboards live in Grafana under the Harbourlight folder.
- Alerts page on-call only for failed payments and stalled Celery queues.

## Accessibility

- Aim for WCAG 2.1 AA on all public pages.
- Run the axe check in CI on the booking flow.

## Localisation

- The site is English only, but strings are wrapped for translation.
- Dates are displayed in the form 3 May 2026.

## Performance

- The sailings list must render in under 300 ms with a warm cache.
- Use `select_related` on any view that lists bookings.

## Payments

- Payments go through the `payments.provider` wrapper around Stripe.
- Webhooks are verified by signature before any processing.
- Webhook handlers are idempotent and keyed on the event id.
- Failed payments release the capacity hold immediately.
- Partial refunds are supported; the remainder stays on the booking.
- Disputes are handled manually by finance, not in code.
- Test card numbers are listed in `docs/payments.md`.
- Never store provider customer ids on the passenger record.

## Staff admin

- The admin is the standard Django admin with custom actions.
- Staff roles are Django groups: Reservations, Operations, Finance.
- Only Operations can cancel a sailing.
- Only Finance can issue manual refunds.
- Bulk actions require a confirmation page.
- Admin list views must not issue more than 10 queries.
- Custom admin pages live in `admin_extras/`.
- Audit every admin change through `django-simple-history`.

## Manifests

- The manifest is emailed to the harbour master 60 minutes before departure.
- It lists passengers by name, age band and vehicle registration.
- Late bookings after the manifest is sent are phoned through.
- Manifests are generated as PDF using WeasyPrint.
- Keep manifests for seven years in cold storage.
- Redact dates of birth in the emailed copy.
- A corrected manifest supersedes, never replaces, the original.
- Test PDFs render on A4 with a four-line header.

## Background tasks

- Tasks live in `tasks.py` inside each app.
- Tasks take ids, not model instances.
- Every task is safe to run twice.
- Long tasks report progress through `TaskProgress` rows.
- Use `acks_late` for tasks that send external messages.
- Beat schedule is defined in `harbourlight/celery.py`.
- Dead-letter failures are visible in the admin under Failed tasks.
- Queues are split into `default`, `email` and `reports`.

## Logging

- Use `structlog` with key-value pairs, not formatted strings.
- Bind the booking reference to the logger inside booking views.
- Log levels: info for business events, warning for recoverable oddities.
- Do not log request bodies from the payment endpoints.
- Logs ship to Loki; keep lines under 8 KB.
- Add a request id to every log line via middleware.
- Noisy third-party loggers are silenced in `settings/base.py`.
- Use `logger.exception` only inside `except` blocks.

## Reports

- Finance reports are materialised nightly into `reporting_*` tables.
- Report queries must not run against live booking tables in business hours.
- CSV exports stream rather than build in memory.
- Revenue is reported by sailing date, not booking date.
- Occupancy is capacity used divided by capacity available.
- Cancelled bookings are excluded from occupancy but included in refunds.
- Report definitions are tested against a small seeded dataset.
- Ask Finance before changing a report's column order.

## Local setup

- Python 3.13 and uv are required.
- Copy `.env.example` to `.env` and fill in the Stripe test keys.
- Run `docker compose up db redis` before the first test run.
- Run `uv run python manage.py migrate` after pulling.
- The demo fixtures include two ports and a week of sailings.
- If migrations conflict, rebase and regenerate rather than merging them.
- Use `direnv` to load `.env` automatically if you have it.
- On Apple silicon, use the arm64 Postgres image in compose.

## Contacts

- Ops questions go to #harbourlight-ops.
