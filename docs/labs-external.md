# External OSS lab wrappers

Four rooms wrap famous open-source vulnerable applications so learners
get them in one place. The platform never copies or redistributes these
applications. Each room points the harness at the official container
image published by the upstream project, pinned by digest, and runs it
unmodified on the isolated room network. Everything we author (lesson
text, solver, answer validation) lives in our repository under our own
license.

## How a wrapper room differs from a built room

- `target.external_image` names the official upstream ref with an
  immutable `@sha256:` digest. The harness pulls that image instead of
  building anything.
- Upstream apps cannot consume injected per-session flags, so wrapper
  rooms set `flag_delivery: static`. Answers are fixed public constants,
  declared on each task's exact/normalized validator, and documented in
  the lesson text. The harness validates solver captures against those
  declared values; the platform grades learner submissions through the
  same validators.
- Some upstream images need companion services. `target.sidecars` runs
  extra official containers from the upstream deployment topology next
  to the target.

## The integrations

Pulled and verified on 2026-08-24; digests are what the rooms pin.

### juice-shop-tour

- Upstream: OWASP Juice Shop, https://github.com/juice-shop/juice-shop
- Image: bkimminich/juice-shop, digest sha256:73c53fbf442e8337b3ea3d98c7e8550308854701ebdfce4cc39768f36b75430e
- Upstream license: MIT
- Objective: reach the hidden /score-board page; fixed answer is the
  route path itself.
- Registry note: ghcr.io/juice-shop/juice-shop denied anonymous pulls at
  verification time, so the room pins the Docker Hub image the official
  README publishes (`docker pull bkimminich/juice-shop`).

### dvwa-cmdi

- Upstream: Damn Vulnerable Web Application, https://github.com/digininja/DVWA
- Image: ghcr.io/digininja/dvwa, digest sha256:38d8f4894c9ec064e42e43eaf423d55ad09a7f59cada82414217113db6129c3e
- Companion: library/mariadb:10, digest sha256:8020e05c4c498d06c87f0a1db010eb79bd6f8fb30e9b763d4690c34ce1e61008
- Upstream license: GPL-3.0
- Objective: complete the Command Injection level at low security;
  fixed answer is the word the intended payload echoes back.
- Topology note: DVWA requires MariaDB per its own compose.yml
  (DB_SERVER=db). The sidecar gets the bounded capability set because
  its entrypoint drops privileges to the mysql user.

### webgoat-first-flag

- Upstream: OWASP WebGoat, https://github.com/WebGoat/WebGoat
- Image: webgoat/webgoat:latest (v2025.3), digest sha256:3101bd9e7bcfe122d7ef91e690ef3720de36cc4e86b3d06763a1ddf2e2751a4b
- Upstream license: GPL-2.0-or-later (SPDX headers in upstream source)
- Objective: register a learner account and complete the HTTP Basics
  assignment; fixed answer is the assignment JSON's completion marker,
  lessonCompleted: true.

### wrongsecrets-one

- Upstream: OWASP WrongSecrets, https://github.com/OWASP/wrongsecrets
- Image: jeroenwillemsen/wrongsecrets:latest-no-vault, digest sha256:7d80321e40dd6ab41600a20a086bd63406d553fc833e4e7cf68fd07b476ec730
- Upstream license: AGPL-3.0
- Objective: solve challenge 1 locally without Kubernetes or Vault;
  fixed answer is the hardcoded constant the upstream source publishes
  (WrongSecretsConstants.java).
- Registry note: there is no ghcr.io/owasp/wrongsecrets image; the
  Docker Hub repository above is what upstream documents for Docker.

## Trademarks

Juice Shop, DVWA, WebGoat, and WrongSecrets are projects of their
respective maintainers and OWASP project names belong to OWASP. This
platform is not affiliated with or endorsed by them. Room titles are
original and only reference the wrapped software factually.

## Resource notes

Upstream images carry their own runtimes (Node, JVM) so external targets
run with a 2 GB memory budget instead of the built-room default. Total
pull size for all four integrations is roughly 3.9 GB.

## Removing an integration

Wrapper rooms are additive and self-contained. To drop one:

1. Delete its directory under content/rooms/.
2. Remove any references from paths or modules that listed it.
3. Nothing else needs cleanup; the SDK fields are generic and used by no
   other bundle. Images already pulled stay in the local Docker cache
   until pruned manually.
