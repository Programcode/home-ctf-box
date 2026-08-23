# Runner agent API contract

The control plane never touches the Docker socket. Every lab lifecycle
operation goes through this authenticated, narrow HTTP API served by the
runner (`apps/lab-runner`), which is the only component allowed to talk
to Docker.

## Authentication

Every request carries:

```
X-Runner-Timestamp: <unix seconds>
X-Runner-Signature: hex(hmac_sha256(RUNNER_API_TOKEN, f"{timestamp}:{body}"))
```

The timestamp must be within 300 seconds of server time (replay
protection). Constant-time comparison everywhere.

## Endpoints

### POST /v1/instances

Create one isolated instance.

```json
{
  "instance_id": "uuid",
  "image": "openrange/test-busted-login:1.0.0",
  "build_context_tar_gz_base64": "...", // optional; when present runner builds instead of pulling
  "env": { "ROOM_FLAG": "FLAG{...}" },
  "cpus": 1.5,
  "mem_mb": 512,
  "pids_limit": 256,
  "ports": [8000],
  "ttl_seconds": 5400,
  "labels": { "room": "busted-login" }
}
```

Behavior:

1. Creates bridge network `lab-{instance_id}` with `internal=true`
   (default-deny egress; nothing leaves the lab network).
2. Runs the container with: non-root where the image supports it,
   `no-new-privileges`, all capabilities dropped, cpu/mem/pids caps,
   `openrange.*` labels, auto-remove disabled.
3. Waits until the declared healthcheck passes or times out (30s).
4. Responds `201`:

```json
{
  "state": "ready",
  "network": "lab-{id}",
  "targets": [{ "name": "target", "url": "tcp://lab-{id}:8000" }]
}
```

Failures return problem details; any partially created resources are
cleaned before responding.

### POST /v1/instances/{id}/restart

Stop and start the same container in place (reset semantics). Returns
`{"state": "ready"}` after the healthcheck passes again.

### DELETE /v1/instances/{id}

Stops the container, removes it, removes its network. Idempotent:
returns `204` even if already gone.

### GET /v1/instances/{id}

Returns current observed state: `ready | starting | stopped | missing`,
started_at, labels.

### POST /v1/reconcile

```json
{ "known_instance_ids": ["uuid", "..."] }
```

Removes every labeled container/network whose instance id is not in the
known set (orphans from crashes). Returns what was removed so the caller
can audit:

```json
{ "removed_containers": ["name"], "removed_networks": ["name"] }
```

### GET /healthz

Liveness only: `{"status": "ok", "docker": true|false}`.

## Labels

Everything the runner creates carries:

```
openrange.managed=true
openrange.instance.id={uuid}
openrange.created-at={iso8601}
```

Reconciliation only ever touches objects carrying `openrange.managed`.
