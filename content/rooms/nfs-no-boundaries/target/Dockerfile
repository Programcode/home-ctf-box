FROM gcc:bookworm AS build

COPY snapshot-recover.c /src/snapshot-recover.c
RUN mkdir -p /out && gcc -O2 -Wall -o /out/snapshot-recover /src/snapshot-recover.c

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server sudo cron python3 \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

# The recovery helper: built here, staged into the share by root's sync job.
COPY --from=build /out/snapshot-recover /usr/local/libexec/snapshot-recover
RUN chown root:root /usr/local/libexec/snapshot-recover \
 && chmod 755 /usr/local/libexec/snapshot-recover

# The share this lab models as a misconfigured export, and its documented line.
RUN mkdir -p /srv/share \
 && chown root:root /srv/share \
 && chmod 777 /srv/share \
 && printf '%s\n' 'Ops sync area backed by the storage host.' \
      'Client jobs pick up staged files from here.' \
      > /srv/share/README.txt \
 && chmod 644 /srv/share/README.txt

COPY exports /etc/exports
RUN chown root:root /etc/exports \
 && chmod 644 /etc/exports \
 && printf '%s\n' '*/2 * * * * root install -m 4755 -o root -g root /usr/local/libexec/snapshot-recover /srv/share/snapshot-recover' \
      > /etc/cron.d/nfs-share-sync \
 && chmod 644 /etc/cron.d/nfs-share-sync

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
