# directory-recovery

Ransomware crews learned something years ago that defenders took
longer to absorb: encrypting files is noisy, but owning the directory
is total. When the domain controller goes, every trust in the estate
goes with it, which is why serious organizations rehearse the rebuild
before it is ever needed rather than improvising it at three in the
morning. This room drops you into exactly that moment for a simulated
domain called SIMDOMAIN. The intruders, who sign themselves SHADOW
VIPER CREW, left a payment demand and a promise to delete what they
copied. Leadership has already answered the demand: we rebuild, you
make sure we rebuild right. Your job as recovery lead is to work the
evidence pack until you know what was touched, which media can be
trusted, and in what order things must happen.

## Letting the note set the clock

Evidence means little without a timeline anchor, so the first artifact
you read sets the boundary for everything after it. The ransom note
does you one unintentional courtesy: it states when encryption began.
That timestamp becomes T0, the edge of your compromise window, and the
whole analysis hangs off it. The ntds-sim dump lists every account
with whenCreated and whenChanged attributes; anything stamped at or
after T0 was written during the incident, by the intruders or under
their influence. Expect the classic pattern once you filter: a
service-looking account created mid-window with Domain Admins
membership nobody requested, another granted backup-style rights with
no ticket behind it, and a plausible-sounding helpdesk account whose
password changed without change control. Attackers love names that
blend into the directory; timestamps do not blend, and that asymmetry
is your entire advantage as the defender reading the dump. Filter on
both attributes separately too, because creations and modifications
tell different stories about what the intruder built versus what they
broke.

## Choosing media you can actually trust

Restore media selection trips up even experienced teams because two
properties must hold simultaneously, not either/or. The backup must
predate T0, or you are faithfully restoring the attacker's changes
along with everything else and handing them persistence back on a
silver platter. It must also be verified offline, meaning a copy
confirmed intact on immutable media outside the storage the ransomware
touched. A snapshot taken on live disks fails the second test even
when its date looks acceptable, because snapshots ride the same
infrastructure the intruder controlled and may themselves be encrypted
or doctored. An incremental taken hours before the window but never
verified fails too: maybe it is fine, maybe it is where they hid, and
recovery runs on proof rather than hope. In this pack exactly one
candidate satisfies both properties at once, and finding it is less
about luck than about refusing to compromise on either test.

## Sequencing the rebuild

Order carries consequences that no checklist can undo after the fact.
Isolate first so the attacker cannot reach whatever replaces the dead
DC. Preserve forensics second, because rebuilding over evidence
destroys your only record of what happened and leaves you defending
the same hole twice. Only then rebuild the DC from clean media, restore
the selected backup, rotate every credential the rogues could have
reached including service accounts, and verify services while watching
for the intruder's return trip. The /recover menu includes steps that
sound tempting in the moment, like paying the crew or trusting their
deletion promise; both belong to the same category of fiction, since
payment funds the next attack and their deletion promise has never
once been kept anywhere. Submit the full plan to /recover and the
endpoint grades each part separately until the simulated DC comes back
clean, and if a part fails, its feedback names which component to
rethink rather than leaving you guessing at the whole plan.

## What is simulated here

One locked Linux container hosts everything, disclosed here and on the
box itself. No encryption code runs, no payload executes, and the
ntds-sim fragments are static JSON standing in for an NTDS database
export split across two recovered pieces. Nothing you submit can break
anything real, and the grading API does deterministic string checks.
What transfers is the methodology, and it transfers completely:
anchoring a timeline from adversary artifacts, diffing directory state
against that anchor, doubting any medium that cannot prove its own
integrity, and sequencing recovery so containment precedes cleanup.
Real AD recovery adds tooling such as DSRM restores, SYSVOL
verification, and KRBTGT double resets, but every judgment call this
room drills remains identical when the stakes stop being simulated,
which is exactly why tabletops like this one reward repetition until
the order of operations feels reflexive rather than recalled. Run it
twice: once for the flag, once for the reflexes, and notice which
parts get easier the second time through.
