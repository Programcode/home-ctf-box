# SSTI Greeting

Greeting Card Studio is a small card shop on your lab network. The
renderer builds each greeting by pasting the recipient's name into a
Jinja template string, so a name that looks like template syntax gets
compiled and executed on the server. You will prove that evaluation,
climb the standard Jinja object chain to Python's os module, and read
the environment variable holding the room flag.

## What you will practice

- Telling echoed input from evaluated template code with an arithmetic
  payload.
- Bridging from a template global such as `cycler` to its module
  namespace, then to the `os` module it imports.
- Running a command through the injected expression and capturing the
  per-session flag from the rendered page.

## Scope

Only the card studio at `http://target:8000` is in scope. Nothing
outside your lab instance is a target.
