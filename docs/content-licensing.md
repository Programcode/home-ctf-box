# Content licensing

Two licenses cover this repository.

- Code, configuration, infrastructure, and tooling: AGPL-3.0-or-later
  (`LICENSE`).
- Training content: prose, scenarios, lesson text, diagrams, room
  bundles, and other creative material under `content/`:
  CC BY-SA 4.0 (`licenses/CC-BY-SA-4.0.txt`). Each bundle also states
  its license in `room.yaml` / `module.yaml` so exports stay correct
  when they travel without the repository.

## What this means in practice

- Forks and self-hosted instances must publish their source changes to
  the platform code under AGPL-3.0 when they offer it as a network
  service.
- Content can be remixed and republished with attribution and a
  share-alike license.
- Contributions assert the contributor has the right to license the
  material this way. Do not submit content copied from commercial
  training platforms, books, or courses, even paraphrased closely
  enough to substitute for them.

## Third-party references

Rooms may cite public standards, RFCs, vendor documentation, or research
papers. Citations name the source; we do not reproduce substantial
portions of third-party text. Screenshots of third-party products appear
only when their license permits it, otherwise rooms use original mockups.

## Room names and trademarks

Room titles are original. They must not use or imitate trademarks of
Hack The Box, TryHackMe, or any other training vendor. Before a public
release, run a search review on new product-level names (ADR 0001).
