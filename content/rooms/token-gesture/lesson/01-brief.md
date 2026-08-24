# token-gesture

Windows lets a process reach into other logon sessions and borrow the
identities it finds there. The famous privilege name,
SeImpersonatePrivilege, is really a stand-in for a family of design
decisions: services accept tokens from callers, tools act in the name of
whatever identity they hold, and everything downstream inherits that
choice. Attackers learned to feed privileged services material shaped
like legitimate tokens, and a whole exploit family grew from that one
gap between accepting input and trusting it. Defenders responded by
treating the privilege itself as radioactive, restricting which accounts
hold it and auditing wherever it appears, because once a privileged
component agrees to act on supplied material, the origin of that
material decides who really owns the action. This room rebuilds the
concept on Linux with plain files and one small root helper, because the
lesson is about provenance and trust placement rather than Windows
internals. You will read simulated tokens, learn their documented
format, notice which directory the privileged helper consults first,
and hand it an identity you built yourself. When the helper acts on your
forged identity's behalf, you will have reproduced, honestly and
legally, the exact reasoning arc that real token abuse follows.

## What is real here, and what is simulated

The platform runs Linux containers only. There is no Windows kernel
here, no token handle, no access check, and no impersonation call.
What the room provides instead is a simulated token store at /opt/tokens
holding three plainly labeled JSON files whose fields mirror real token
attributes: user, domain, group memberships, integrity level. Each file
carries a checksum computed over its own body with sha256, and a README
inside the store documents the exact recipe. A helper program called
tokentool stands in for a token-aware service; through one sudo grant it
runs as root and can list tokens or assume an identity they describe.
The Unix mechanics are real throughout. The sudo grant genuinely
elevates only that single binary, the flag file at /root/flag.txt
genuinely denies every account except root, the cache directory at
/var/cache/tokentool genuinely has mode 777, and your session genuinely
runs as uid 1000 with no other powers. Nothing pretends to parse real
Windows token structures and every artifact labels itself as
simulation, starting with the motd banner you see at login.

## Why token provenance matters

The room's central trick fits in one sentence: a checksum proves the
bytes were not edited, not who wrote them or where they came from.
Real Windows token abuse rhymes with this constantly. Services holding
SeImpersonatePrivilege accept authentication material from clients as a
normal part of their job, and attackers spend enormous effort coaxing
those privileged processes into handling attacker-shaped tokens, which
is exactly what the potato family of exploits does against Windows. A
format-valid, internally consistent credential that arrived through a
writable location is still attacker material, and validation schemes
that stop at internal consistency miss that entirely. When you later
audit real systems, ask three questions of every trusted artifact:
where does it come from, who can write that location, and would the
validation notice a forgery that simply reused the correct format?
tokentool answers all three badly on purpose, and the flag falls out as
direct proof that provenance beats integrity checks every time.

## Walking the intended path

Log in as learner and read before you write anything. The motd
discloses the simulation, /opt/tokens/README.txt documents every field
including the checksum recipe, and `sudo -n tokentool --list` shows the
helper enumerating both stores while marking each entry trusted or
cache. Compare the three issued tokens and notice the asymmetry built
into them: the kiosk identity holds low integrity, the backup service
holds medium, and the nightly service holds high integrity but only
SERVICE OPS-SIM membership, so assuming it politely performs nothing
privileged. That contrast tells you precisely which two fields must
qualify at once. Then forge: build your own JSON with user adm-sim,
high integrity, DOMAIN ADMINS-SIM membership, compute the checksum
exactly as documented with sorted keys and compact separators, and
place the file in /var/cache/tokentool, where your unprivileged account
can already write. Listing again shows your entry sourced from cache.
Run `sudo -n tokentool --assume adm-sim`, watch the helper announce the
assumed identity, see both conditions satisfied, and collect the flag
it reads from the guarded file.

## Scope

Confine yourself to ssh://target:22 and the learner account this room
publishes. The container reaches nothing beyond the lab network: no
internet, no host, no control plane, no neighboring labs. Everything
you need sits inside this instance: three sample tokens, one documented
checksum recipe, one world-writable directory, one sudo-granted binary,
and one guarded flag file. Do not attack sshd itself, do not attempt to
read /root/flag.txt by other escalation routes, and do not try to widen
the sudo grant beyond tokentool; none of that is necessary for the
intended path and none of it is in scope. Credentials printed anywhere
in these rooms are disposable training labels shared across instances,
so never carry them to systems outside the lab, and never test
techniques from this room on machines you do not own. If an exercise
seems to demand out-of-scope action, reread the room instead; the
answer is always inside the box.
