# Open Panels

PanelOps is an internal status board on your lab network. It shipped
with a leftover diagnostics page that prints runtime details and the
process environment to anyone who asks, and nothing on the dashboard
links to it. You will pick up the public hints that reveal the hidden
path, open the panel yourself, and read what it leaks.

## What you will practice

- Checking robots.txt and page source for paths the app never links.
- Enumerating undocumented routes on a web service.
- Recognizing information disclosure in diagnostic output and capturing
  the per-session flag from it.

## Scope

Only the status board at `http://target:8000` is in scope. Nothing
outside your lab instance is a target.
