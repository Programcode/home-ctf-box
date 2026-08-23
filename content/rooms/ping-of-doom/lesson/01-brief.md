# Ping of Doom

NetCheck 3000 is a diagnostics page on your lab network that pings
whatever host an employee types into the form. Behind the page, the
handler glues the host value into a shell command string, so shell
metacharacters in the field reach `/bin/sh` untouched. You will confirm
the flaw from the response output, run a command of your own through
it, and read the environment variable that holds the room flag.

## What you will practice

- Recognizing shell command construction from untrusted web input.
- Using a metacharacter to append a second command to the ping call.
- Reading injected command output from the response and capturing the
  per-session flag.

## Scope

Only the diagnostics service at `http://target:8000` is in scope.
Nothing outside your lab instance is a target.
