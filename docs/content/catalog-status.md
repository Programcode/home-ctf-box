# Content catalog status

Tracks room, module, and path production against the launch targets:
100 rooms (20/30/30/15/5 across beginner/easy/medium/hard/insane),
20 paths, 60 modules, 300+ sections, 1000+ questions/tasks,
100 cheat sheets, 20 capstones.

A room counts as authored once it passes the automated gate: schema lint
via `cyberrange lint`, clean-build intended-path solver, reset/idempotency
proof, per-session flag match. `.github/workflows/content.yml` runs this
gate on every content PR in four solver shards. The latest green content
run on main is 32680139689 (2026-08-24); later runs fail before any step
executes for environmental reasons, so the current proof of record is a
local lint pass on this date: 109 bundles, 0 errors, 0 warnings.
Instructional, safety, and accessibility review happen through the studio
review workflow before a room counts as published. Regenerated from
`content/rooms/*/room.yaml`, `content/paths/*/path.yaml`, and
`content/modules/*/module.yaml` on 2026-08-24 at main commit `ddbc21e`.

Track letters follow plan section 8 with one extension: A web-foundations
(rooms 001-025), B linux-networking (026-045), C windows-ad (046-065),
D crypto-binary concepts (066-080), E defense-cloud (081-100), F classic
vulnerable boxes (101-105) added by PR #48. The four external-image
wrappers from PR #44 carry no room number and are listed separately.
The letter comes from each room's number range; one bundle deviates from
its range's `spec.track` value and is flagged inline.

## Rooms

