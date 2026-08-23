# Content catalog status

Tracks room, module, path production against the launch targets:
100 rooms (20/30/30/15/5 across beginner/easy/medium/hard/insane),
20 paths, 60 modules, 300+ sections, 1000+ questions/tasks,
100 cheat sheets, 20 capstones.

A room counts only after it passes: schema lint, solver proof on a clean
build, reset/idempotency test, instructional review, safety review, and
accessibility review. This ledger is the source of truth for what has
actually passed; `in-review` items are listed but not counted.

## Rooms

Migrated from legacy: all 20 bundles exist and pass the automated gate
(schema lint + clean-build solver + reset proof + per-session flag
match). Instructional review happens through the review workflow before
they count as published.

| Slug                | Track | Difficulty | Type          | Status          |
| ------------------- | ----- | ---------- | ------------- | --------------- |
| busted-login        | A     | beginner   | guided web    | bundle-verified |
| nosy-files          | A     | beginner   | guided web    | bundle-verified |
| ping-of-doom        | A     | easy       | challenge web | bundle-verified |
| ssti-greeting       | A     | easy       | challenge web | bundle-verified |
| token-forger        | A     | medium     | challenge web | bundle-verified |
| idor-invoices       | A     | beginner   | guided web    | bundle-verified |
| open-panels         | A     | beginner   | guided web    | bundle-verified |
| cookie-shapeshifter | A     | beginner   | guided web    | bundle-verified |
| regex-doom          | A     | easy       | challenge web | bundle-verified |
| mass-assign         | A     | easy       | challenge web | bundle-verified |
| xxe-importer        | A     | medium     | challenge web | bundle-verified |
| pickle-jar          | A     | medium     | challenge web | bundle-verified |
| trusted-proxy       | A     | beginner   | guided web    | bundle-verified |
| wrong-method        | A     | beginner   | guided web    | bundle-verified |
| open-closet         | A     | beginner   | guided web    | bundle-verified |
| predictable-reset   | A     | easy       | challenge web | bundle-verified |
| double-trouble      | A     | easy       | challenge web | bundle-verified |
| fetch-boy           | A     | easy       | challenge web | bundle-verified |
| union-vault         | A     | easy       | challenge web | bundle-verified |
| brace-yourself      | A     | easy       | challenge web | bundle-verified |

New rooms 021–100: `not-started` (authored in batches per track B–E).

## Paths and modules

0 of 20 paths, 0 of 60 modules authored. Batch plan follows plan
section 9 (three-room vertical slice first, then batches of ten rooms
and six modules).
