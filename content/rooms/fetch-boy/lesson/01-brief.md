# Fetch Boy

Peeker renders plain-text previews of any URL you give it. The fetch
happens on the server, which means the preview code sees networks you
do not, including the container's own loopback interface. An admin
service is listening there on port 9001. You will borrow the preview's
network position, make it request the admin page for you, and read what
it brings back.

## What you will practice

- Tracing where a user-supplied URL is actually fetched from.
- Using a server-side request to reach a loopback-only service.
- Confirming the exposure by capturing the per-session flag.

## Scope

Only the preview service at `http://target:8000` is in scope, plus its
own loopback interfaces as reached through it. Nothing outside your lab
instance is a target.
