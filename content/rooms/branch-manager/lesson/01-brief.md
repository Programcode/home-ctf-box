# branch-manager

A program is a graph of branches, and reversing is often the craft of
reading that graph when the source is not available. This room gives
you a small license checker whose visible behavior lies to you. The
banner quotes a vendor bulletin, the bulletin names a key format, and
the key it suggests can never work, because the constant used in that
comparison was corrupted before the build shipped. Only by reading the
actual instructions can you find which branch is live and what it
demands from your input.

## Control flow as the real specification

Run /opt/challenges/license-check and try the advertised format. The
verifier rejects it. That rejection is data: somewhere in the binary a
comparison failed, and your job is to find it. A disassembly dump turns
guessing into reading. The image ships one at
/opt/challenges/notes.asm, generated with objdump -d while the binary
was built, and this build keeps function names intact so you can jump
between named regions instead of drowning in anonymous bytes. Look at
corrupt_compare first: its string constant ends in an unprintable byte,
which is why no typed key satisfies it. That is a dead branch. Dead
branches are common in real software, left behind by refactors, feature
flags, or deliberate decoys, and recognizing them saves enormous time.

## Extracting constants from cmp instructions

The live route into grant_license runs through verify_key, and
verify_key asks three numeric questions about your input: its length,
the arithmetic sum of its bytes, and its first byte. In assembly those
appear as cmp instructions with immediate operands, values like $0x14
or $0x775 written directly into the instruction stream. Strings tools
never show these because they are numbers, not text; only the
disassembly carries them. Read them in order and you have a precise
specification of every accepted key.

## Crafting input from constraints

Constraints derived from comparisons rarely have a single answer, and
that flexibility is yours to use. You need twenty bytes starting with B
whose values add up to 1909. Pick a cheap filler character, do the
arithmetic once, and any key meeting the three checks takes the branch.
Feed it in on stdin and the checker prints your flag. The lesson
generalizes: when input validation blocks you, the disassembly tells
you exactly what the validator wants, and satisfying a validator
honestly is often simpler than attacking it.
