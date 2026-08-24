# Brief: command injection at low security

This room wraps the real Damn Vulnerable Web Application, published by
its maintainers as a container image and paired with the MariaDB service
their own compose file declares. Nothing was changed inside either
container. You get DVWA on port 80 of the `target` host.

## Why this matters

Command injection happens when an application passes user input to a
system shell. DVWA's Command Injection level is the classic sandbox for
seeing the failure mode up close: the page pings an IP you type, and the
string you type reaches that shell with no filtering at low security.

## Your path

1. Wait a moment after start, then open `http://target/setup.php` and
   press Create / Reset Database. A fresh database needs this once.
2. Sign in as `admin` with password `password`.
3. Open DVWA Security, set it to low, and submit.
4. Open the Command Injection level from the left menu.
5. Enter an IP followed by a shell separator and a second command.
6. The results block prints ping output and then your command's output.

## Answer convention

DVWA cannot host platform-injected flags, so this room validates a fixed
public artifact: the word your injected command makes the server print.
Complete the level through the app's own form and submit that word.

Credit: DVWA is maintained by digininja and contributors under GPL-3.0,
published as an official container image. This room references those
images and adds original lesson text around them.
