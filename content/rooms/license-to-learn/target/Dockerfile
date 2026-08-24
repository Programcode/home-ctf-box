FROM debian:bookworm-slim AS build

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 gcc libc6-dev \
 && rm -rf /var/lib/apt/lists/*

COPY activator.c /tmp/activator.c
RUN gcc -O0 -Wall -o /tmp/activator /tmp/activator.c


FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
      openssh-server python3 file binutils gdb \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd /opt/challenges \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

COPY --from=build /tmp/activator /opt/challenges/activator
COPY cheatsheet.gdb /opt/challenges/cheatsheet.gdb
RUN chown root:root /opt/challenges/activator /opt/challenges/cheatsheet.gdb \
 && chmod 4755 /opt/challenges/activator \
 && chmod 644 /opt/challenges/cheatsheet.gdb

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
