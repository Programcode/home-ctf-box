/* ropebridge: toy ROP target for the return-address lab scenario.
 * Room target only: built with mitigations OFF (-no-pie, -fno-stack-
 * protector, NX still on so chains not shellcode are the answer) and
 * statically linked so gadget addresses never move. symbols.txt and
 * dump.asm are captured at build time, before the binary was stripped. */
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

#define WIN_MAGIC 0xdeadbeefUL

__attribute__((noinline)) void gadget_pop_rdi_ret(void)
{
    __asm__ volatile("pop %rdi\n\tret");
}

__attribute__((noinline)) void gadget_ret(void)
{
    __asm__ volatile("ret");
}

__attribute__((noinline)) void win(unsigned long magic)
{
    char flagbuf[128];
    ssize_t n;
    int fd;

    if (magic != WIN_MAGIC) {
        puts("wrong magic offered to the summit");
        return;
    }
    fd = open("/root/flag.txt", O_RDONLY);
    if (fd < 0) {
        puts("summit reached but flag file unavailable in this context");
        return;
    }
    n = read(fd, flagbuf, sizeof flagbuf - 1);
    if (n > 0) {
        while (n > 0 && (flagbuf[n - 1] == '\n' || flagbuf[n - 1] == '\r')) {
            n--;
        }
        flagbuf[n] = '\0';
        printf("=== SUMMIT REACHED ===\n%s\n", flagbuf);
    }
    close(fd);
}

/* Kept in a helper so climb()'s frame holds nothing but buf[64]:
 * the distance from buffer start to saved return address is then
 * exactly depth + 8 on this toolchain, which the lesson teaches. */
__attribute__((noinline)) static void drain(char *buf)
{
    size_t off = 0;
    ssize_t n;

    while (off < 256) {
        n = read(0, buf + off, 256 - off);
        if (n <= 0) {
            break;
        }
        off += (size_t)n;
    }
}

__attribute__((noinline)) void climb(void)
{
    char buf[64];

    setvbuf(stdout, NULL, _IONBF, 0);
    puts("ropebridge basecamp. the order buffer is 64 bytes deep.");
    drain(buf);
}

int main(void)
{
    climb();
    puts("basecamp closed.");
    return 0;
}
