# Lab gateway API contract

The lab gateway (`apps/lab-gateway`) is the only component that exposes lab
instances. Learners never get host ports or direct network routes; every
request into a lab flows through this authenticated proxy, keyed by an
opaque instance id and a short-lived token minted by the API.

Out of scope for this document (later phases): WireGuard configuration
flow and noVNC/Guacamole desktops.

## Authentication: `lab-v1` tokens

The gateway validates short-lived, lab-scoped tokens. The API mints them
(the minting endpoint lands in the API in a later branch); the shared
secret comes from the `OPENRANGE_GATEWAY_SECRET` environment variable,
set identically on the API and the gateway.

### Format

```
lab-v1.<base64url(payload)>.<base64url(hmac)>
```

- `<payload>` is compact JSON with sorted keys (`separators=(",", ":")`,
  `sort_keys=True`), base64url-encoded without padding.
- `<hmac>` is HMAC-SHA256 over the ASCII bytes of
  `lab-v1.<base64url(payload)>` (scheme prefix included), keyed with
  `OPENRANGE_GATEWAY_SECRET`, base64url-encoded without padding.
- Verification recomputes the HMAC and compares with
  `hmac.compare_digest` (constant time). Expired tokens are rejected.

### Payload fields

| Field      | Type        | Required | Meaning                                              |
| ---------- | ----------- | -------- | ---------------------------------------------------- |
| `sub`      | string      | yes      | User id the token was issued to                      |
| `lab`      | string      | yes      | Instance id the token is scoped to                   |
| `exp`      | int         | yes      | Expiry as unix seconds; rejected once `now >= exp`   |
| `ports`    | list[int]   | yes      | Allowlist of target ports reachable via `/proxy`     |
| `ssh`      | bool        | yes      | Whether `/terminal` may be used (default `false`)    |
| `ssh_user` | string      | no       | Overrides the gateway's default SSH username         |
| `ssh_pass` | string      | no       | Overrides the gateway's default SSH password         |
| _(other)_  | _(ignored)_ | no       | Unknown fields are ignored for forward compatibility |

Default TTL is 300 seconds when minting (`ttl_seconds`). Tokens are
bearer credentials: they grant exactly one lab, at most its listed ports,
for at most a few minutes.

### Presenting tokens

- HTTP proxy: `Authorization: Bearer <token>`, or `?token=` query param.
- Terminal WebSocket: `?token=` query param (browsers cannot set headers
  on WebSocket connects).

The gateway strips `token` (and `resume`) from any query string it
forwards upstream, and never forwards `Authorization` or `Cookie`
headers to targets.

## Endpoints

### ANY /proxy/{instance_id}/{port}/{path}

Streaming HTTP reverse proxy to `http://<runner-resolved host>:<port>/<path>`.

Status mapping:

| Condition                             | Result             |
| ------------------------------------- | ------------------ |
| Missing/invalid/expired token         | `401` problem+json |
| Token `lab` ≠ `instance_id`           | `403`              |
| `port` not in token `ports` allowlist | `403`              |
| Malformed instance id                 | `400`              |
| Runner reports unknown instance       | `404`              |
| Runner unreachable / 5xx              | `502`              |
| Otherwise                             | Upstream status    |

Behavior:

1. Resolves `instance_id` by asking the runner:
   `GET {RUNNER_URL}/labs/{instance_id}/address`, authenticated as a
   service per docs/contracts/runner-api.md (timestamp + HMAC headers,
   signed with `RUNNER_SERVICE_TOKEN`). Response:
   `{"host": "<address>"}`.
2. Streams request body and response body in both directions; hop-by-hop
   headers are stripped on both legs.
3. Injects `X-Forwarded-For` (appending the client IP to any existing
   chain), `X-Forwarded-Proto`, `X-Forwarded-Host`, `X-Forwarded-Port`.

