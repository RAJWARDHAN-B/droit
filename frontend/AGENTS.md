<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Droit frontend rules

- Keep route-specific workflows under `src/app/(app)/` and authentication pages under `src/app/(auth)/`.
- Reuse the existing components and API client before adding new UI abstractions.
- Keep API calls in `src/lib/api.ts` and represent loading, empty, error, and success states.
- Do not imply that a route is protected until the session client and backend authentication are connected.
- Run `npm run lint` and `npm run build` after route or component changes.
