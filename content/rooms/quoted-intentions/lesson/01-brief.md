# quoted-intentions

Some of the most consequential Windows bugs were not memory
corruption or clever logic; they were punctuation. When the Service
Control Manager launches a service, it takes the binPath string from
the registry and hands it to CreateProcess. If the path contains
spaces but no surrounding quotes, CreateProcess cannot tell where the
program name ends and the arguments begin, so it resolves the string
greedily from the left: it tries an executable at every space
boundary before it ever reaches the file the administrator actually
installed. A path like C:\Program Files\Unquoted Helper\helper.exe
therefore offers an attacker who can write to C:\ a free ride to
service-account privileges, because C:\Program.exe gets attempted
first. This bug class has shipped in commercial products, made
privilege-escalation chapters for twenty years, and still turns up in
audits, all because one pair of quote characters was left out. The
whole skill in this room is internalizing that resolution algorithm
until you can reproduce it by hand.

## What is real here, and what is simulated

This is a reasoning room, and honesty about its edges keeps it
useful. There is no Windows service host here, no binary ever runs at
any of these paths, and nothing is exploited in the execution sense;
the platform only runs Linux containers, so this lab is a Flask page
on a locked-down container. What the page gives you is faithful in
the ways that matter for learning: the enumerator output mirrors sc
qc formatting, one entry carries exactly the spaces-and-no-quotes
pattern the bug class lives on, and the checker enforces the real
resolution semantics, including order, when grading your answer.
You get no credit for dumping the set of candidates in any sequence,
because on Windows the sequence is the exploit. Everything else,
writable directories, actual SYSTEM payloads, is deliberately absent
and plainly labeled simulation. Learn the algorithm here; apply it to
real enumerations later in the track where those pieces exist.

## Deriving resolution order by hand

Work the example like CreateProcess does. Take the unquoted string
and scan from the left for the first space. Everything before that
space becomes your first candidate executable once .exe is attached:
for C:\Program Files\Unquoted Helper\helper.exe that is C:\Program.exe.
If that file had existed, the story would end there and the service
would have launched it with full service privileges. It did not, so
resolution extends through the next space boundary and tries again,
producing C:\Program Files\Unquoted.exe as candidate two. Only after
every shorter prefix fails does Windows finally run the recorded path
in full, helper.exe itself, as the last candidate. Two habits fall
out of practicing this. First, you will read enumerator output and
flag unquoted paths instantly instead of skimming past them. Second,
you will know which directory matters most for each path: earlier
boundaries sit closer to the drive root, and roots are historically
where ordinary users retained write access.

## Claiming the flag

The task folds everything into one submission. Read the enumerator
page, identify the single unquoted entry among its quoted neighbors,
derive the ordered chain, and POST it as the chain field to /check,
one path per line. The checker grades strictly: wrong count, wrong
content, or wrong order each earn specific rejection messages rather
than the flag, so a mismatch tells you which mental step slipped.
When your derivation matches resolution semantics exactly, the
success page prints this session's flag value for submission. If you
want to verify your understanding beyond the graded answer, notice
what the checker refuses to do: it never accepts a reordered or
partial chain, because any real exploitation depends on attempt order
determining which binary actually executes. That strictness is the
lesson wearing a grading harness.

## Scope

Touch only http://target:8000 inside your own lab instance. The
container holds no secrets beyond this session's flag, performs no
elevation, and cannot reach the internet, the host, the control
plane, or other labs. There is genuinely nothing to attack here and
nothing to escalate; the entire exercise is deriving one ordered list
of strings and submitting it. Do not probe the checker for injection
or fuzzing opportunities, since it validates text and returns text,
and time spent there teaches nothing the room is trying to teach.
Treat rooms like this as the theory half of the track: cheap to run,
safe by construction, and most valuable when you can reproduce their
reasoning from memory on the boxes where the paths are real.
