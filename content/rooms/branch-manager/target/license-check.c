/* license-check: license portal for the branch-manager lab scenario.
 * Room target only: the advertised master key constant was corrupted at
 * build time so the obvious comparison can never succeed; the live path
 * into grant_license is guarded by three constants that only appear in
 * the disassembly dump shipped alongside this binary. */
#include <stdio.h>
#include <string.h>

#define KEY_LEN   20
#define KEY_SUM   1909u
#define KEY_FIRST 0x42u

__attribute__((noinline)) static unsigned key_checksum(const char *k)
{
    unsigned s = 0;
    while (*k) {
        s += (unsigned char)*k++;
    }
    return s;
}

/* The vendor bulletin advertises BMGR-LIFETIME-2026. The constant this
 * comparison uses was mangled when the build was signed, so it matches
 * nothing a user can type. */
__attribute__((noinline)) static int corrupt_compare(const char *k)
{
    return strcmp(k, "BMGR-LIFETIME-202\007") == 0;
}

__attribute__((noinline)) static int verify_key(const char *k)
{
    size_t n = strlen(k);
    if (n != KEY_LEN) {
        return 0;
    }
    if (key_checksum(k) != KEY_SUM) {
        return 0;
    }
    if ((unsigned char)k[0] != KEY_FIRST) {
        return 0;
    }
    return 1;
}

__attribute__((noinline)) static void grant_license(void)
{
    FILE *f = fopen("/root/flag.txt", "rb");
    int c;
    if (!f) {
        puts("license granted but flag file missing");
        return;
    }
    puts("=== LICENSE GRANTED ===");
    while ((c = fgetc(f)) != EOF && c != '\n') {
        putchar(c);
    }
    putchar('\n');
    fclose(f);
}

int main(void)
{
    char buf[128];
    printf("branch-manager license portal\n");
    printf("vendor bulletin: master keys look like BMGR-LIFETIME-2026\n");
    printf("enter key: ");
    fflush(stdout);
    if (!fgets(buf, sizeof buf, stdin)) {
        return 1;
    }
    buf[strcspn(buf, "\r\n")] = '\0';
    if (corrupt_compare(buf) || verify_key(buf)) {
        grant_license();
    } else {
        puts("license denied: key rejected by verifier");
    }
    return 0;
}
