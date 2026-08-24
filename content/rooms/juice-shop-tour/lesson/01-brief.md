# Brief: find the hidden Score Board

This room wraps the real OWASP Juice Shop, running exactly as its
maintainers publish it. Nothing was added to the app. You get the
storefront on port 3000 of the `target` host, and one job: reach the
score board page that the interface intentionally hides.

## Why this matters

Modern storefronts are single-page applications. The navigation bar shows
you what the designers chose to show, but every route the app can render
is present in the JavaScript it ships to your browser. Learning to read
that code is a recon superpower that transfers to every SPA you will ever
test.

## Your path

1. Open `http://target:3000` in the workstation browser or with curl.
2. Look at the page source and find the main JavaScript bundle.
3. Download the bundle and search it for route-like strings containing
   "board".
4. Open the route you found. The Score Board should render.
5. Submit the route path as your answer.

## Answer convention

Juice Shop cannot host platform-injected flags, so this room validates a
fixed public artifact instead: the hidden route's path. The answer is the
same for every learner and every session.

Credit: OWASP Juice Shop is an official OWASP project, MIT licensed,
published by its maintainers as a container image. This room only
references that image and adds original lesson text around it.
