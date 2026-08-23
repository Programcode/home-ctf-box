FROM gcc:bookworm AS build

COPY backupctl.c /src/backupctl.c
RUN mkdir -p /out && gcc -O2 -Wall -o /out/backupctl /src/backupctl.c

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server sudo python3 tar \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

# The homegrown helper and the archive directory it writes to.
COPY --from=build /out/backupctl /usr/local/bin/backupctl
RUN chown root:root /usr/local/bin/backupctl \
 && chmod 4755 /usr/local/bin/backupctl \
 && mkdir -p /var/backups \
 && chown root:root /var/backups \
 && chmod 755 /var/backups

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
