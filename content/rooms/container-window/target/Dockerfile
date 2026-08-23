FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server sudo python3 \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

# The simulated host filesystem. Ordinary directories inside this
# container; they play the role of an attached host for the lesson.
RUN mkdir -p /hostsim/root /hostsim/root/.ssh /hostsim/etc /hostsim/var/log /hostsim/home/deploy \
 && printf '%s\n' 'root:x:0:0:root:/root:/bin/bash' 'deploy:x:1002:1002:Deploy Bot:/home/deploy:/bin/sh' \
      > /hostsim/etc/passwd \
 && printf '%s\n' 'Mar 12 07:41:01 host CRON[5121]: (root) CMD (/usr/local/bin/snapshot-sync)' \
      'Mar 12 07:42:01 host CRON[5133]: (root) CMD (/usr/local/bin/snapshot-sync)' \
      > /hostsim/var/log/syslog \
 && printf '%s\n' 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPlaceholderKeyForLabSimulation ops@host' \
      > /hostsim/root/.ssh/authorized_keys \
 && chown -R root:root /hostsim \
 && chmod 700 /hostsim/root \
 && chmod 600 /hostsim/root/.ssh/authorized_keys \
 && chmod 644 /hostsim/etc/passwd /hostsim/var/log/syslog

# The delegated trust: one read-only introspection utility via sudo.
COPY container-inspect /usr/local/bin/container-inspect
COPY sudoers.learner /etc/sudoers.d/learner
RUN chown root:root /usr/local/bin/container-inspect /etc/sudoers.d/learner \
 && chmod 755 /usr/local/bin/container-inspect \
 && chmod 440 /etc/sudoers.d/learner \
 && visudo -cf /etc/sudoers.d/learner

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
