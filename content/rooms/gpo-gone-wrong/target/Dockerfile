FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server python3 \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd gpo-editors \
 && useradd -m -s /bin/bash -G gpo-editors learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

# Simulated SYSVOL: GPO definitions read straight from the share, the way
# real policy processing does. The deployment policy defines scheduled
# tasks; one of them points into a folder the ops group can write.
COPY sysvol-sim /srv/sysvol-sim
RUN chown -R root:root /srv/sysvol-sim \
 && find /srv/sysvol-sim -type d -exec chmod 755 {} + \
 && find /srv/sysvol-sim -type f -exec chmod 644 {} +

# The scripts GPO tasks execute. audit-stamp.sh lives on a locked path;
# cache-refresh.sh sits in the group-writable ops folder.
COPY gpo-scripts /srv/gpo-scripts
COPY audit-stamp.sh /usr/local/sbin/audit-stamp.sh
RUN chown root:gpo-editors /srv/gpo-scripts \
 && chmod 775 /srv/gpo-scripts \
 && chown root:gpo-editors /srv/gpo-scripts/cache-refresh.sh \
 && chmod 775 /srv/gpo-scripts/cache-refresh.sh \
 && chmod 755 /usr/local/sbin/audit-stamp.sh

# Root-side policy loop runner.
COPY gpo-task-runner.py /usr/local/sbin/gpo-task-runner.py
RUN chmod 755 /usr/local/sbin/gpo-task-runner.py

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
