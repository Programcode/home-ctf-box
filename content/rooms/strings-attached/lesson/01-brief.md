# strings-attached

Before a binary runs, it already tells you most of its story. Every
string literal a C program contains, every option name, every prompt,
every error message, ends up in the compiled file so the program can
print it later. Static triage is the discipline of reading that story
before you execute anything, and it is the fastest way to understand
an unfamiliar program on an unfamiliar box.

## What you will practice

The room gives you one small custom binary at /opt/challenges/ledger.
Start with `file /opt/challenges/ledger`, which parses the ELF header
and reports the architecture, linkage, and whether the binary is
stripped of symbols. That single line tells you which tools will work
and what to expect. Then run `strings /opt/challenges/ledger` and read
the output slowly. You are looking for literals the author wrote: a
usage line listing supported options, and anything else that hints at
behavior the usage does not mention. Comparing what the usage advertises
against what the string table contains is a habit worth building early,
because hidden or forgotten modes are common in real software and they
are usually reachable by anyone who reads.

## Running the hidden mode

Among the strings you will find the name of an option that never
appears in the usage line. Run the documented options first so you know
what normal output looks like, then run the undocumented one. It prints
a hex blob plus a key byte in hex. The transformation is a single-byte
XOR: every plaintext byte was combined with that fixed key using XOR
before being printed as hex. XOR has a property that makes it ideal for
exercises like this and terrible for real confidentiality: applying the
same operation with the same key twice returns the original data. So
the decode step is the encode step run in reverse.

## From bytes back to text

Decode the blob with a short Python one-liner, or by hand if you want
to feel each byte flip. The restored text holds your flag. When you
finish, notice how little risk you took: no debugger, no patching, no
guessing. File identification, string extraction, careful reading, and
one reversible math operation carried you from an unknown binary to
its secret. That workflow scales up to much larger reversing tasks,
where the same first steps always come before anything fancier.
