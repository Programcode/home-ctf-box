# minimcorp-breach

Capstones are where a track stops holding your hand and starts checking
whether the skills stuck. This room compresses an enterprise intrusion
into three simulated hosts on one box: a VPN edge that never deleted an
old rollback config, an internal wiki guarded by credentials that
config hands over, and a finance API that trusts its gateway more than
it trusts itself. You finish by forging what the estate treats as its
crown credential, a directory-sim admin token, and only then does the
scoreboard open. Each host surrenders one fragment of the master flag,
and the fragments matter only together. The chain is sequential on
purpose: every hop produces exactly the material the next hop demands,
which is how real intrusions actually move, one small oversight quietly
paying for the next step inward. Work it in order and keep written
notes per host, because when the scoreboard rejects you at the end you
want lookup to take seconds, not another walk of the estate.

## Reading the perimeter before touching it

Start at vpn-edge.minimcorp.net and read the page source, not just the
rendered text. Operational teams leave comments for each other all the
time, and forgotten staging or rollback artifacts behind those comments
are the single most reliable first foothold in perimeter assessments.
The comment here admits a rollback snapshot still sits at a predictable
static path. Fetch it, notice it is base64 rather than encrypted, and
decode it locally. Inside you find the host's flag fragment plus basic
auth credentials for the internal wiki, which teaches a habit worth
more than any single exploit: whenever you recover credentials, ask
where else that same pair has been reused before you attack anything
else. Credential reuse across trust boundaries is the connective tissue
of almost every real breach, and the room's chain will not advance
unless you make reuse your default assumption. Keep the decoded config
handy even after you move on, because its asides about finance and the
directory sim are quietly telling you the shape of the rest of the
estate, and attackers who read carefully finish faster than attackers
who enumerate blindly.

## The wiki as an intelligence drop

The wiki answers only with valid basic auth, so authenticate as the
service account you recovered and then behave like an analyst instead
of a tourist. List the space, open the finance runbook, and read it
end to end because runbooks document exactly the assumptions attackers
love: static integration keys issued once and copied into every
pipeline, endpoint shapes nobody re-reviews, and a delegated sign-in
scheme whose signing secret was written down years ago with the word
never next to rotation. Then check the page's revision history, because
collaboration metadata routinely leaks more than the content does; this
room stamps the second fragment into a revision comment the way sync
bots really do stamp identifiers into places reviewers forget to look.
The lesson is that authenticated recon should be slow and greedy.
Read everything twice before you send a single crafted request. Note
also what the wiki chooses to record: page reads and revision lists are
audit events on real estates, which means your own browsing is already
writing the blue team's timeline for them, a fact worth remembering
from both sides of the wire.

## Broken authorization at the finance API

Armed with the integration key, turn to finance.minimcorp.net and test
the runbook's claims. Invoice records are keyed by numeric employee ids
that start at 1001 and climb sequentially, and the gateway checks only
that your key exists, never whether the record belongs to you. That
mismatch between where access control happens and where data lives is
the definition of broken object-level authorization. Enumerate upward
with patience: most ids are ordinary expense lines, one id belongs to
an executive ledger extract, and the extract carries the third fragment
plus the name of the privileged principal whose identity you are about
to assume. Notice what made this possible. Sequential identifiers gave
you a map, and centralized enforcement without per-record checks gave
you permission. Both failings are boring, common, and worth reporting
every time you see them. A competent fix is unglamorous, per-object
authorization plus unpredictable identifiers, but it removes an entire
attack class rather than one instance of it, which is why finding IDOR
matters more than the data any single request returns.

## Forging trust from a documented scheme

The last stage is the one people underestimate. The runbook told you
precisely how the directory sim verifies delegated sign-ins: an md5
digest over user, role, and a legacy secret, all three of which you now
hold. Nothing here requires cleverness, only assembly. Hash the exact
string for principal a.adams with role estate-admin, submit it to the
verification endpoint, and receive the admin token the scoreboard
demands alongside your three fragments. When it unlocks, sit with why:
the scheme was documented, the secret was unrotated, and the signature
carried no server-side session or nonce, so anyone who read the runbook
could be anyone at all. Then file the whole journey away as a pattern:
leak, reuse, read generously, test claims against behavior, and forge
what documentation handed you. Every real-world delegation protocol,
from SAML assertions to internal service tokens, fails the same way
when its signing material is shared, static, and fully described in a
document any compromised service account can open.

## What is simulated here

Say it plainly: this is one Linux container, disclosed identically on
the landing page, in the safety notes, and here. Three Flask apps bind
to three loopback ports inside the box, the controller proxies between
them like an edge proxy fronts a corporate network, fragments are
slices of this session's flag, and the token forge is md5 over fields
this room itself hands you because no real cryptographic attack exists
here. No real exploit code ships in this image, nothing executes
outside the process, and nothing leaves the container. What transfers
is the sequence: read sources and comments, decode careless artifacts,
reuse recovered credentials deliberately, mine collaboration metadata,
enumerate identifiers until authorization breaks, and treat documented
trust schemes as attack surface. Each technique has a dedicated room
earlier in the track; this capstone asks you to run them back to back
without a reset, which is the honest shape of an intrusion.
