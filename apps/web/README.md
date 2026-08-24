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

### Learning, challenges, notifications

`/learn`, `/learn/[pathSlug]`, `/learn/[pathSlug]/[moduleSlug]`,
`/challenges`, and `/notifications` read and mutate through the same-origin
proxy from client components (`lib/api-browser.ts`). These surfaces are
inherently per-user and interactive, so the browser owns the fetch lifecycle:
loading skeletons first, an inline sign-in prompt on 401/403, and a problem-
details error banner otherwise. Response types live once in
`@openrange/contracts` (`ApiClient.learning`, `.challenges`, `.notifications`);
the web app casts nothing.

Two behaviors worth knowing:

- Quiz feedback shows only per-question correctness returned by
  `POST /api/or/quiz/{section_id}/attempt`. Answer keys never reach the
  browser, so the UI cannot leak them.
- The module reading pane offers a language switcher only when a probe of
  `GET /api/or/learning/modules/{slug}?lang=<code>` answers 200 for a
  candidate language ("when 200 else hide"). Today no candidate answers 200,
  so the switcher stays hidden until localization ships backend-side.

### Browser terminal

`/terminal` attaches xterm.js to the gateway WebSocket at
`/terminal/{instance_id}?token=...` (binary frames carry keystrokes and PTY
output; text frames are control JSON such as resize, plus the initial
`{"type":"session"}` handshake used for `?resume=` reconnects).

Token reality check (grep before you trust this): the gateway verifies
short-lived `lab-v1` tokens (`apps/lab-gateway/src/openrange/gateway/tokens.py`),
but the FastAPI side has **no minting endpoint yet** — there is no
`POST /api/labs/{id}/terminal-token` route in `apps/api`, and the tokens
module docstring says minting lands in a later branch. Until that endpoint
ships, the page therefore stays gated behind selecting a READY lab from your
own instance list, and Connect reports precisely that the token endpoint is
missing instead of pretending to attach. When the endpoint exists, the same
client connects for real: it expects `{token}` from
`POST /api/or/labs/{id}/terminal-token` and opens
`${NEXT_PUBLIC_GATEWAY_WS_URL:-ws://localhost:8772}/terminal/{id}?token=...`.

### Styling and accessibility

- `packages/ui` owns tokens (`tokens.css`: near-black surfaces, single lime
  accent, danger red, warning amber) and component classes
  (`components.css`). Tailwind maps those variables into utilities via
  `@theme inline` in `app/globals.css`.
- Dark-first by design; there is no light theme to drift against.
- Keyboard support: skip link as first tab stop, visible focus rings
  everywhere, native `<dialog>` for modals (focus trap + Escape for free),
  WAI-ARIA tabs pattern in the Tabs primitive, reduced-motion-safe animations.
- The top navigation marks the active route with `aria-current="page"`;
  below the `md` breakpoint it collapses into a disclosure menu button.
- Playwright runs axe on `/`, `/catalog`, `/login`, `/learn`, and
  `/challenges` at 320 px and 1280 px, plus a keyboard-only journey test and
  mocked-API journeys for enroll/module/quiz and challenge flag submission.

## Local development

```bash
pnpm install
pnpm --filter web dev   # http://localhost:3100
```

Environment variables (see `.env.example` at the repo root):

- `ORIGIN_API_URL`: where FastAPI listens (default `http://localhost:8700`).
- `OPENRANGE_CONTENT_DIR`: override for the content bundle directory.
- `NEXT_PUBLIC_GATEWAY_WS_URL`: gateway WebSocket base for the browser
  terminal (default `ws://localhost:8772`); production Caddy exposes it under
  `/gateway/*`, so set `wss://<host>/gateway`.

## Commands

```bash
pnpm exec turbo run lint typecheck build --filter=web...
pnpm --filter web test:e2e   # starts next dev on :3210 automatically
```
