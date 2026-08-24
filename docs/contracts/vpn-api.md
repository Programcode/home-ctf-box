# VPN API contract

Phase 7 remainder: WireGuard device management on the API
(`apps/api/src/openrange/api/vpn/`) and the browser desktop bridge plus
heartbeat client on the lab gateway (`apps/lab-gateway`).

Scope rules, in one place:

- A device is a WireGuard keypair owned by one user. The private key is
  generated client-side and NEVER sent to the server; the API stores the
  public key only. The rendered config has no `PrivateKey =` line; the
  client pastes their own.
- Rendered configs route ONLY the lab subnets from
  `OPENRANGE_VPN_ALLOWED_SUBNETS` into the tunnel. `0.0.0.0/0` (and
  `::/0`) are never emitted; internet traffic stays off the range.
- Revocation is permanent for that device: the lease address returns to
  the pool immediately, config downloads answer `410 Gone`, and
  heartbeats for a revoked public key answer `404` like any unknown key.

## Configuration

| Variable                          | Default         | Meaning                                              |
| --------------------------------- | --------------- | ---------------------------------------------------- |
| `OPENRANGE_VPN_POOL`              | `10.99.0.0/16`  | IPv4 pool addresses are allocated from, lowest-first |
| `OPENRANGE_VPN_SERVER_PUBLIC_KEY` | _(empty)_       | Server peer public key written into client configs   |
| `OPENRANGE_VPN_ENDPOINT`          | _(empty)_       | `host:port` clients dial (`Endpoint =` line)         |
| `OPENRANGE_VPN_ALLOWED_SUBNETS`   | `172.30.0.0/16` | Comma-separated lab subnets for `AllowedIPs`         |
| `OPENRANGE_GATEWAY_SECRET`        | _(empty)_       | Shared secret authenticating gateway heartbeats      |

Issuance endpoints answer `503 Service Unavailable` while the server
public key or endpoint is unset: a half-configured installation must not
hand out configs pointing at nothing.

## User endpoints (`vpn:issue` permission required)

All requests require an authenticated session (cookie + CSRF, or bearer
token). Devices belong to their owner; other users' devices answer `404`
as if they do not exist.

### POST /api/vpn/devices

Body: `{"name": "laptop", "public_key": "<canonical base64>"}`.

- `name` must match `^[a-zA-Z0-9_-]{1,32}$`.
- `public_key` must be canonical base64 of exactly 32 bytes (the
  WireGuard format, 44 chars ending in `=`).
- Duplicate public keys conflict globally: `409`.

Response `200`:

```json
{
  "device": {
    "id": "…uuid…",
    "name": "laptop",
    "public_key": "…",
    "address": "10.99.0.1",
    "created_at": "…iso…",
    "revoked_at": null,
    "last_seen_at": null
  },
  "config": "[Interface]\n…\n"
}
```

The server allocates the lowest free address from `OPENRANGE_VPN_POOL`
(`409 Conflict` with detail `vpn address pool exhausted` when none is
left) and renders the config text:

```ini
[Interface]
# Paste your own private key here; it is never sent to the server.
Address = 10.99.0.1/32

[Peer]
PublicKey = <OPENRANGE_VPN_SERVER_PUBLIC_KEY>
AllowedIPs = <comma-separated scoped subnets>
Endpoint = <OPENRANGE_VPN_ENDPOINT>
PersistentKeepalive = 25
```

### GET /api/vpn/devices

The caller's devices, newest first, each with its current lease address
(`null` once revoked).

### DELETE /api/vpn/devices/{device_id}

Revokes: sets `revoked_at`, deletes the lease (freeing the address),
returns `{"revoked": true}`. Repeat calls stay `200`; the first
revocation timestamp wins.

### GET /api/vpn/devices/{device_id}/config.qr?format=text

Returns the rendered config as `text/plain`. Only `format=text` exists:
the API deliberately does not render QR images server-side; clients
generate the QR from the returned text themselves. Any other `format`
answers `400`. Revoked devices answer `410 Gone`.

### GET /api/vpn/devices/{device_id}/status

Device view including `last_seen_at` (updated by gateway heartbeats,
below) and `revoked_at`.

## Admin endpoint

### GET /api/vpn/admin/devices

Requires `lab:manage-any`. Lists every device (newest first, limit 200)
with its owner in `user_id`.

## Gateway heartbeat

### POST /internal/vpn/heartbeat (API)

Called by the gateway when it observes a VPN device being live. The
WireGuard peer watcher lands in a later branch; the request contract and
client ship now.

Authentication mirrors the runner service scheme but keyed with
`OPENRANGE_GATEWAY_SECRET`:

- Headers: `X-Gateway-Timestamp` (unix seconds), `X-Gateway-Signature`
  = hex HMAC-SHA256 over `f"{timestamp}:{body}"`.
- Timestamps more than 300 seconds from now are rejected (`401`).

Body: `{"device_public_key": "<key>"}`. On success the API sets that
device's `last_seen_at` and answers `{"ok": true}`. Unknown or revoked
keys answer `404`; malformed bodies answer `400`.

Gateway side (`apps/lab-gateway`): `HttpVpnHeartbeatClient` reads
`OPENRANGE_API_URL` (default `http://127.0.0.1:8000`) and the shared
secret, exposes `await beat(device_public_key) -> bool`, and never
raises on transport errors (`False` instead).

## Desktop bridge (gateway)

### WS /desktop/{instance_id}?token=…[&port=…][&resume=…]

Bridges a browser WebSocket to the instance's RFB/VNC TCP port,
discovered through the runner exactly like `/terminal`. Protocol:

- On connect the gateway sends `{"type":"session","session_id":"…"}`.
- Binary frames pass verbatim in both directions. RFB negotiates its own
  resolution, so there is no resize control frame.
- Text control frames: `{"type":"close"}` ends the session cleanly.
- `?port=` overrides the target port (default `5900`); the token's
  `ports` allowlist must contain it, same rule as `/proxy`.
- `?resume=<session-id>` reattaches to a live stream within the grace
  TTL, mirroring terminal reconnect semantics.

Close codes: `1000` normal/end of stream, `1008` policy violation (bad
token, wrong lab, port not allowed, unknown/expired resume), `1011`
upstream failure, `1013` per-lab concurrency cap reached. The cap and
grace TTL reuse `OPENRANGE_GATEWAY_MAX_SESSIONS` and
`OPENRANGE_GATEWAY_RESUME_TTL_SECONDS`.
