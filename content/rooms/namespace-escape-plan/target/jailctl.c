/* jailctl: training-target helper that moves a session into the /jail
 * chroot sandbox, or performs an arbitrary chroot on demand.
 *
 * Deliberate teaching flaws, mirroring real-world misconfigurations:
 *   1. The "chroot" subcommand does NOT chdir("/") after chroot(),
 *      unlike coreutils chroot. A process whose working directory sits
 *      above its new root can climb out with relative paths.
 *   2. To let chained invocations keep working across the boundary,
 *      the helper plants a setuid-root stub of itself inside every new
 *      root it enters, so the next "chroot" step regains CAP_SYS_CHROOT
 *      even though plain execs otherwise lose it.
 *
 * Training target only. Not a security tool.
 */

#define _GNU_SOURCE
#include <errno.h>
#include <grp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define JAIL_ROOT "/jail"
#define HELPER_PATH "/usr/local/bin/jailctl"
#define STUB_PATH "/.jt"

static void die(const char *what) {
    fprintf(stderr, "jailctl: %s: %s\n", what, strerror(errno));
    exit(126);
}

/* Return from elevated euid to the invoking user. Clears supplementary
 * groups and both ids so exec'd programs run unprivileged. */
static void drop_privs(void) {
    uid_t uid = getuid();
    gid_t gid = getgid();
    if (setgroups(0, NULL) != 0) {
        die("setgroups");
    }
    if (setgid(gid) != 0) {
        die("setgid");
    }
    if (setuid(uid) != 0) {
        die("setuid");
    }
}

static void enter_jail_and_exec(char *const cmd[]) {
    if (chroot(JAIL_ROOT) != 0) {
        die("chroot " JAIL_ROOT);
    }
    if (chdir("/") != 0) {
        die("chdir /");
    }
    setenv("PATH", "/bin", 1);
    drop_privs();
    execv(cmd[0], cmd);
    die("exec");
}

/* Slurp this binary's image so a privileged stub can be planted inside
 * whatever root we are about to assume. */
static char *slurp_self(const char *argv0, size_t *out_len) {
    const char *candidates[3];
    static char buf[1 << 20];
    FILE *fh = NULL;
    size_t got;

    candidates[0] = argv0 ? argv0 : "";
    candidates[1] = HELPER_PATH;
    candidates[2] = NULL;
    for (int i = 0; candidates[i] != NULL && fh == NULL; i++) {
        if (candidates[i][0] == '/') {
            fh = fopen(candidates[i], "rb");
        }
    }
    if (fh == NULL) {
        return NULL;
    }
    got = fread(buf, 1, sizeof(buf), fh);
    fclose(fh);
    *out_len = got;
    return buf;
}

static void plant_stub(char *image, size_t len) {
    FILE *out = fopen(STUB_PATH, "wb");
    if (out == NULL) {
        return; /* best effort; the direct exec may still work */
    }
    if (fwrite(image, 1, len, out) != len) {
        fclose(out);
        return;
    }
    fclose(out);
    chmod(STUB_PATH, 04755);
}

int main(int argc, char **argv) {
    int login_mode;
    login_mode = argc < 2
        || (strcmp(argv[1], "-c") != 0 && strcmp(argv[1], "chroot") != 0);

    if (login_mode) {
        /* sshd login shell: land inside the jail with an interactive sh. */
        char *cmd[] = {"/bin/busybox", "sh", NULL};
        enter_jail_and_exec(cmd);
    }

    if (strcmp(argv[1], "-c") == 0) {
        /* sshd non-interactive form: jailctl -c '<command>'. */
        char *cmd[5];
        if (argc < 3) {
            fprintf(stderr, "usage: jailctl -c COMMAND\n");
            return 2;
        }
        cmd[0] = "/bin/busybox";
        cmd[1] = "sh";
        cmd[2] = "-c";
        cmd[3] = argv[2];
        cmd[4] = NULL;
        enter_jail_and_exec(cmd);
    }

    /* Tool form: jailctl chroot NEWROOT [COMMAND...].
     *
     * Requires the elevated helper (euid 0 via setuid bit). Flaws live
     * here on purpose: no chdir("/") after chroot(), so the caller's
     * working directory ends up ABOVE the new root; and before crossing,
     * a fresh setuid stub is planted inside the new root so a follow-up
     * "chroot ." step regains the capability that plain execs lose. */
    if (geteuid() != 0) {
        fprintf(stderr, "jailctl: chroot subcommand requires the elevated helper\n");
        return 1;
    }
    if (argc < 3) {
        fprintf(stderr, "usage: jailctl chroot NEWROOT [COMMAND...]\n");
        return 2;
    }

    size_t len = 0;
    char *image = slurp_self(argc >= 1 ? argv[0] : NULL, &len);
    int as_stub = argc >= 1 && strcmp(argv[0], STUB_PATH) == 0;

    if (chroot(argv[2]) != 0) {
        die("chroot");
    }

    /* Now that the new root is active, plant the privileged stub so a
     * later "chroot ." step can regain the capability this exec chain
     * just shed. */
    if (!as_stub && image != NULL && len > 0) {
        plant_stub(image, len);
    }

    if (argc >= 4) {
        setenv("PATH", "/bin:/usr/bin", 1);
        drop_privs();
        execv(argv[3], &argv[3]);
        die("exec");
    }
    {
        char *cmd[] = {"/bin/busybox", "sh", NULL};
        setenv("PATH", "/bin", 1);
        drop_privs();
        execv(cmd[0], cmd);
    }
    die("exec");
}
