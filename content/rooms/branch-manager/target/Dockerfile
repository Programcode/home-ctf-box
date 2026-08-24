FROM debian:bookworm-slim AS build

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 gcc libc6-dev binutils \
 && rm -rf /var/lib/apt/lists/*

COPY license-check.c /tmp/license-check.c
RUN gcc -O0 -Wall -o /tmp/license-check /tmp/license-check.c \
 && objdump -d /tmp/license-check > /tmp/notes.asm


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

COPY --from=build /tmp/license-check /opt/challenges/license-check
COPY --from=build /tmp/notes.asm /opt/challenges/notes.asm
RUN chown root:root /opt/challenges/license-check /opt/challenges/notes.asm \
 && chmod 4755 /opt/challenges/license-check \
 && chmod 644 /opt/challenges/notes.asm

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
