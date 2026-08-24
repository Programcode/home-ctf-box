# Firmware Pantry

Firmware analysis looks exotic from the outside and is mostly patient
file carving once you are inside. A vendor update lands in your
evidence folder, you work out which byte ranges mean what, cut an
embedded filesystem free, and read whatever the shipping image
carries. This room compresses that loop into one synthetic PantryGate
image: a 512-byte printable stub that doubles as release notes, an
8-byte FSQSIM1 magic, then a POSIX tar compressed with xz holding a
small simulated root filesystem. Somewhere in etc/shadow-sim sits
admin's password hash, and a wordlist waits on the same evidence shelf.

Say plainly what this is not. The image contains no machine code, no
real vendor identity, and no credential used anywhere beyond this
container. The shadow entry uses a $sim$ marker with plain SHA-256 so
the math stays deterministic and offline friendly. The extraction,
hashing, and reporting habits are the real deliverable.

## Carving the archive out of the container

Real images rarely announce their layout, which is why binwalk exists:
it walks the bytes, matches known signatures, and reports offsets.
Squashfs images start with hsqs, gzip streams with 1f 8b, xz with fd
37 7a 58 5a 00, and cpio archives with 070701. You rehearse exactly
that scan here, with two twists worth keeping. The stub prints its own
contract, telling you the archive starts after the magic at offset
512, but it also spells the magic while describing itself, so a naive
first-find lands you in prose. Validate candidates by their
neighborhood instead: accept an FSQSIM1 occurrence only when the xz
signature follows immediately. That habit generalizes to real carving,
where signatures appear inside compressed noise constantly and only
context confirms them. After slicing at offset 512 and confirming the
signature sits where arithmetic says it should, `tar -xJf` or Python's
tarfile opens the tree; list names before reading anything so you know
what shipped.

Reading the extracted files is where firmware assessment earns its
fee, and the payoff justifies the carving work. Vendors ship
configuration files, default passwords, hardcoded keys, stale
binaries, and private hostnames inside updates, all invisible until
someone unpacks the image and looks. Here the prize is etc/shadow-sim,
formatted like a Unix shadow database but marked $sim$ to keep honesty
intact, one line per account with the admin entry carrying a hash you
can attack offline.

## From hash to login

The admin line carries 64 hex characters, the exact width of a raw
SHA-256 digest, and the room guarantees no salt: sha256(password)
equals what the file stores. That makes the crack a dictionary loop,
the oldest and still most productive attack in password work.
Hash every line of wordlist.txt, strip newlines first, and compare
lowercase hex digests; exactly one candidate matches. In production
work this is hashcat mode 1400 territory, and the reason it works here
is the same reason it fails against modern systems: fast unsalted
digests surrender to offline guessing, while salted slow schemes like
yarcrypt make each guess expensive and unique. When your word hits,
POST it to /admin/login as user=admin and password, read the flag,
and carry away the reportable finding: this device published
password-equivalent material inside its own update channel, which is
a standing invitation to anyone who downloads firmware from the
vendor's site.
