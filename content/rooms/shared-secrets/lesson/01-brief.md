# Shared Secrets

The learner account on this box can read an old handoff note that
should have been shredded with the tape library it describes. The note
records the password of svc_backup, a backup job identity that was
supposed to be retired in 2025. Nobody wrote down which other accounts
might still answer to that same string, and that omission is the
whole room. Password reuse does not announce itself in any config
file; you find it by trying recovered credentials against accounts
that look unrelated.

## What you will practice

- Enumerating local accounts like an investigator rather than a
  tourist. `/etc/passwd` lists every identity on the box, and the
  shell field is the fastest triage signal: `/usr/sbin/nologin` marks
  service accounts that cannot open a session, while `/bin/bash`
  marks identities worth testing. Here that separates svc_backup from
  archivist, uid 1100, the records custodian.
- Using su to test credential reuse across identities. `su -
archivist -c '...'` asks for archivist's password, and the stale
  backup string opens her session. One recovered secret has now
  crossed from a retired service account to a human data custodian,
  which is exactly how real incidents spread after a single leak.
- Reading file permissions as an access boundary. The flag lives at
  /var/archives/flag.txt with mode 0640 owned by archivist. As
  learner you can see it exists and cannot read a byte; only after
  the reuse chain lands you in the right identity does it open.

## An honest note about scale

In production networks this technique usually spans machines: a
password scraped from an SMB share or an NFS-exported home directory
works on a jump host two subnets away, and every hop looks innocent
on its own. This lab compresses the whole chain into one container so
the harness stays simple and nothing leaves the box. The mechanism
you practice here, recover, enumerate, retry elsewhere, transfers
unchanged to multi-host pivoting later in your track.

## Scope

Only `ssh://target:22` is in scope, with the learner and archivist
accounts inside this lab container. Every credential here is
fictional. The lesson to carry home is procedural: treat any
recovered password as live until proven otherwise, and audit for
reuse whenever a rotation retires anything.
