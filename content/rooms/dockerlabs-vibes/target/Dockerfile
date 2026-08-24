FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server sudo python3 \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash learner \
 && echo 'learner:learner' | chpasswd \
 && groupadd docker \
 && usermod -aG docker learner \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

COPY dockersim.py /usr/local/bin/dockersim
COPY API.md /usr/share/doc/dockersim/API.md
COPY README.first /home/learner/README.first
COPY sudoers.learner /etc/sudoers.d/learner

RUN chmod 0755 /usr/local/bin/dockersim \
 && chmod 0644 /usr/share/doc/dockersim/API.md /home/learner/README.first \
 && chown root:root /etc/sudoers.d/learner \
 && chmod 440 /etc/sudoers.d/learner \
 && visudo -cf /etc/sudoers.d/learner

COPY entrypoint.py /usr/local/bin/entrypoint.py
RUN chmod 0755 /usr/local/bin/entrypoint.py

EXPOSE 22
ENTRYPOINT ["python3", "/usr/local/bin/entrypoint.py"]
