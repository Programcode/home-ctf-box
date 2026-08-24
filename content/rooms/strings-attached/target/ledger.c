/* ledger: bookkeeping helper for the strings-attached lab scenario.
 * Room target only: --export-secrets is an undocumented mode that XORs
 * the flag with a fixed byte and prints the result as hex. */
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define EXPORT_KEY 0x5A

static const char *KEY_NOTE =
    "ledger export cipher: single-byte xor, key byte 0x5A";

int main(int argc, char **argv)
{
    if (argc < 2) {
        puts("ledger: usage: ledger [--balance] [--accounts]");
        return 0;
    }
    if (strcmp(argv[1], "--balance") == 0) {
        puts("balance: 3 florins, 12 groats, 1 suspicious IOU");
        return 0;
    }
    if (strcmp(argv[1], "--accounts") == 0) {
        puts("accounts: petty-cash, travel, misc");
        return 0;
    }
    if (strcmp(argv[1], "--export-secrets") == 0) {
        unsigned char blob[256];
        size_t n = 0;
        int c;
        FILE *f;
        if (geteuid() != 0) {
            puts("ledger: export requires the privileged build of this tool");
            return 1;
        }
        f = fopen("/root/flag.txt", "rb");
        if (!f) {
            puts("ledger: no secret ledger found");
            return 1;
        }
        while (n < sizeof blob && (c = fgetc(f)) != EOF && c != '\n' && c != '\r') {
            blob[n++] = (unsigned char)c;
        }
        fclose(f);
        printf("export-key=0x%02X\n", EXPORT_KEY);
        printf("secret-blob:");
        for (size_t i = 0; i < n; i++) {
            printf(" %02x", blob[i] ^ EXPORT_KEY);
        }
        printf("\n");
        return 0;
    }
    fprintf(stderr, "ledger: unknown option: %s\n", argv[1]);
    return 1;
}
