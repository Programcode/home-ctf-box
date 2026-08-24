/* snack: stack-layout demonstrator for the stack-snacks lab scenario.
 * Room target only: reads far more input than its buffer holds. Built
 * WITH modern mitigations on purpose (stack canary, NX, PIE), so
 * control-flow hijack is out of reach; the exercise is measuring where
 * the guard sits by feeding patterns of increasing length. */
#include <stdio.h>
#include <unistd.h>

int main(void)
{
    char buf[64];
    ssize_t n;

    setvbuf(stdout, NULL, _IONBF, 0);
    puts("snack bar open. today's pastry is 64 bytes deep.");
    n = read(0, buf, 256);
    if (n < 0) {
        puts("kitchen error");
        return 1;
    }
    printf("devoured %zd bytes without complaint\n", n);
    return 0;
}
