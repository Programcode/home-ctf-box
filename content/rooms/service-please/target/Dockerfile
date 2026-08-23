FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server sudo python3 procps \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

# The service script and the configuration it sources every cycle.
COPY app-runner.sh /usr/local/sbin/app-runner.sh
RUN chown root:root /usr/local/sbin/app-runner.sh \
 && chmod 755 /usr/local/sbin/app-runner.sh \
 && mkdir -p /etc/app \
 && printf '%s\n' '# Application settings sourced by /usr/local/sbin/app-runner.sh.' \
      'APP_NAME=orders-api' 'APP_ENV=production' 'APP_LOGLEVEL=info' \
      > /etc/app/env \
 && chown root:root /etc/app/env \
 && chmod 666 /etc/app/env \
 && touch /var/log/app-runner.log \
 && chmod 644 /var/log/app-runner.log

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
