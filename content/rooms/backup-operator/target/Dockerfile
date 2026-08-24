FROM debian:bookworm-slim AS build

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 gcc libc6-dev \
 && rm -rf /var/lib/apt/lists/*

COPY disk-shadow-sim.c /tmp/disk-shadow-sim.c
RUN gcc -O2 -Wall -s -o /tmp/disk-shadow-sim /tmp/disk-shadow-sim.c


FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server python3 \
 && rm -rf /var/lib/apt/lists/*

# debian:bookworm-slim already ships a system 'backup' group; join it.
RUN useradd -m -s /bin/bash learner \
 && usermod -aG backup learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

# The SeBackupPrivilege stand-in: root-owned, executable only by backup.
COPY --from=build /tmp/disk-shadow-sim /usr/local/bin/disk-shadow-sim
RUN chown root:backup /usr/local/bin/disk-shadow-sim \
 && chmod 4750 /usr/local/bin/disk-shadow-sim

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
