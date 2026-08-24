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

COPY responder_sim.py checker.py /usr/local/bin/
RUN chown root:root /usr/local/bin/responder_sim.py /usr/local/bin/checker.py \
 && chmod 755 /usr/local/bin/responder_sim.py /usr/local/bin/checker.py \
 && mkdir -p /usr/local/share/name-resolution/tools
COPY tools/README.md tools/namesim_query.py /usr/local/share/name-resolution/tools/

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22 8000
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