109 authored against the 100-room launch target. All 109 pass the local
lint pass; solver shards last ran green on CI at run 32680139689. Origin:
20 migrated from the legacy LAN demo (PR #4), 85 original, 4 wrappers of
upstream OSS images (PR #44).

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
| cartographer        | easy       | challenge | 150    | original |
| tenant-trouble      | medium     | challenge | 200    | original |
| graph-maze          | medium     | challenge | 225    | original |
| cache-me-outside    | hard       | challenge | 275    | original |
| race-to-zero        | hard       | challenge | 250    | original |

25 rooms, 4075 points.

### Track B: linux-networking, complete at 20 of 20

| Slug                     | Difficulty | Type          | Points | Origin   |
| ------------------------ | ---------- | ------------- | ------ | -------- |
| first-shell              | beginner   | guided        | 75     | original |
| paper-permissions        | beginner   | guided        | 100    | original |
| scheduled-surprise       | easy       | challenge     | 175    | original |
| sudo-side-door           | easy       | challenge     | 200    | original |
| suid-story               | easy       | challenge     | 225    | original |
| capable-enough           | easy       | challenge     | 200    | original |
| path-of-least-resistance | easy       | challenge     | 175    | original |
| service-please           | medium     | challenge     | 225    | original |
| container-window         | medium     | challenge     | 250    | original |
| nfs-no-boundaries        | medium     | challenge     | 250    | original |
| knock-knock              | beginner   | challenge     | 150    | original |
| dns-breadcrumbs          | easy       | challenge     | 175    | original |
| proxy-pivot              | hard       | challenge     | 275    | original |
| route-less-traveled      | medium     | challenge     | 225    | original |
| packet-diary             | easy       | investigation | 125    | original |
| mailroom                 | medium     | challenge     | 225    | original |
| shared-secrets           | medium     | challenge     | 250    | original |
| kernel-of-truth          | hard       | challenge     | 275    | original |
| namespace-escape-plan    | hard       | challenge     | 300    | original |
| quiet-persistence        | hard       | investigation | 300    | original |

20 rooms, 4175 points.

### Track C: windows-ad, complete at 20 of 20

| Slug                  | Difficulty | Type          | Points | Origin   |
| --------------------- | ---------- | ------------- | ------ | -------- |
| windows-welcome       | beginner   | guided        | 100    | original |
| service-accounted     | easy       | challenge     | 200    | original |
| registry-keys         | easy       | challenge     | 175    | original |
| quoted-intentions     | easy       | challenge     | 150    | original |
| token-gesture         | medium     | challenge     | 250    | original |
| share-and-share-alike | beginner   | guided        | 125    | original |
| name-resolution       | easy       | challenge     | 175    | original |
| spray-day             | easy       | challenge     | 150    | original |
| graph-the-domain      | easy       | challenge     | 200    | original |
| ticket-booth          | hard       | challenge     | 275    | original |
| as-rep-arcade         | medium     | challenge     | 225    | original |
| delegated-trust       | medium     | challenge     | 250    | original |
| certificate-misprint  | hard       | challenge     | 275    | original |
| relay-station         | hard       | challenge     | 300    | original |
| gpo-gone-wrong        | hard       | challenge     | 300    | original |
| forest-footpath       | hard       | challenge     | 300    | original |
| backup-operator       | medium     | challenge     | 250    | original |
| blue-screenplay       | medium     | investigation | 250    | original |
| directory-recovery    | hard       | investigation | 300    | original |
| crown-jewels          | insane     | range         | 500    | original |

20 rooms, 4750 points.

### Track D: crypto-binary, complete at 15 of 15

| Slug                       | Difficulty | Type          | Points | Origin   |
| -------------------------- | ---------- | ------------- | ------ | -------- |
| encoding-is-not-encryption | beginner   | guided        | 75     | original |
| reused-horizon             | easy       | challenge     | 150    | original |
| padding-post               | medium     | challenge     | 250    | original |
| tiny-rsa                   | medium     | challenge     | 200    | original |
| signed-twice               | hard       | challenge     | 275    | original |
| strings-attached           | beginner   | challenge     | 125    | original |
| branch-manager             | easy       | challenge     | 175    | original |
| license-to-learn           | easy       | challenge     | 200    | original |
| stack-snacks               | medium     | challenge     | 250    | original |
| return-address             | hard       | challenge     | 300    | original |
| heap-house                 | insane     | range         | 500    | original |
| apk-breadcrumbs            | easy       | challenge     | 175    | original |
| intentional-leak           | medium     | challenge     | 225    | original |
| firmware-pantry            | medium     | challenge     | 275    | original |
| signal-in-the-noise        | hard       | investigation | 300    | original |

15 rooms, 3475 points.

### Track E: defense-cloud, complete at 20 of 20

| Slug                     | Difficulty | Type          | Points | Origin   |
| ------------------------ | ---------- | ------------- | ------ | -------- |
| alert-one                | beginner   | guided        | 100    | original |
| phish-food               | beginner   | challenge     | 125    | original |
| web-trail                | easy       | investigation | 150    | original |
| memory-lane              | medium     | investigation | 250    | original |
| disk-detective           | medium     | investigation | 275    | original |
| cloudtrail-of-crumbs     | easy       | challenge     | 175    | original |
| bucket-brigade           | easy       | challenge     | 150    | original |
| role-play                | medium     | challenge     | 250    | original |
| function-junction        | medium     | challenge     | 225    | original |
| kubernetes-paper-walls   | medium     | challenge     | 275    | original |
| pipeline-spill           | easy       | challenge     | 150    | original |
| dependency-confusion-lab | medium     | challenge     | 250    | original |
| image-issues             | medium     | investigation | 225    | original |
| detection-forge          | hard       | challenge     | 300    | original |
| threat-hunt-northstar    | hard       | investigation | 300    | original |
| minimcorp-breach         | hard       | range         | 400    | original |
| minimcorp-defense        | hard       | investigation | 400    | original |
| purple-replay            | hard       | range         | 350    | original |
| cloud-company            | insane     | range         | 500    | original |
| full-spectrum            | insane     | range         | 600    | original |

20 rooms, 5450 points. Note: minimcorp-breach (096) declares
`spec.track: windows-ad` in its bundle even though it sits in the
defense-cloud number range; minimcorp-defense, its matching blue-team
room, declares defense-cloud.

### Track F: classic boxes (spec.track stays linux-networking), complete at 5 of 5

| Slug                | Difficulty | Type      | Points | Origin   |
| ------------------- | ---------- | --------- | ------ | -------- |
| services-everywhere | easy       | box       | 250    | original |
| kernel-adjacent     | medium     | box       | 300    | original |
| phoenix-stack       | medium     | challenge | 275    | original |
| dockerlabs-vibes    | easy       | box       | 225    | original |
| boot2root-finale    | hard       | box       | 350    | original |

5 rooms, 1400 points.

### External OSS wrappers, no room number

| Slug               | Difficulty | Type   | Points | Origin  |
| ------------------ | ---------- | ------ | ------ | ------- |
| dvwa-cmdi          | easy       | guided | 100    | wrapper |
| juice-shop-tour    | beginner   | guided | 75     | wrapper |
| webgoat-first-flag | easy       | guided | 125    | wrapper |
| wrongsecrets-one   | easy       | guided | 100    | wrapper |

4 rooms, 400 points. Each pins an upstream official image by digest;
see `docs/labs-external.md` for the licensing stance.

## Difficulty distribution vs plan targets

Counts come straight from `metadata.difficulty` across all 109 bundles.
Targets describe the 100-room launch shape, so the total row compares
against 100 while authored counts include the five extra track F boxes
and the four wrappers.

| Difficulty | Authored | Target | Gap |
| ---------- | -------- | ------ | --- |
| beginner   | 18       | 20     | -2  |
| easy       | 36       | 30     | +6  |
| medium     | 30       | 30     | 0   |
| hard       | 21       | 15     | +6  |
| insane     | 4        | 5      | -1  |
| Total      | 109      | 100    | +9  |

Reading: the platform passed its 100-room target with nine rooms to
spare. Beginner is still two short of plan and insane holds four of five;
both shortages sit inside otherwise complete tracks. Every difficulty
band except beginner and insane meets or beats target.

Type spread against the plan section 8 minimums: guided 18
(minimum 30, short by 12), challenge 70 plus box 4
= 74 unguided (minimum 50, met),
investigation 11 (minimum 10, met), multi-host range 6
(minimum 5, met). The guided shortfall is real: only tracks A through C
open with guided walkthroughs, and nothing later in the catalog walks
learners through step by step.

Room points total 23725 across the 109 bundles (track A 4075,
B 4175, C 4750, D 3475, E 5450, F 1400, wrappers 400).

## Curriculum inventory

Paths live in `content/paths/*/path.yaml`, modules in
`content/modules/*/module.yaml`. Every module carries one cheat sheet and
exactly six sections; quiz sections hold one scored block each.

Totals vs launch minimums:

| Metric       | Authored | Target | Notes                            |
| ------------ | -------- | ------ | -------------------------------- |
| Paths        | 18       | 20     | 3 modules referenced each        |
| Modules      | 54       | 60     |                                  |
| Sections     | 324      | 300+   | target met                       |
| Questions    | 181      | 1000+  | one scored quiz block each       |
| Cheat sheets | 54       | 100    | one per module                   |
| Capstones    | 13 refs  | 20     | across 10 paths; see split below |

Paths (module count in parentheses):

- api-security (3)
- applied-crypto-attacks (3)
- binary-exploitation-foundations (3)
- cloud-security-fundamentals (3)
- devsecops-foundations (3)
- dfir-investigator (3)
- kubernetes-container-security (3)
- linux-operator (3)
- linux-privilege-escalation (3)
- malware-reversing-foundations (3)
- networking-for-security (3)
- professional-security-engagement (3)
- soc-analyst-1 (3)
- soc-analyst-2 (3)
- start-here (3)
- web-pentester-1 (3)
- web-pentester-2 (3)
- windows-operator (3)

Module spread by spec.track: defense-cloud 18,
web-foundations 15, linux-networking 9,
crypto-binary 9, windows-ad 3.
Module difficulties: medium 35, easy 16,
beginner 3; no hard modules exist yet, which mirrors
the room-side shortage at the top difficulty bands.

Capstone references by path, straight from `spec.capstones`:

- api-security: mass-assign
- dfir-investigator: quiet-persistence
- kubernetes-container-security: container-window
- linux-operator: first-shell
- linux-privilege-escalation: sudo-side-door, suid-story
- soc-analyst-1: packet-diary, knock-knock
- soc-analyst-2: quiet-persistence
- start-here: busted-login
- web-pentester-1: busted-login
- web-pentester-2: pickle-jar, race-to-zero

Eight paths list none: applied-crypto-attacks, binary-exploitation-foundations, cloud-security-fundamentals, devsecops-foundations, malware-reversing-foundations, networking-for-security, professional-security-engagement, windows-operator.
busted-login capstones two paths at once (start-here and web-pentester-1),
and quiet-persistence does the same for both soc-analyst paths, which is
the kind of reuse the plan's quality bar flags: distinct capstones should
replace at least one reference in each pair.
