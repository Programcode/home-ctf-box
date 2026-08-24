# crown-jewels

Capstones exist to make you prove that everything earlier in the track
was skill and not luck. This room compresses an entire attack
narrative into five simulated hosts: a leaky web portal in the DMZ, an
overconfident database API, a file server with something to hide, a
domain controller exporting weak secrets, and a workstation where the
intruder left persistence behind. Each host surrenders one fragment of
the master flag, and the fragments only matter together. You cannot
skip around meaningfully: every hop's findings are the next hop's
keys, which is precisely how real intrusions unfold, one small victory
quietly funding the next until someone finally notices. Work it in
order, write your findings down as you go, and treat each host's
disclosures as reconnaissance rather than trivia.

## The estate and how to walk it

The front controller on port 8000 routes by Host header, so you
address each simulated host by name exactly as you would vhost-route
through a reverse proxy. Start at web.dmz and read everything,
including HTML source comments, because careless staging artifacts are
the classic first foothold on any perimeter. The leaked deploy config
there is obfuscated with XOR and the page itself tells you the key
convention; decoding it yields working credentials for db.internal
plus your first fragment. On db.internal, read the API docs with an
analyst's suspicion rather than a tourist's trust: services that
loudly claim all queries are parameterized are asking to be tested.
Probe each documented endpoint yourself with injection payloads and
let behavior, not documentation, tell you what is safe. That habit
alone separates operators from tourists more reliably than anything
else in this track, because documentation is written by the vendor's
optimism and behavior is written by reality.

## From foothold to estate

The database host rewards the probe: one endpoint concatenates user
input straight into SQL despite the docs, and a UNION against its
vault table returns the second fragment along with intelligence naming
the next two stops, a hidden share on filesrv and a preauthentication-
disabled account on dc01. That note is the room teaching chain
discipline, because findings feed forward or they feed nothing. The
hidden share never appears in listings but answers when addressed
directly, hidden is not protected, and its backup log carries the
third fragment alongside a remark about legacy exports. dc01 marks the
named account as roastable; its export uses a documented toy cipher,
so pull the served wordlist, encode each candidate locally, match the
hash, and redeem the password for the fourth fragment plus a pointer
to workstation7's task family. workstation7 closes it out: six
persistence artifacts, one planted by unknown hands at an ugly hour,
its action string carrying the fifth piece inside padding noise.

## Assembling and reporting

Fragments score nothing individually, which is deliberate. Partial
compromise of an estate is not compromise, and unverified findings do
not belong in anyone's report. POST all five fragments to /scoreboard
and the controller verifies each against this session's flag before
unlocking the master value you actually submit for grading. The design
mirrors how assessment platforms separate progress from proof, and it
forces the reporting habit that matters operationally: assemble
verified state end to end before declaring victory, and let the
verifier, not your confidence, decide whether the chain holds. If the
scoreboard locks you out, it names which hosts were accepted, wrong,
or missing, so debugging your own chain becomes one more exercise in
precise bookkeeping under pressure. Keep your fragment notes labeled
by host as you collect them, because a scoreboard rejection at the
finish line should cost you seconds of lookup, not minutes of
re-walking hosts you already solved.

## What is simulated here

Say it plainly: this is one Linux container, disclosed identically on
the landing page, in the safety notes, and here. Five Flask apps bind
to five loopback ports inside the box, the controller proxies between
them like nginx fronts an internal network, fragments are slices of
this session's flag, and the credential crack runs a rot+7 byte cipher
against a wordlist the box serves you because no GPU cracking exists
here. No real exploit code ships in this image, no payload executes,
and nothing leaves the container. What transfers is the sequence:
enumerate leaks, verify claims, follow intel across trust boundaries,
crack whatever was exported carelessly, sweep persistence last, and
never mistake one host's cooperation for ownership of the estate. The
individual techniques all have dedicated rooms earlier in track C;
this capstone asks you to run them back to back without a reset
between them, which is the honest shape of a real engagement.
