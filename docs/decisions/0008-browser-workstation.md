# ADR 0008: Browser workstation

Status: accepted

## Context

Learners should not need local tooling to attack rooms. The browser must
provide a terminal for CLI work and a desktop for GUI-designated
content, without opening per-room host ports.

## Decision

- Terminal: each attacker workstation container runs `ttyd` serving an
  xterm.js-compatible WebSocket. The lab gateway terminates user auth and
  proxies the stream; the web app embeds xterm.js.
- Desktop: GUI rooms run Xvfb plus a lightweight window manager with
  x11vnc, bridged by noVNC/websockify, again proxied through the gateway.
- The workstation image is versioned, scanned, and published with a tool
  manifest. A persistent (opt-in) workstation reuses the same image with
  a durable volume; the default is ephemeral.
- SSH over VPN remains available for users who prefer real clients;
  the browser path is the zero-setup default.

## Consequences

- No SSH key management in the browser path; short-lived gateway tokens
  gate access instead.
- Clipboard flows through the browser with copy controls so secrets do
  not leak to shared machines accidentally.
