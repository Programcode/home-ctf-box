# Packet Diary

Case 2026-08-19: an archive appliance on the operations segment was
found still speaking plain FTP, and one control session was captured
before the service was switched off. The capture is attached to the
case page as raw evidence. Nothing about it has been summarized or
interpreted for you; the bytes are the bytes.

## What you will practice

- Treating a pcap as a primary source. Tools that parse captures for
  you are convenient, but the skill underneath is knowing that a
  libpcap file is a small header followed by timestamped frames, and
  that TCP payload bytes sit inside those frames unencrypted.
- Reading application protocols off the wire. FTP predates encryption,
  so its control channel reads like a diary: USER, then PASS with the
  password in the open, then PORT announcing where the client will
  accept a data connection, then the transfer itself.
- Closing the loop on a finding. An investigation ends when evidence
  turns into a verified fact. Here you prove the leaked password still
  works by filing it with the report desk, which returns the case
  finding.

The password in this capture is fictional and disposable. The habit it
teaches is not: any credential that crossed a network in cleartext has
to be treated as burned, rotated, and written up.

## Scope

Only `http://target:8000` is in scope. The capture is generated inside
the target process from fixed bytes; there is no live traffic and no
real credential anywhere in the room.
