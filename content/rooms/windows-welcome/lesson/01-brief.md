# windows-welcome

Every Windows administrator lives in PowerShell, so the Windows track
starts there. On this box you log in over SSH and land directly in a
PowerShell session instead of a bash prompt. From the first keystroke
you can run Get-Command, Get-Help, Get-ChildItem, and Select-String,
and everything they tell you is true about the shell you are using.
The room exists to build two habits at once: reading what the shell
tells you before guessing, and asking which parts of an environment
are real before you trust them. Both habits transfer straight to real
Windows work later in the track, where the same cmdlets drive Active
Directory, services, and the registry through different providers.
Take the time to actually run each command in this room rather than
reading past it. Muscle memory formed on cheap rooms is what carries
you through timed assessments, and the four cmdlets here account for
most day-to-day navigation a Windows admin does in a terminal.

## What is real here, and what is simulated

This deserves plain language up front. The platform runs Linux
containers only, so there is no Windows kernel anywhere in this lab.
What you are connected to is a Debian container with genuine
PowerShell 7 installed from Microsoft's own package repository. The
shell, its parser, its pipeline, its error messages, and its help
system are all real. What is simulated is everything around the
shell: $env:COMPUTERNAME reads WIN-SIM01 because a profile script sets
it, and the C: drive is a folder tree at ~/winfs that imitates
C:\ProgramData, C:\Users, and C:\Windows. No registry hive loads, no
Active Directory domain exists, and nothing here talks to a real
Windows machine. When a later room needs those pieces it will simulate
them just as visibly and label them just as clearly. Treat the shell
as ground truth and the scenery as labeled props, and this room gives
you honest practice rather than pretend Windows.

## The four cmdlets you will live on

Get-Command answers existence questions. Hand it a name or a wildcard
and it reports every command that matches, including cmdlets,
functions, and external executables. When you wonder whether
something like Select-String exists or how else it might be spelled,
ask the shell instead of a search engine. Get-Help explains any of
those commands in depth, and adding -Examples shows copied-paste
style usage, which is usually the fastest way to learn correct
syntax. Get-ChildItem enumerates whatever a path contains, files and
folders alike, and its -Recurse switch walks an entire subtree in one
call, which turns "search everywhere" into a single short line.
Select-String then filters content: point it at files or pipe objects
into it, give it a pattern, and it prints the matching lines together
with the file and line number they came from. Chaining the last two
through the pipeline, listing files then filtering their contents, is
the single most useful navigation pattern on any Windows box you
will ever touch.

## Your hunt for the flag

The task sounds modest because it is: one file somewhere under the
simulated Users tree holds the flag, and your job is to find it with
the tools above rather than opening folders one by one. Start by
listing the top of ~/winfs so the layout stops being abstract, then
let Get-ChildItem -Recurse enumerate every profile at once. The
resulting object stream feeds Select-String cleanly, and a
case-sensitive pattern keeps you from matching the English word that
litters ordinary prose. Expect exactly one hit when you search
correctly; if you see many, tighten the pattern, and if you see none,
check that you included -File and pointed at the right root. This
loop, wide enumeration followed by targeted content filtering, is the
same loop you would run hunting configuration mistakes on a real
file server. The flag value itself follows the platform format and is
what you submit for credit once the search prints it.

## Scope

Stay on ssh://target:22 with the learner account you were given.
Nothing outside your own lab instance is a target, and the container
has no route to the internet, the host, or other labs anyway. The
account owns its home directory and nothing privileged hides inside
it; this room involves no elevation at all, by design. Credentials in
these rooms are disposable labels shared by every instance of the
lab, so never reuse them on systems that matter, and never point
reconnaissance tooling at networks you do not own. If an exercise
ever seems to require leaving the declared scope, stop and reread the
prompt, because the intended path always fits inside the boundary the
room declares. That discipline matters more on the Windows track than
almost anywhere else, since production Windows networks punish casual
enumeration far more loudly than a training container ever will.
