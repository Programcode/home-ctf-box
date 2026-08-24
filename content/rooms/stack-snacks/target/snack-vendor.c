/* snack-vendor: kiosk service for the stack-snacks lab scenario.
 * Room target only: order lines are passed to fprintf as a format
 * string (the deliberate bug), while the quiz endpoint validates that
 * the learner leaked this process's real stack canary and knows the
 * buffer offset. The process runs as root just long enough to pin an
 * open descriptor on the flag file, then drops to the learner account,
 * so even a full printf primitive stays unprivileged. */
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>

#define PORT 9994
#define BUF 64

static uintptr_t vendor_canary;
static int flag_fd = -1;

static uintptr_t read_canary(void)
{
    uintptr_t v;
    __asm__ volatile("mov %%fs:0x28, %0" : "=r"(v));
    return v;
}

static void emit_flag(FILE *out)
{
    char flagbuf[128];
    ssize_t n;

    if (flag_fd < 0) {
        fputs("vendor cannot serve the prize right now\n", out);
        return;
    }
    n = pread(flag_fd, flagbuf, sizeof flagbuf - 1, 0);
    if (n <= 0) {
        fputs("vendor cannot serve the prize right now\n", out);
        return;
    }
    while (n > 0 && (flagbuf[n - 1] == '\n' || flagbuf[n - 1] == '\r')) {
        n--;
    }
    flagbuf[n] = '\0';
    fprintf(out, "prize: %s\n", flagbuf);
}

static void handle(int fd)
{
    char order[BUF];
    char line[160];
    FILE *in;
    FILE *out;

    in = fdopen(fd, "r");
    if (!in) {
        close(fd);
        return;
    }
    out = fdopen(dup(fd), "w");
    if (!out) {
        fclose(in);
        close(fd);
        return;
    }
    setvbuf(out, NULL, _IOLBF, 0);
    fputs("snack-vendor kiosk ready. commands: order <text> | quiz\n", out);

    while (fgets(line, sizeof line, in)) {
        line[strcspn(line, "\r\n")] = '\0';
        if (strncmp(line, "order ", 6) == 0) {
            /* The bug: caller-controlled text used as a format string.
             * Positional %N$p verbs walk the stack frame of this
             * handler, and somewhere up there sits the canary. */
            fprintf(out, line + 6);
            fputc('\n', out);
        } else if (strcmp(line, "quiz") == 0) {
            unsigned long long guess;
            int offset;
            char *end = NULL;

            fputs("quiz question 1: submit the canary value you leaked (hex)\n", out);
            if (!fgets(line, sizeof line, in)) {
                break;
            }
            guess = strtoull(line, &end, 16);
            if (end == line || guess != vendor_canary) {
                fputs("wrong canary; quiz over. reconnect and leak again.\n", out);
                break;
            }
            fputs("quiz question 2: how many bytes from the start of the "
                  "order buffer to the canary?\n", out);
            if (!fgets(line, sizeof line, in)) {
                break;
            }
            offset = atoi(line);
            if (offset != BUF) {
                fputs("wrong offset; quiz over. reconnect and try again.\n", out);
                break;
            }
            fputs("all answers correct.\n", out);
            emit_flag(out);
            break;
        } else {
            fputs("unknown command. commands: order <text> | quiz\n", out);
        }
        fflush(out);
    }
    fflush(out);
    fclose(in);
    fclose(out);
}

int main(void)
{
    struct sockaddr_in addr;
    int server;
    int one = 1;

    signal(SIGPIPE, SIG_IGN);
    vendor_canary = read_canary();

    flag_fd = open("/root/flag.txt", O_RDONLY);
    setgid(1000);
    setuid(1000);

    server = socket(AF_INET, SOCK_STREAM, 0);
    if (server < 0) {
        perror("socket");
        return 1;
    }
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(PORT);
    if (bind(server, (struct sockaddr *)&addr, sizeof addr) < 0 ||
        listen(server, 8) < 0) {
        perror("bind/listen");
        return 1;
    }

    for (;;) {
        int client = accept(server, NULL, NULL);
        if (client < 0) {
            continue;
        }
        handle(client);
        close(client);
    }
}
