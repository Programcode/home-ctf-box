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

COPY sysinfo.py /usr/local/bin/sysinfo
COPY exploit_checker.py /usr/local/bin/exploit-checker
COPY CANDIDATES.txt preconditions.conf /home/learner/lab/
COPY sudoers.learner /etc/sudoers.d/learner

RUN chmod 0755 /usr/local/bin/sysinfo /usr/local/bin/exploit-checker \
 && chown -R root:root /home/learner/lab \
 && chmod 0755 /home/learner/lab \
 && chmod 0644 /home/learner/lab/CANDIDATES.txt \
 && chown learner:learner /home/learner/lab/preconditions.conf \
 && chmod 0644 /home/learner/lab/preconditions.conf \
 && chown root:root /etc/sudoers.d/learner \
 && chmod 440 /etc/sudoers.d/learner \
 && visudo -cf /etc/sudoers.d/learner \
 && mkdir -p /etc/lab

COPY lab-kernel-release /etc/lab/kernel-release
RUN chmod 0444 /etc/lab/kernel-release

COPY entrypoint.py /usr/local/bin/entrypoint.py
RUN chmod 0755 /usr/local/bin/entrypoint.py

EXPOSE 22
ENTRYPOINT ["python3", "/usr/local/bin/entrypoint.py"]
