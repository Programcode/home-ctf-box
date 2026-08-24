# registry-keys

Ask a Windows administrator where the operating system keeps its
settings and you will hear one word: the registry. Ask where
credential hygiene goes to die and you will often hear about the same
place. The registry is a hierarchical database of keys and values,
split conceptually between HKLM for machine-wide settings and HKCU
for per-user ones. Most of it is boring configuration, but certain
keys have historically held live secrets, and few are as famous as
the autologon values under HKLM's Winlogon key. When administrators
enable automatic logon for convenience, Windows may store the account
name and password right there, readable by anyone who can read the
hive. Attackers who land on a box make checking that key an early
step precisely because the payoff, working credentials for a likely
privileged account, is so outsized. This room teaches that whole arc:
explore, find the leaky value, and reuse what it hands you.

## What is real here, and what is simulated

The platform runs Linux containers only, so no Windows registry
exists here in any binary form. What this room provides instead is a
simulated registry under /opt/registry, organized into explicit HKLM
and HKCU subtrees whose plain-text .hiv files carry faithful value
names: AutoAdminLogon, DefaultUserName, DefaultPassword, Run entries,
per-user application preferences. The structure, naming, and meaning
are true to Windows; the file format itself is a labeled stand-in,
and a README inside the tree says exactly that. The credential reuse
half of the room is entirely real Unix mechanics: the password stored
in the simulated hive genuinely authenticates the adminsim account on
this container, over su or SSH, and its home directory genuinely
denies you until you hold it. Nothing pretends to parse real hive
binaries, nothing touches actual Windows, and every artifact labels
itself as simulation.

## Why autologon leaks matter

The Winlogon key sits under HKLM\SOFTWARE\Microsoft\Windows NT\
CurrentVersion, and its autologon values tell Windows to sign an
account in at boot without typing anything. Set AutoAdminLogon to 1,
fill in DefaultUserName, and on legacy configurations DefaultPassword
held the secret in cleartext. Modern Windows offers encrypted storage
for exactly this reason, but countless machines and third-party tools
still create the plaintext pattern, and offline hive dumping puts the
whole database in an attacker's hands anyway when they have disk
access. The security lesson generalizes far past this one key:
configuration stores accumulate secrets, secrets get stored beside
the settings that use them, and anyone who can read the store owns
whatever it protects. When you later audit real systems, registry
value names like the ones here are worth grepping for, because the
failure mode has not retired, it has just moved.

## Walking the intended path

Start as learner and treat /opt/registry as the database it stands in
for. Listing the tree shows you both hives' shapes before you read a
line, which builds the mental model better than jumping straight to
the answer file. A recursive grep for the autologon value name takes
you to the Winlogon equivalent immediately; reading it should feel
like eavesdropping on a misconfiguration happening in slow motion.
The two values you need name the account and hand you its password,
and this room makes the reuse step honest: those credentials actually
work against the adminsim account on this container, either through
su from your current session or through a fresh SSH login as that
user. Once authenticated, the flag waits in the new home directory,
one cat away from submission. Notice how little privilege was needed
at any point; readable configuration did all the work, which is
exactly why real defenders lock hive access down.

## Scope

Confine yourself to ssh://target:22 and the accounts this room
publishes. The container reaches nothing beyond the lab network: no
internet, no host, no control plane, no neighboring labs. Your goal
is one credential pair exposed by the room itself and one flag file
inside this instance, and the intended path needs nothing more than
grep, cat, su, and a second SSH session. Do not attempt to crack the
password hashes in /etc/shadow or attack sshd itself; neither is in
scope and neither is necessary. Credentials printed anywhere in these
rooms are disposable training labels shared across instances, so
never carry them to systems outside the lab, and never test techniques
from this room on machines you do not own. The moment an exercise
seems to demand out-of-scope action, reread the room instead.
