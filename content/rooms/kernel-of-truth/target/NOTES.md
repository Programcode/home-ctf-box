# Exploit candidate notes, appliance slice meridian-app-07

#

# Authoritative version source: GET http://<slice>:8000/api/sysinfo

# The slice reports kernel 5.4.0-42-generic. Container uname output is

# meaningless inside the virtualized slice; use the API value.

#

# Candidate A: CVE-2022-0847 ("Dirty Pipe", pipe buffer flags)

# VERDICT: not applicable.

# Reason: the vulnerable pipe_buffer.flags handling only exists from

# kernel 5.8 onward. The reported 5.4.x build predates the buggy code,

# so there is nothing to exploit here no matter how loud the headlines.

#

# Candidate B: CVE-2021-4034 (polkit pkexec argument confusion)

# VERDICT: not applicable.

# Reason: exploitation requires a setuid-root pkexec helper on disk.

# This appliance image ships without policykit entirely; dpkg -l shows

# no policykit package and /usr/bin/pkexec does not exist.

#

# Candidate C: CVE-2021-3490 (eBPF verifier bounds tracking, ALU32)

# VERDICT: applicable.

# Reason: 5.4.x sits inside the affected range for unpatched verifier

# builds, and this slice records eBPF as available with unprivileged

# BPF reachable. Exactly one candidate survives the analysis; drive

# the precompiled simulator with it:

# /usr/local/bin/exploit-sim --simulate <CVE-ID>

#

# Reminder: the simulator validates recorded conditions and prints the

# verification token. No exploit code runs anywhere in this lab.
