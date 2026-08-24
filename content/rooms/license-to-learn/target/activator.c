/* activator: license activator for the license-to-learn lab scenario.
 * Room target only: the expected code comes out of a deliberately slow
 * naive loop, so the honest way to learn it is to break after the loop
 * with a debugger and read the value from memory, not to recompute it. */
#include <stdio.h>
#include <stdlib.h>

unsigned expected_code;

__attribute__((noinline)) unsigned slow_loop(unsigned seed)
{
    volatile unsigned v = seed;
    for (unsigned i = 0; i < 8000000u; i++) {
        v = v * 1664525u + 1013904223u + (i & 0xFu);
    }
    return v;
}

__attribute__((noinline)) void report(unsigned given)
{
    FILE *f;
    int c;
    if (given != expected_code) {
        puts("activation denied: code does not match the computed expectation");
        return;
    }
    f = fopen("/root/flag.txt", "rb");
    if (!f) {
        puts("activation accepted but flag file unavailable in this context");
        return;
    }
    puts("=== ACTIVATION ACCEPTED ===");
    while ((c = fgetc(f)) != EOF && c != '\n') {
        putchar(c);
    }
    putchar('\n');
    fclose(f);
}

int main(int argc, char **argv)
{
    unsigned given;
    char *end = NULL;

    if (argc != 2) {
        printf("usage: %s <numeric activation code>\n", argv[0]);
        return 1;
    }
    expected_code = slow_loop(20260824u);
    given = strtoul(argv[1], &end, 10);
    if (end == argv[1] || *end != '\0') {
        puts("activation denied: code must be a plain decimal number");
        return 1;
    }
    report(given);
    return 0;
}
