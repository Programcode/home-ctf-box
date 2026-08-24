# share-and-share-alike

File shares are the circulatory system of a Windows network: user
drives, team repositories, software drops, all of it moves over SMB.
On this box a genuine Samba server, the standard SMB implementation
for Linux, stands in for a Windows file server with two shares. The
first is public and deliberately chatty; organizations leak their own
secrets constantly through files that end up in shared spaces nobody
audits. The second is hidden, marked browseable=no so it never shows
up when clients enumerate the server's share list. Beginners often
believe that flag makes a share secret, so this room exists to break
that belief early: hidden shares answer perfectly well when you
address them by name, and access control is what actually protects
them. When the name and credentials are sitting in a public document,
the protection evaporates. Reading other people's meeting notes is
one of the oldest and most productive moves in network security.

## What is real here, and what is simulated

The platform runs Linux containers only, so there is no Windows file
server here, but the SMB service itself is real: Samba speaks the
same protocol Windows uses, enforces the same browseable versus valid
users semantics from its smb.conf, and serves port 445 exactly like a
Windows box would if you had a client to speak to it. What is
simulated is the surrounding fiction: the server is named SIMFILE01,
the domain is SIMDOMAIN, and the documents are stage props about a
company that does not exist. One practical concession deserves an
explicit mention because you will hit it in every lab on this track:
the workstation image ships without an SMB client, so the room adds
a small HTTP mirror that lists and serves the very same directories,
with its own credential check mirroring the dev$ share's valid users
setting. Outside the lab you would run smbclient commands instead;
this lesson shows them so the translation stays honest rather than
hidden. Nothing about the underlying lesson changes between the
protocols: names, credentials, listings, and reads work identically.

## Hidden is not protected

SMB servers publish a list of their shares to any client that asks,
and browseable=no simply removes an entry from that list. The share
itself keeps existing at its exact name, accepts connections as
usual, and applies whatever authentication rules were configured for
it. Administrators reach for the hidden flag hoping to keep a share
away from casual eyes, which works until someone learns the name,
and names travel: they appear in documentation, scripts, mapped
drives on departed employees' laptops, and yes, meeting notes. Real
security for a share comes from layered controls, correct permissions
on the share, least-privilege accounts, and secrets that live in a
credential manager rather than a text file. Notice how each of those
layers fails independently in this room's story: the share hides but
does not authenticate well, because the one account that can read it
publishes its own password next door. Defense in depth sounds abstract
until you watch three separate mistakes stack into a single breach.

## Walking the intended path

Start where any curious insider would, at the public listing, and
actually read the files instead of pattern-matching filenames. The
meeting notes gossip about the development team's working share,
give its UNC path, and then do something worse: hand over the service
account login on a line formatted like a config value. With a name
and working credentials, address the hidden share directly, exactly
as smbclient would with //SIMFILE01/dev$ outside the lab. On the
mirror that means requesting /browse/dev$/ with basic authentication;
the server checks the pair before showing anything, which is the
valid users rule wearing web clothes. The listing inside holds the
development team's deploy notes, and the release verification token
inside them is your flag. Submit that value to complete the room,
then reread the public note once more and count how many policy
lines it violates; the count is the lesson.

## Scope

Stay within http://target:8000 and, if you explore with raw
protocol tools, smb://target:445 on your own instance only. Both
shares are mounted read-only by design, so there is nothing to
deface and nothing to upload; the entire exercise is reading what a
chatty organization published about itself. Do not attempt password
guessing against the dev$ share or brute-force the mirror, since the
credentials are printed plainly in the public share and guessing
teaches nothing. The container cannot reach the internet, the host,
other labs, or the control plane, and no artifact here has value
beyond this session's flag. As always on this track, the credentials
you see are disposable labels shared across every instance of the
lab; carry none of them anywhere real, and treat every technique you
practice here as something to aim exclusively at systems you own.
