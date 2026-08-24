FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# Real PowerShell 7 (LTS) from the Microsoft package repo; everything
# Windows-flavored beyond pwsh is provided by the entrypoint as a
# clearly labeled simulation.
RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
      wget ca-certificates openssh-server python3 \
 && mkdir -p /etc/apt/keyrings \
 && wget -qO /etc/apt/keyrings/microsoft.asc https://packages.microsoft.com/keys/microsoft.asc \
 && printf 'deb [signed-by=/etc/apt/keyrings/microsoft.asc arch=amd64] https://packages.microsoft.com/debian/12/prod bookworm main\n' \
      > /etc/apt/sources.list.d/microsoft.list \
 && apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends powershell-lts \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /usr/bin/pwsh learner \
 && echo 'learner:learner' | chpasswd \
 && printf '/usr/bin/pwsh\n' >> /etc/shells \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

# Place the all-users profile next to the pwsh binary, wherever the
# package put it (7, 7-lts, ...).
COPY profile.ps1 /tmp/profile.ps1
RUN install -D -m 0644 /tmp/profile.ps1 \
      "$(dirname "$(readlink -f /usr/bin/pwsh)")/profile.ps1" \
 && rm /tmp/profile.ps1

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
