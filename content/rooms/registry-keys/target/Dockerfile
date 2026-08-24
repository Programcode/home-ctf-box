FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server python3 \
 && rm -rf /var/lib/apt/lists/*

# Two unprivileged accounts: the starting learner and the
# administrator-sim whose credentials leak through the simulated hive.
RUN useradd -m -s /bin/bash learner \
 && echo 'learner:learner' | chpasswd \
 && useradd -m -s /bin/bash adminsim \
 && echo 'adminsim:RustyLantern26' | chpasswd \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

# Simulated registry: plain-text .hiv files under an explicit
# /opt/registry root. Nothing here parses real binary hive formats;
# the layout teaches structure, not file-format forensics.
COPY registry/ /opt/registry/
RUN chown -R root:root /opt/registry \
 && find /opt/registry -type d -exec chmod 755 {} + \
 && find /opt/registry -type f -exec chmod 644 {} +

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
