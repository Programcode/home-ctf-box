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

# One overly generous grant: find, no password, as root.
COPY sudoers.learner /etc/sudoers.d/learner
RUN chmod 440 /etc/sudoers.d/learner \
 && visudo -cf /etc/sudoers.d/learner

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
