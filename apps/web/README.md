# OpenRange web

Learner-facing web shell for OpenRange: Next.js 15 (App Router), TypeScript
strict, Tailwind v4, and the shared `@openrange/ui` design system.

## Architecture decisions

### Data flow: everything goes through the server

The browser never talks to FastAPI directly. There are two call paths and both
are server-side:

1. **Server Components** read data with `lib/api-server.ts`, which builds an
   `ApiClient` from `@openrange/contracts` and forwards the visitor's
   `openrange_session` cookie (plus the CSRF header on mutations) to the API.
2. **Client Components** mutate through the same-origin route handler at
   `app/api/or/[...path]/route.ts`. The handler forwards method, path, query,
   JSON body, cookies, and `x-csrf-token` to `${ORIGIN_API_URL}/api/...` and
   relays every upstream `Set-Cookie` header.

Why proxying instead of direct client-to-API calls:

- No CORS configuration and no cross-site cookie rules to reason about.
- The httpOnly session cookie stays first-party on the web origin.
- The API can move behind a private network; only the web app needs reach it.
- One typed client (`@openrange/contracts`) serves both paths, so request and
  response shapes are defined exactly once.

### Auth model

FastAPI owns sessions. Login/register set an httpOnly `openrange_session`
cookie and a JS-readable `openrange_csrf` cookie; both are relayed through the
proxy. Every mutating browser call attaches `x-csrf-token` from that readable
cookie (`lib/api-browser.ts`); the API compares it against the session's
stored token. MFA-pending logins surface a second step in the login form
(`POST /api/auth/mfa/verify`) before redirecting to `/dashboard`.

### Catalog source of truth

Until the catalog API phase lands, `/catalog` and `/catalog/[slug]` read
`content/rooms/*/room.yaml` at build/dev time through `lib/content.ts`.
The loader parses YAML with the `yaml` package and validates the same field
enums as `packages/content-sdk` (difficulty, type, track) plus required
numeric fields; invalid bundles fail loudly instead of rendering. Set
`OPENRANGE_CONTENT_DIR` to point somewhere other than the repo checkout.
Filters write `?difficulty=&type=&track=` query params, so filtered views are
shareable URLs while the grid itself renders server-side.

### Styling and accessibility

- `packages/ui` owns tokens (`tokens.css`: near-black surfaces, single lime
  accent, danger red, warning amber) and component classes
  (`components.css`). Tailwind maps those variables into utilities via
  `@theme inline` in `app/globals.css`.
- Dark-first by design; there is no light theme to drift against.
- Keyboard support: skip link as first tab stop, visible focus rings
  everywhere, native `<dialog>` for modals (focus trap + Escape for free),
  WAI-ARIA tabs pattern in the Tabs primitive, reduced-motion-safe animations.
- Playwright runs axe on `/`, `/catalog`, `/login` at 320 px and 1280 px, plus
  a keyboard-only journey test.

## Local development

```bash
pnpm install
pnpm --filter web dev   # http://localhost:3100
```

Environment variables (see `.env.example` at the repo root):

- `ORIGIN_API_URL`: where FastAPI listens (default `http://localhost:8700`).
- `OPENRANGE_CONTENT_DIR`: override for the content bundle directory.

## Commands

```bash
pnpm exec turbo run lint typecheck build --filter=web...
pnpm --filter web test:e2e   # starts next dev on :3210 automatically
```
