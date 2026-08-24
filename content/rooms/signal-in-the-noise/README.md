# Signal in the Noise

Hard investigation room for RF-style artifact work with zero radios.
The case serves a raw int16 IQ capture plus a spectrum plot, both
computed in-image; the learner demodulates OOK bits by threshold,
separates a static identifier from rolling counter bits across six
repeated frames, and replays the static code at the simulated opener.
Points: 300.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` covers IQ sampling, OOK demodulation, and repetition analysis.
- `target/` builds the case desk (Flask, port 8000), stdlib-only PNG plot.
- `solver/solver.py` proves decode to replay end to end with struct alone.

No transmission or hardware exists anywhere; everything is generated
deterministically inside the container. Verify locally with
`cyberrange solve content/rooms/signal-in-the-noise`.
