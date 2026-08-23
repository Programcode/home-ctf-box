# path-of-least-resistance

When a privileged program calls another program by bare name, it trusts
whichever copy of that name appears first on PATH. Most of the time the
trust is deserved. On this box the learner controls one of the
directories in that search order, which makes the trust misplaced.

## What you will practice

- Enumerating SUID binaries and separating stock Debian entries from
  locally added ones.
- Confirming, without source code, how a compiled helper invokes
  external commands.
- Preparing a writable directory, placing a stand-in executable in it,
  and controlling PATH for a single run.

## The scenario

The ops team wrote backupctl so anyone could trigger nightly config
archiving. It carries the SUID bit because the archive step needs root,
and it shells out to `tar -czf ...` with no absolute path. Your home
directory has a bin directory convention going for it: Debian's default
.profile prepends $HOME/bin to PATH whenever that directory exists.

## How to work it

Find the helper first, then prove to yourself how it resolves tar.
strings prints embedded shell lines from compiled binaries. Build your
own tar script that reads exactly one file, /root/flag.txt, put it
somewhere you control, and run the helper once with your directory
ahead on PATH. Submit the FLAG value the run prints.

## Scope

Only the box at `ssh://target:22` is in scope. Nothing outside your lab
instance is a target. Log in as learner with password learner. The
hijacked lookup affects only this container.
