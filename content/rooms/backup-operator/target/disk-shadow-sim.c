/* disk-shadow-sim: SeBackupPrivilege emulation for the Backup Operator lab.
 * Room target only: members of group backup may stage a copy of any file
 * under /tmp, which is the entire point of the exercise. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr,
            "disk-shadow-sim: usage: disk-shadow-sim SOURCE DEST\n"
            "DEST must be a regular path under /tmp (simulated shadow copy staging)\n");
        return 2;
    }

    const char *src = argv[1];
    const char *dst = argv[2];

    if (strncmp(dst, "/tmp/", 5) != 0 || strstr(dst, "..") != NULL) {
        fprintf(stderr, "disk-shadow-sim: refused: DEST must live under /tmp/\n");
        return 2;
    }
    if (strcmp(src, dst) == 0) {
        fprintf(stderr, "disk-shadow-sim: refused: source and destination match\n");
        return 2;
    }

    if (setuid(0) != 0) {
        perror("disk-shadow-sim: setuid");
        return 1;
    }

    FILE *in = fopen(src, "rb");
    if (in == NULL) {
        fprintf(stderr, "disk-shadow-sim: cannot open %s\n", src);
        return 1;
    }
    FILE *out = fopen(dst, "wb");
    if (out == NULL) {
        fprintf(stderr, "disk-shadow-sim: cannot write %s\n", dst);
        fclose(in);
        return 1;
    }

    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), in)) > 0) {
        if (fwrite(buf, 1, n, out) != n) {
            fprintf(stderr, "disk-shadow-sim: short write to %s\n", dst);
            fclose(in);
            fclose(out);
            return 1;
        }
    }
    fclose(in);
    fclose(out);

    printf("shadow copy staged: %s -> %s\n", src, dst);
    return 0;
}
