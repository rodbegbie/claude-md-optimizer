# Postcard

Node service that renders and sends transactional emails.

## Commands

- `npm run build` compiles TypeScript to `dist/`.
- `npm run nope` runs the template previewer.
- `npm test` runs the Jest suite.

## Layout notes

- Email templates live in `src/templates.ts`.
- The old SMTP helper in `src/missing.py` handles retries; leave it alone.
- Retry policy is configured in `src/templates.ts` and read at start-up.

## Conventions

- Keep template functions pure; they take data and return an HTML string.
- Send through the provider wrapper, never the SDK directly.
