# Content catalog status

Tracks room, module, and path production against the launch targets:
100 rooms (20/30/30/15/5 across beginner/easy/medium/hard/insane),
20 paths, 60 modules, 300+ sections, 1000+ questions/tasks,
100 cheat sheets, 20 capstones.

A room counts as authored once it passes the automated gate: schema lint
via `cyberrange lint`, clean-build intended-path solver, reset/idempotency
proof, per-session flag match. `.github/workflows/content.yml` runs this
gate on every content PR in four solver shards; the latest green run on
main is 32680139689 (2026-08-24). Instructional, safety, and accessibility
review happen through the studio review workflow before a room counts as
published. Regenerated from `content/rooms/*/room.yaml`,
`content/paths/*/path.yaml`, and `content/modules/*/module.yaml`
on 2026-08-24 at main commit `b4a9e8c`.

Track letters follow plan section 8: A web-foundations (rooms 001-025),
B linux-networking (026-045), C windows-ad (046-065), D concepts
(066-080), E defense-cloud (081-100). The letter matches each bundle's
`spec.track`.

## Rooms

50 of 100 authored. All 50 pass the automated gate. Origin:
20 migrated from the legacy LAN demo (PR #4), 30 original.

### Track A: web-foundations, complete at 25 of 25

| Slug                | Difficulty | Type      | Points | Origin   |
| ------------------- | ---------- | --------- | ------ | -------- |
| busted-login        | beginner   | guided    | 100    | migrated |
| nosy-files          | beginner   | guided    | 150    | migrated |
| ping-of-doom        | easy       | challenge | 200    | migrated |
| ssti-greeting       | easy       | challenge | 150    | migrated |
| token-forger        | medium     | challenge | 250    | migrated |
| idor-invoices       | beginner   | guided    | 125    | migrated |
| open-panels         | beginner   | guided    | 50     | migrated |
| cookie-shapeshifter | beginner   | guided    | 100    | migrated |
| regex-doom          | easy       | challenge | 125    | migrated |
| mass-assign         | easy       | challenge | 150    | migrated |
| xxe-importer        | medium     | challenge | 225    | migrated |
| pickle-jar          | medium     | challenge | 275    | migrated |
| trusted-proxy       | beginner   | guided    | 75     | migrated |
| wrong-method        | beginner   | guided    | 75     | migrated |
| open-closet         | beginner   | guided    | 50     | migrated |
| predictable-reset   | easy       | challenge | 175    | migrated |
| double-trouble      | easy       | challenge | 150    | migrated |
| fetch-boy           | easy       | challenge | 200    | migrated |
| union-vault         | easy       | challenge | 225    | migrated |
| brace-yourself      | easy       | challenge | 125    | migrated |
| tenant-trouble      | medium     | challenge | 200    | original |
| graph-maze          | medium     | challenge | 225    | original |
| cartographer        | easy       | challenge | 150    | original |
| race-to-zero        | hard       | challenge | 250    | original |
| cache-me-outside    | hard       | challenge | 275    | original |

### Track B: linux-networking, complete at 20 of 20

| Slug                     | Difficulty | Type          | Points | Origin   |
| ------------------------ | ---------- | ------------- | ------ | -------- |
| first-shell              | beginner   | guided        | 75     | original |
| paper-permissions        | beginner   | guided        | 100    | original |
| knock-knock              | beginner   | challenge     | 150    | original |
| capable-enough           | easy       | challenge     | 200    | original |
| dns-breadcrumbs          | easy       | challenge     | 175    | original |
| path-of-least-resistance | easy       | challenge     | 175    | original |
| scheduled-surprise       | easy       | challenge     | 175    | original |
| suid-story               | easy       | challenge     | 225    | original |
| sudo-side-door           | easy       | challenge     | 200    | original |
| packet-diary             | easy       | investigation | 125    | original |
| mailroom                 | medium     | challenge     | 225    | original |
| service-please           | medium     | challenge     | 225    | original |
| route-less-traveled      | medium     | challenge     | 225    | original |
| shared-secrets           | medium     | challenge     | 250    | original |
| container-window         | medium     | challenge     | 250    | original |
| nfs-no-boundaries        | medium     | challenge     | 250    | original |
| kernel-of-truth          | hard       | challenge     | 275    | original |
| proxy-pivot              | hard       | challenge     | 275    | original |
| namespace-escape-plan    | hard       | challenge     | 300    | original |
| quiet-persistence        | hard       | investigation | 300    | original |

### Track C: windows-ad, 5 of 20 authored

| Slug                  | Difficulty | Type      | Points | Origin   |
| --------------------- | ---------- | --------- | ------ | -------- |
| windows-welcome       | beginner   | guided    | 100    | original |
| share-and-share-alike | beginner   | guided    | 125    | original |
| quoted-intentions     | easy       | challenge | 150    | original |
| registry-keys         | easy       | challenge | 175    | original |
| service-accounted     | easy       | challenge | 200    | original |

### Track D: concepts (crypto/reversing/binary/mobile/hardware), 0 of 15

Nothing authored yet.

### Track E: defense-cloud, 0 of 20

Nothing authored yet.

## Difficulty distribution vs plan targets

Counts come straight from `metadata.difficulty` across all 50 bundles.

| Difficulty | Authored | Target | Gap |
| ---------- | -------- | ------ | --- |
| beginner   | 13       | 20     | -7  |
| easy       | 20       | 30     | -10 |
| medium     | 11       | 30     | -19 |
| hard       | 6        | 15     | -9  |
| insane     | 0        | 5      | -5  |
| Total      | 50       | 100    | -50 |

Reading: tracks A and B front-loaded easy content, so the shortage is
concentrated in medium (-19) with hard (-9) and the entire insane tier
still empty. Track D is the planned home of most insane rooms, so closing
the difficulty gap largely means authoring D and the rest of C/E.

Room points total 9000 across the 50 bundles (track A 4075,
B 4175, C 750).

## Curriculum inventory

Paths live in `content/paths/*/path.yaml`, modules in
`content/modules/*/module.yaml`. Every module carries one cheat sheet and
its sections contain prose/code/callout blocks plus one scored quiz block
per quiz section.

Totals vs launch minimums:

| Metric       | Authored | Target | Notes                      |
| ------------ | -------- | ------ | -------------------------- |
| Paths        | 12       | 20     | 3 modules referenced each  |
| Modules      | 36       | 60     |                            |
| Sections     | 216      | 300+   | sum of `spec.sections`     |
| Questions    | 115      | 1000+  | one scored quiz block each |
| Cheat sheets | 36       | 100    | one per module             |
| Capstones    | 11 refs  | 20     | see split below            |

Paths (module count in parentheses):

- start-here (3)
- linux-operator (3)
- linux-privilege-escalation (3)
- networking-for-security (3)
- web-pentester-1 (3)
- web-pentester-2 (3)
- windows-operator (3)
- soc-analyst-1 (3)
- soc-analyst-2 (3)
- cloud-security-fundamentals (3)
- devsecops-foundations (3)
- api-security (3)

Module spread by track: web-foundations 12, defense-cloud 12,
linux-networking 9, windows-ad 3. Module difficulties: easy 13,
medium 20, beginner 3, no hard modules yet.

Capstone references by path, straight from `spec.capstones`: api-security
mass-assign; linux-operator first-shell; linux-privilege-escalation
sudo-side-door and suid-story; soc-analyst-1 packet-diary and
knock-knock; soc-analyst-2 quiet-persistence; start-here busted-login;
web-pentester-1 busted-login; web-pentester-2 pickle-jar and race-to-zero.
Four paths (cloud-security-fundamentals, devsecops-foundations,
networking-for-security, windows-operator) list none. busted-login
capstones two paths at once, which is the kind of reuse the plan's quality
bar flags: distinct capstones should replace at least one of the two.
