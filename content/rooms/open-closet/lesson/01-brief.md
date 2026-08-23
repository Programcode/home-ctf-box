# Open Closet

Nimbus CRM's ops host writes a database dump every night and serves the
whole backup folder over plain HTTP. Nobody put an index file in the
directory, so the server happily lists its contents to anyone who asks.
You will walk the listing, pick the right artifact, and read a secret
the export embedded in plain SQL.

## What you will practice

- Spotting sensitive files through an unauthenticated directory listing.
- Reading file names and dates to decide which artifact holds live data.
- Confirming the exposure by capturing the per-session flag.

## Scope

Only the host at `http://target:8000` is in scope. Nothing outside your
lab instance is a target.
