# Web frontend stack guide: TypeScript, React-style components

Follow the repository's framework and conventions. Use this guide for new code. Check current versions in npm before pinning anything new.

## TypeScript
- Strict mode on. No `any` without a comment that explains why; prefer `unknown` plus narrowing.
- Type API responses at the boundary (generated types or schema validation with zod), so the rest of the app works with trusted types.

## Structure
- Feature folders (`src/features/orders/`) holding components, hooks, API calls, types, and tests together. Shared, generic components live in `src/components/`.
- Components are small and do one job. Pages compose them; they do not hold business rules.

## State
- Keep state as local as possible: component state first, then context for a small shared value, then a store (Zustand or Redux Toolkit) only when many distant components need it.
- Server data belongs in a query library such as TanStack Query, with explicit cache keys and invalidation, not copied into a global store.
- Forms: react-hook-form with zod schemas, so validation rules live in one place.

## Styling
- Use the repository's approach (CSS modules, Tailwind, or a component library) and its design tokens. No hard-coded colors, spacing, or font sizes (ui-design skill).

## Data fetching and errors
- One typed API client with base URL, auth header, timeouts, and error mapping in one place.
- Every view that loads data handles loading, empty, and error states.
- Frontend environment variables are public by definition. Never put secrets in them.

## Performance
- Split code by route. Lazy-load heavy components.
- Memoize only when a measurement shows a problem.
- Size images correctly, serve modern formats, and reserve space to avoid layout shift.

## Accessibility
Semantic HTML first (button, nav, main, label), ARIA only to fill gaps, keyboard access for everything, and visible focus (ui-design skill).

## Quality commands
Use the scripts in package.json, typically `npm run lint`, `npm run typecheck` (or `tsc --noEmit`), `npm test` (Vitest or Jest), and `npx playwright test` for end-to-end tests.

## Next.js notes, if the repository uses it
Keep server-only code (secrets, database access) in server components, route handlers, or server actions. Mark client components explicitly and keep them small. Fetch data on the server where possible.
