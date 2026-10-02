# Beacon Dashboard

React dashboard for monitoring uptime checks.

## Commands

- `npm run dev` starts Vite on port 5173.
- `npm test` runs Vitest.

## Rules

- IMPORTANT: use the `useQuery` wrapper in `src/hooks/`, not raw fetch.
- You MUST write a test for every new component.
- NEVER import from `src/legacy/`.
- IMPORTANT: all dates are formatted through `formatDate` in `src/lib/dates.ts`.
- CRITICAL: do NOT add new dependencies without asking first.
- You MUST use named exports; default exports break our codemods.
- NEVER store tokens in localStorage.
- IMPORTANT: keep components under 200 lines.
- ALWAYS USE THE DESIGN TOKENS FROM `src/theme.ts` FOR COLOURS.
- You MUST NOT disable ESLint rules inline.
- VERY IMPORTANT: ALL API CALLS GO THROUGH `src/api/client.ts`.
- MUST handle loading AND error states in every data component.
