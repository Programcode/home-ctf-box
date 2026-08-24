# APK Breadcrumbs

Every Android assessment starts the same way: get the package, unpack
it, and read what the developers shipped. This room gives you a
package desk with one archive, app.apk, and asks for the two findings
that show up in real reports more than almost anything else: a
production API endpoint nobody documented, and a debug credential that
made it into release resources.

Straight disclosure about the artifact. This APK is not from any app
store and contains no bytecode, no signing key, and no live endpoint.
The service builds it as an ordinary zip at startup with fixed
timestamps, and its classes.dex entry is a plain-text manifest that
narrates the smali control flow instead of holding dalvik code. That
swap keeps the room solvable with the Python standard library while
preserving exactly the reading order apktool and jadx would impose on
a genuine package: manifest first for identity, resources second for
values, dex last for behavior.

## What real tooling does here

Two programs dominate Android static analysis. apktool decodes an APK
into readable resources: it turns the binary XML of
AndroidManifest.xml back into text, drops every string into
res/values/strings.xml, and disassembles classes.dex into smali files.
jadx takes the other axis, decompiling dex bytecode into approximate
Java sources you can read in a GUI. Analysts run both, because
resources tell you what values exist and decompiled code tells you
which values actually matter. In this room both halves are already
text, so your zipfile listing plays apktool's role and the classes.dex
stub plays jadx's: it tells you SyncClient reads the resource named
api_base_url and DebugGate compares against debug_api_key.

That reading order matters more than it looks. Packages routinely ship
several URL-shaped strings, and grabbing the wrong one produces a
finding that falls apart under review. Here strings.xml holds two
hosts: a legacy v1 endpoint marked deprecated in the flow notes and
the v2 crumb-sync host production traffic actually uses. The stub
resolves the ambiguity, which is precisely how a decompiler resolves
it on a real target: by showing which constant the shipping code path
loads at runtime.

## From extraction to report

Unpack with `python3 -m zipfile -l app.apk`, read the entries, and
pull both values out of strings.xml with a small regex or by eye.
The verification desk wants them submitted together, because each one
alone is trivia while the pair is a finding: a hidden production
surface plus a credential that authenticates to it. When you write
this up in real life, note remediation too, since the fix pattern is
stable across teams: secrets move behind server-side distribution or a
managed config system, and debug gates compile out of release builds
entirely rather than relying on runtime checks.

Finish by submitting the exact endpoint and key to POST /verify as
form fields api_endpoint and api_key. If the desk rejects you,
re-check which host the flow notes call production before blaming
your regex. The whole exercise should take well under half an hour,
and the skill it rehearses, mapping packaged resources to runtime
behavior, transfers unchanged to genuine packages analyzed inside a
lab you are authorized to test.
