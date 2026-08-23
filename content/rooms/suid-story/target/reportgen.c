/* reportgen: fake status reporter for the SUID Story lab scenario.
 * Room target only: the --dump path is deliberately misconfigured. */
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc < 2) {
        puts("reportgen: usage: reportgen --summary | --dump");
        return 0;
    }
    if (strcmp(argv[1], "--summary") == 0) {
        puts("uptime ok, disks ok, nothing interesting to report");
        return 0;
    }
    if (strcmp(argv[1], "--dump") == 0) {
        if (setuid(0) != 0) {
            perror("reportgen: setuid");
            return 1;
        }
        fflush(stdout);
        execl("/bin/cat", "cat", "/root/flag.txt", (char *)NULL);
        perror("reportgen: execl");
        return 1;
    }
    fprintf(stderr, "reportgen: unknown option: %s\n", argv[1]);
    return 1;
}
