# Dependency Confusion Lab

Every package manager resolves versions by ranking. When a company
resolves installs from a mixed feed that considers both a private
registry and a public one, the highest version wins, and nothing in
that comparison knows which source is authoritative. If an internal
package called company-utils exists privately at 1.0.0 and nobody has
registered that name on the public registry, an outsider can publish
company-utils 2.0.0 publicly and every build that trusts the feed will
prefer it. This is dependency confusion, and it has paid attackers
six-figure bug bounties because one accepted publish turns into code
execution on thousands of build machines.

The install step is what makes publishes dangerous. Package managers
run lifecycle hooks like postinstall from package metadata as part of
installation. A hostile hook inherits the identity of the build runner,
which usually holds cloud credentials, deploy keys, and network reach
into staging. The lab in this room models exactly that: its installer
accepts a hook with each publish, and the canary policy requires every
hook to ping a known beacon URL so executions are attributable. In this
simulation your hook is recorded as a string and the lab writes the
canary marker itself rather than executing anything, but the resolution
logic, version ranking, and token checks behave like the real thing.

Publishing requires authority, and the second half of the incident is
how the attacker gets it. The org's nightly job archives raw CI
workspaces to an evidence bucket, and those snapshots include whatever
config files were lying around, npmrc files among them. An npmrc with a
publish-scoped auth token is equivalent to handing over the maintainer
key. Credential hygiene in CI means short-lived tokens, least-scope
grants, and archives that scrub secrets before storage.

In the room you will inspect the public registry copy of company-utils
to learn its version landscape, pull the archived artifact to recover
the maintainer token, submit a publish claim for 2.0.0 carrying a
compliant hook, and then hit the takeover checker, which only confirms
a takeover when the installer actually resolved your version.

## Simulation disclosure

The registry, resolver, installer, and canary all live inside one Flask
process on the room target. No external registry, package, or network
is contacted. Submitted install scripts are never executed; the app
parses them, stores the string, and writes the canary file itself. All
names, tokens, and artifacts are synthetic.

## What you will practice

- Reasoning about version resolution across mixed public and private feeds.
- Recovering credentials from CI artifact archives.
- Driving a publish API end to end and verifying impact through a canary signal.

## Scope

Only the lab at `http://target:8000` is in scope. Nothing outside your
lab instance is a target.
