FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server python3 \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd learners \
 && useradd -m -s /bin/bash -G learners learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

# Simulated service database (stands in for SCM registry data).
# Root-owned, world-readable: enumerating services should never need
# privilege, only acting on what they reveal should.
COPY services.json /opt/services/services.json
RUN chown root:root /opt/services/services.json \
 && chmod 644 /opt/services/services.json \
 && mkdir -p /opt/services/bin /opt/services/updater/bin \
 && printf '%s\n' '#!/bin/sh' 'echo "$(date +%FT%T) simeventlog heartbeat"' \
      > /opt/services/bin/simeventlog.sh \
 && printf '%s\n' '#!/bin/sh' 'echo "$(date +%FT%T) nightlybackup heartbeat"' \
      > /opt/services/bin/nightlybackup.sh \
 && chown root:root /opt/services/bin/simeventlog.sh /opt/services/bin/nightlybackup.sh \
 && chmod 755 /opt/services/bin /opt/services/bin/*.sh \
 # The updater payload directory is the planted flaw: group-writable
 # while its payload executes with root privileges on every pass.
 && chown root:learners /opt/services/updater /opt/services/updater/bin \
 && chmod 755 /opt/services/updater \
 && chmod 775 /opt/services/updater/bin

COPY service-runner.sh /usr/local/sbin/service-runner.sh
RUN chown root:root /usr/local/sbin/service-runner.sh \
 && chmod 700 /usr/local/sbin/service-runner.sh

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
