FROM debian:bookworm-slim AS build

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
      gcc libc6-dev binutils \
 && rm -rf /var/lib/apt/lists/*

COPY ropebridge.c /tmp/ropebridge.c
RUN gcc -O0 -static -no-pie -fno-stack-protector -z noexecstack \
        -o /tmp/ropebridge /tmp/ropebridge.c \
 && nm -n /tmp/ropebridge | awk '$3=="win" || $3=="climb" || $3=="gadget_pop_rdi_ret" || $3=="gadget_ret" || $3=="main"' \
      > /tmp/symbols.txt \
 && for s in gadget_ret gadget_pop_rdi_ret win climb main; do \
        objdump -d /tmp/ropebridge --disassemble=$s >> /tmp/dump.asm || exit 1; \
    done \
 && strip /tmp/ropebridge


FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
      openssh-server python3 file binutils \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd /opt/challenges \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

COPY --from=build /tmp/ropebridge /opt/challenges/ropebridge
COPY --from=build /tmp/symbols.txt /opt/challenges/symbols.txt
COPY --from=build /tmp/dump.asm /opt/challenges/dump.asm
RUN chown root:root /opt/challenges/ropebridge /opt/challenges/symbols.txt /opt/challenges/dump.asm \
 && chmod 4755 /opt/challenges/ropebridge \
 && chmod 644 /opt/challenges/symbols.txt /opt/challenges/dump.asm

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
