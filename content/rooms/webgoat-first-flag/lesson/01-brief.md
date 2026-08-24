# Brief: your first WebGoat assignment

This room wraps the real OWASP WebGoat, running exactly as its
maintainers publish it. You get the goat on port 8080 of the `target`
host under the `/WebGoat` path. Your job is to become a registered
learner and finish one assignment for real.

## Why this matters

WebGoat is a structured curriculum: every lesson pairs theory with a live
assignment endpoint that grades what you send. The HTTP Basics lesson is
the front door. Completing it proves you can drive an authenticated,
session-bound flow against a Spring application, which is the base skill
every later lesson builds on.

## Your path

1. Open `http://target/WebGoat/registration`.
2. Create your own account. Password rules apply: 6 to 10 characters,
   and confirm it. Tick the agreement checkbox.
3. Registration signs you in automatically.
4. Find the HTTP Basics lesson, read both theory pages, then complete
   the first assignment by sending your name.
5. Watch the response JSON. It reports what the server did with your
   value and whether the assignment counts as completed.

## Answer convention

WebGoat cannot host platform-injected flags, so this room validates a
fixed public artifact: the completion marker from the assignment's JSON
response, written as key: value.

Credit: OWASP WebGoat is an official OWASP project under GPL-2.0-or-later,
published by its maintainers as a container image. This room references
that image and adds original lesson text around it.