Instance ids must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`. Upstream
targets are plain HTTP; TLS to targets is not part of the core scope.

### WS /terminal/{instance_id}?token=...[&resume=<session-id>]

WebSocket-to-SSH bridge into port `OPENRANGE_GATEWAY_SSH_PORT` (default 22) on the runner-resolved host. Requires `ssh: true` on the token.
SSH username/password come from the token's optional `ssh_user`/`ssh_pass`
claims, falling back to `OPENRANGE_GATEWAY_SSH_USER` /
`OPENRANGE_GATEWAY_SSH_PASSWORD`.

Protocol after accept:

1. Gateway sends `{"type": "session", "session_id": "..."}` as text.
2. Binary frames pass through verbatim to/from the SSH PTY
   (`xterm-256color`).
3. Text frames are control JSON:
   - `{"type": "resize", "cols": <int>, "rows": <int>}` resizes the PTY
     (values clamped to 1..1000; invalid frames are ignored).
   - `{"type": "close"}` ends the session cleanly.

Close codes:

| Code | Meaning                                                                                     |
| ---- | ------------------------------------------------------------------------------------------- |
| 1000 | Clean close requested, or the SSH session ended                                             |
| 1008 | Policy violation: bad/expired token, wrong lab, `ssh:false`, resume missing/expired/foreign |
| 1011 | Upstream failure (runner unavailable, SSH connect failed)                                   |
| 1013 | Per-lab concurrency cap reached (`OPENRANGE_GATEWAY_MAX_SESSIONS`, default 4)               |

Reconnect grace: if the socket drops, the SSH channel stays alive for
`OPENRANGE_GATEWAY_RESUME_TTL_SECONDS` (default 60). Reconnecting with
`?resume=<session-id>` reattaches to the same channel (same
`session_id`) and drains output buffered during the gap. Output buffered
while detached is capped; when full, the oldest chunks are dropped.
Opening a brand-new session while the cap is held entirely by detached
sessions evicts the oldest detached session first — a browser reopening
beats a stale grace window. Resume is bound to both the lab and the
token subject; sessions are single-attach.

Known limitation: session state is in-memory only. Single-replica
deployments today; horizontal scale later needs sticky routing or shared
state.

### GET /healthz

```json
{ "status": "ok", "runner": true, "secret": true }
```

`status` is `"degraded"` (still HTTP 200) when the runner is unreachable
or the secret is unset.

## Observability

One JSON object per line on stdout: `ts`, `level`, `logger`, `msg`,
plus `path`, `method`, `status`, `duration_ms` and `request_id` per
request. Every response carries `X-Request-ID`; send it back when
reporting issues.

## Threat notes: what the gateway must never do

- Never log authorization headers, token bodies, query strings, or SSH
  credentials. Request logs carry paths only; forwarded requests lose
  `Authorization`, `Cookie`, and `?token=` before leaving the gateway.
- Never route a request whose token does not bind that exact instance id
  and port; cross-lab access fails closed with 403.
- Never accept an expired or badly-signed token; signature comparison is
  constant-time so timing cannot leak signature bytes.
- Never touch the Docker socket or the host network from the gateway
  process; the runner is the only Docker-capable component.
- Never forward platform identity (cookies/bearer) into lab networks;
  labs see only the injected X-Forwarded-* headers.

## Deployment (compose)

See infra/compose/gateway.yml. It declares compose project name
`openrange`, matching runner.yml, so both stacks share one default
network and the gateway reaches the runner at `http://lab-runner:8771`.
The image installs the package from the mounted workspace and runs the
`openrange-gateway` entry point; the listen port stays bound to
127.0.0.1 on the host (a tunnel/edge proxy terminates public traffic in
front of it).

Environment variables:

| Variable                               | Default                 | Purpose                               |
| -------------------------------------- | ----------------------- | ------------------------------------- |
| `OPENRANGE_GATEWAY_SECRET`             | _(required)_            | Shared HMAC secret, same value as API |
| `RUNNER_URL`                           | `http://127.0.0.1:8771` | Runner base URL                       |
| `RUNNER_SERVICE_TOKEN`                 | empty                   | Service token for runner HMAC auth    |
| `OPENRANGE_GATEWAY_MAX_SESSIONS`       | `4`                     | Concurrent terminal sessions per lab  |
| `OPENRANGE_GATEWAY_RESUME_TTL_SECONDS` | `60`                    | Terminal reconnect grace window       |
| `OPENRANGE_GATEWAY_SSH_PORT`           | `22`                    | SSH port on the target                |
| `OPENRANGE_GATEWAY_SSH_USER`           | `lab`                   | Fallback SSH username                 |
| `OPENRANGE_GATEWAY_SSH_PASSWORD`       | empty                   | Fallback SSH password                 |
| `OPENRANGE_GATEWAY_HOST`               | `127.0.0.1`             | Bind address                          |
| `OPENRANGE_GATEWAY_PORT`               | `8772`                  | Bind port                             |

Lab containers live on internal `lab-{instance_id}` networks (default-deny
egress). Reaching them requires attaching the gateway container to those
networks at instance creation time; wiring that attachment through the
runner is planned alongside VPN issuance in a later branch of Phase 7.
