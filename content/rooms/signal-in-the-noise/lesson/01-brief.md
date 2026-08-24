# Signal in the Noise

Cheap garage remotes, gate openers, and weather sensors speak a
language simpler than anything on the internet: turn the carrier on
for a while to send a one, off for a while to send a zero. A capture
of that transmission is just amplitude over time, and this room hands
you one as raw complex int16 samples plus an envelope plot. Six
repetitions of the same 72-bit frame carry a 64-bit code whose top
half identifies the remote and whose bottom half rolls upward. The
bench receiver wants the half that never changes.

Honesty first. Nothing was transmitted and nothing real opens. The
capture comes from Python integer math with fixed constants inside
this container, the modulation is textbook on-off keying with a
generous 8 samples per bit, and the opener is a Flask route. The
transferable part is the workflow: parse interleaved samples,
demodulate by threshold, align frames, and let repetition tell you
which bits are identity and which are state.

## From bytes to bits without libraries

The file holds no header, only alternating little-endian signed 16-bit
I and Q pairs, so `struct.unpack` with a computed count is the whole
parser. Quadrature carries tiny wobble here; the decision statistic is
absolute I against the documented 3000-count threshold, which turns
3600ish samples into a string of level bits. Because every symbol
spans exactly 8 samples, consecutive equal levels come in multiples
of 8, and collapsing runs into (level, length) pairs then expanding
each length divided by 8 reconstructs the transmitted bit sequence
exactly. That run-length trick is worth internalizing: it is how you
decode any constant-symbol-rate OOK signal once you know or guess the
symbol period, and guessing it is easy when wrong periods produce
ragged runs.

Alignment follows from structure rather than luck, and structure is
what you should hunt for in any protocol. Each frame opens with
10101010, so searching the bit string for that preamble finds
candidate starts; take the following 64 bits as two 32-bit words.
False alignments can occur inside payload data, and the defense is
statistical: the true static word appears at every repetition while
accidental matches scatter randomly. Count candidate top words and
keep the one that repeats across frames, then sanity-check that its
companions increment monotonically like a counter should.

## Why repetition gives the code away

The rolling section exists precisely to defeat replay, yet naive
implementations hand attackers the static half anyway. Observing
several transmissions and diffing them, the de Bruijn-style pattern
analysis this case documents, separates constant identity bits from
counters: identical across captures means identifier, incrementing
means state. Here the counter increments by exactly one per repetition
and the receiver, embarrassingly, still honors the static half alone,
which is why your replay works and why the case closes at all. Real
systems earn their security by
making both halves matter through a shared secret algorithm such as
KeeLoq's successors, though history shows those fail too when the
keystream is weak. The defensive summary writes itself: never accept a
fixed identifier as authorization, rotate genuinely with cryptographic
backing, and rate-limit replays. Submit the surviving word as eight
hex characters at /garage/open and read your flag from the bench.
