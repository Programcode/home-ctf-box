# kubernetes-paper-walls

Medium challenge closing track E batch 2. A simulated Kubernetes
apiserver serves namespace prod as JSON with live RBAC checks over
bearer tokens. Starting as metrics-agent (token published on the
console page), learners read their own effective rules, discover
deploy-bot holds binding-admin rights, steal its mounted token from
the secrets API, then use it to create a rolebinding granting
prod-admin (pods/exec) to themselves. Exec into flagship-0 via POST
and cat /var/run/secrets/flag.txt for the flag. Points: 275.

- `room.yaml` declares objectives, scope, locked profile, one task
  with tiered hints and a step-by-step solution.
- `lesson/` teaches the RBAC graph walk, token-theft mechanics, and
  full simulation disclosure including the in-memory binding state.
- `target/` builds the Flask apiserver on port 8000; permissions
  recompute per request, created bindings reset on restart.
- `solver/solver.py` derives the whole chain (target SA, secret,
  role, pod) from API responses using httpx and base64 only.

Verify locally with `cyberrange solve content/rooms/kubernetes-paper-walls`.
