namesim_query toolkit
=====================

This folder holds the learner client for the name-resolution room.
Everything here is a simulation: the responder on 127.0.0.1 is a plain
Python UDP logger, and captured blobs are labeled fakes.

Usage:

python3 namesim_query.py --proto llmnr --name FILESRV01
python3 namesim_query.py --proto nbtns --name PRINTSVR02

Real Windows clients fall back to LLMNR and NBT-NS broadcasts when DNS
fails, which is exactly the window a poisoning responder waits for.
Here the same idea plays out on loopback: when you query a name the
responder has been told to answer for, it claims the name and returns
a simulated credential blob, then records the capture in its log.

Which name should you try? Read /srv/public/network-inventory.txt; it
is the simulated site inventory, and it hints at the legacy file server
that clients in this scenario still resolve by bare name.

The responder writes two logs:

/var/log/responder-sim/queries.log every query it observed
/srv/public/responder-capture.log successful captures only

The capture log under /srv/public stands in for the SMB share an
attacker-facing responder would expose. When your query draws a reply,
copy the SIM-HASH value and submit it to the checker web page on port
8000 of this box.
