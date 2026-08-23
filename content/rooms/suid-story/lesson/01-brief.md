# suid-story

Setuid binaries run with the privileges of their owner no matter who
starts them, which is why the list of them on any system should be
short and boring. This reporting server ships one extra entry:
/usr/local/bin/reportgen, marked SUID root so it can read protected
files for its reports. Its dump mode shells out to cat on whatever path
it was pointed at, and someone repointed it at /root/flag.txt.

## What you will practice

- Sweeping the filesystem for the setuid bit with find / -perm -4000.
- Reading permission strings like -rwsr-xr-x and knowing what the s
  does at execution time.
- Probing an unfamiliar binary with harmless options first, then using
  its documented behavior against itself.

## Scope

Only the box at `ssh://target:22` is in scope. Nothing outside your lab
instance is a target. The reporter's only privileged trick is printing
one file inside this container; use that and take the flag.
