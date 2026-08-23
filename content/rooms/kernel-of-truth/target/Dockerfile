FROM debian:bookworm-slim AS build

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 gcc libc6-dev \
 && rm -rf /var/lib/apt/lists/*

COPY exploit_sim.c /tmp/exploit_sim.c
RUN gcc -O2 -Wall -s -o /tmp/exploit-sim /tmp/exploit_sim.c


FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server python3 \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

COPY --from=build /tmp/exploit-sim /usr/local/bin/exploit-sim
COPY NOTES.md /opt/exploit-sim/NOTES.md
COPY sysinfo_server.py /usr/local/lib/sysinfo_server.py
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN mkdir -p /opt/exploit-sim/conditions \
 && chown root:root /usr/local/bin/exploit-sim \
 && chmod 4755 /usr/local/bin/exploit-sim \
 && chmod 0644 /opt/exploit-sim/NOTES.md \
 && chmod 0755 /usr/local/lib/sysinfo_server.py /usr/local/bin/entrypoint.sh

EXPOSE 22 8000
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
