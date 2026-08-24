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

# Simulated token store (stands in for a Windows token cache).
COPY tokens /usr/local/share/token-gesture/tokens
RUN chown -R root:root /usr/local/share/token-gesture \
 && chmod 755 /usr/local/share/token-gesture/tokens \
 && chmod 644 /usr/local/share/token-gesture/tokens/* \
 && mkdir -p /opt/tokens \
 # The runtime cache is the planted flaw: any local account can drop
 # files into it, and the root helper trusts what it finds there.
 && mkdir -p /var/cache/tokentool \
 && chmod 777 /var/cache/tokentool

# Root helper with the single sudo grant. Root-owned and not writable.
COPY tokentool /usr/local/bin/tokentool
RUN chown root:root /usr/local/bin/tokentool \
 && chmod 755 /usr/local/bin/tokentool

COPY sudoers.learner /etc/sudoers.d/learner
RUN chmod 440 /etc/sudoers.d/learner \
 && visudo -cf /etc/sudoers.d/learner

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
