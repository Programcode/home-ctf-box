# Security policy

## Supported versions

The project has not shipped a public release yet. Security fixes land on
`main` and are picked up by anyone running a checkout. Once releases
start, the latest minor line is supported and older lines get fixes at
maintainer discretion.

## Reporting a vulnerability

Email the maintainers or open a GitHub security advisory on this
repository. Do not open a public issue for something exploitable.

Include what you found, how you confirmed it, and what a fix would need
to change. You will get an acknowledgment within 3 days and a triage
decision within 10 days.

## Scope

In scope:

- the control plane (API, web, worker, gateway, runner agent);
- the content SDK and any code path that renders contributor content;
- the packaged Compose/Helm deployments;
- anything that lets a lab container reach the host, control plane, or
  another tenant's lab.

Out of scope:

- the deliberately vulnerable room targets themselves. Exploiting them
  is the entire point of the platform. Findings that only affect a room
  container from inside its own lab network are not vulnerabilities.
- reports from automated scanners without a working proof.

## Rules of engagement

Test only against your own installation. Never attack infrastructure you
do not own, and never expose intentionally vulnerable targets to networks
you do not control.

## Disclosure

We coordinate disclosure: fix first, advisory second, credit to the
reporter unless they prefer anonymity.
