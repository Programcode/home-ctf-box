# Threat Hunt Northstar

Threat hunting starts before an alert exists. A hunter holds a
hypothesis, usually a behavior pattern attackers cannot easily avoid,
and goes looking for it across whatever telemetry the org already
collects. The discipline is pivot-driven: one finding earns you a new
filter value, and each filter you apply to the next source either kills
the hypothesis or walks you deeper. This room runs that loop five times
against three synchronized sources, and the chain structure matters as
much as any single answer.

Authentication logs carry the entry story. Service accounts are prime
targets because they authenticate non-interactively, often with static
credentials, and their failures rarely alarm anyone. A burst of failed
attempts that shifts from reason=password to reason=mfa is the
signature of password spraying followed by push fatigue, where the
attacker stops guessing and starts hoping someone approves a prompt.
The successful login from an external address, immediately followed by
a vpn assignment event, converts an account compromise into a foothold
you can follow into other sources.

Proxy and DNS logs then split the attacker's behavior into its two
halves: moving data and staying alive. Staging infrastructure serves
human-shaped requests, a download then one large upload, while command
and control needs rhythm, so beacons repeat identical requests at fixed
intervals no matter how innocuous each request looks. DNS tunneling
moves the exfiltration channel itself into query names, hiding payload
chunks in high-entropy labels under a parent domain the attacker
controls. Timing regularity and label entropy are both things you can
compute from raw logs, which is exactly what you will do here.

By the final stage you will have tied account, address, workstation,
staging host, tunnel domain, and beacon together into one incident
narrative, which is the deliverable a real hunt produces.

## Simulation disclosure

All three log sources are deterministic synthetic strings served by the
room's Flask target. Hostnames, addresses, accounts, and timestamps are
fictional; no live traffic, real credentials, or actual malware is
involved. The /hunt endpoint tracks your stage in memory and compares
answers to constants.

## What you will practice

- Forming hypotheses and pivoting between authentication, proxy, and DNS evidence.
- Reading failure bursts and mfa fatigue patterns as initial access signals.
- Separating staging uploads from beaconing using request shape and interval math.

## Scope

Only the hunt desk at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
