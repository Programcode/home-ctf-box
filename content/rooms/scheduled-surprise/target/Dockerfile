FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server cron python3 \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd learners \
 && useradd -m -s /bin/bash -G learners learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

# The housekeeping script root runs every minute. The file is root-owned;
# the directory below is deliberately group-writable for the ops team.
COPY cleanup.sh /usr/local/sbin/cleanup.sh
RUN chown root:root /usr/local/sbin/cleanup.sh \
 && chmod 755 /usr/local/sbin/cleanup.sh \
 && chown root:learners /usr/local/sbin \
 && chmod 775 /usr/local/sbin \
 && printf '* * * * * root /usr/local/sbin/cleanup.sh\n' > /etc/cron.d/cleanup-job \
 && chmod 644 /etc/cron.d/cleanup-job

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
