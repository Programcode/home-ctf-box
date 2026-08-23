#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

/*
 * Lab helper: wraps nightly config archiving. Runs with full root
 * credentials (real and effective) so the archive step can traverse
 * everything it needs.
 */
int main(void)
{
    if (setuid(0) != 0) {
        fprintf(stderr, "[backupctl] cannot promote to root\n");
        return 1;
    }
    printf("[backupctl] archiving /etc\n");
    fflush(stdout);
    int rc = system("tar -czf /var/backups/etc-backup.tar.gz /etc 2>/dev/null");
    if (rc != 0) {
        fprintf(stderr, "[backupctl] archive step failed\n");
        return 1;
    }
    printf("[backupctl] wrote /var/backups/etc-backup.tar.gz\n");
    return 0;
}
