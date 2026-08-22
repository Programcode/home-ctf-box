# home_ctf_box

A self-hosted capture-the-flag lab: one scoreboard platform plus three deliberately
vulnerable web services, all in Docker. Built for a Raspberry Pi 5 on your home LAN,
attackable from your MacBook browser or terminal. Images are multi-arch, so the same
stack also builds on any x86 box (it was developed and tested on a VPS).

## Rooms

| # | Room | Port | Points | Technique |
|---|------|------|--------|-----------|
| 1 | Busted Login | 8081 | 100 | SQL injection login bypass |
| 2 | Nosy Files | 8082 | 150 | Path traversal |
| 3 | Ping of Doom | 8083 | 200 | Shell command injection |
| 4 | SSTI Greeting | 8084 | 150 | Jinja server-side template injection |
| 5 | Token Forger | 8085 | 250 | JWT alg:none forgery |
| 6 | IDOR Invoices | 8086 | 125 | Missing ownership check |
| 7 | Open Panels | 8087 | 50 | Exposed debug panel |
| 8 | Cookie Shapeshifter | 8088 | 100 | Unsigned base64 cookie forgery |
| 9 | Regex Doom | 8089 | 125 | Regex injection |
| 10 | Mass Assign | 8090 | 150 | Blind mass assignment |
| 11 | XXE Importer | 8091 | 225 | External entity injection |
| 12 | Pickle Jar | 8092 | 275 | Unsafe deserialization RCE |
| 13 | Trusted Proxy | 8093 | 75 | X-Forwarded-For spoofing |
| 14 | Wrong Method | 8094 | 75 | HTTP verb tampering |
| 15 | Open Closet | 8095 | 50 | Directory listing exposure |
| 16 | Predictable Reset | 8096 | 175 | Time-derived reset tokens |
| 17 | Double Trouble | 8097 | 150 | HTTP parameter pollution |
| 18 | Fetch Boy | 8098 | 200 | SSRF |
| 19 | Union Vault | 8099 | 225 | UNION-based SQL injection |
| 20 | Brace Yourself | 8100 | 125 | Python format string injection |

Total: 2975 points. Exploit each service, grab its `FLAG{...}` token, submit it on the platform scoreboard.

## Safety

- Every published port binds to `127.0.0.1` by default (`CTF_BIND`).
- These services are vulnerable **on purpose**. Never expose them to the internet,
  never port-forward them on your router, never run them on a shared host.
- To play from another device on your LAN, set `CTF_BIND=0.0.0.0` in `.env`
  (or export it) only on a trusted home network.

## Quickstart

```sh
docker compose up -d --build
```

Platform: http://localhost:8000 (override with `PLATFORM_PORT`, e.g. when 8000 is busy).

Rooms: `http://localhost:8081`, `:8082`, `:8083`.

Register a player on the platform, then solve rooms manually or run the demo bot:

```sh
PLATFORM_PORT=8000 ./scripts/demo-solve.sh
```

The script registers a throwaway player, exploits all twenty rooms, submits the flags,
and exits non-zero unless the scoreboard confirms 2975 points.

## Deploying to the Pi

```sh
git clone <this repo> && cd home-ctf-box
CTF_BIND=0.0.0.0 docker compose up -d --build
```

Then browse to `http://<pi-ip>:8000` from the MacBook.

## Reset scores

```sh
docker compose down -v   # wipes the ctf-db volume
```

## Adding a room

1. Copy a folder under `rooms/`, write your Flask app, bake its flag via build arg or env.
2. Add the service to `docker-compose.yml` (publish a new host port, loopback-bound).
3. Register its flag + points in `platform/app.py` (`FLAGS` and `CHALLENGES`).
4. Extend `scripts/demo-solve.sh` with an automated exploit if you want CI-style proof.

## Roadmap ideas

- More rooms: SSTI, unsigned JWT `alg:none`, unsafe file upload, IDOR.
- Session timer + per-room first-blood bonus.
- Room difficulty labels and tiered hints.
