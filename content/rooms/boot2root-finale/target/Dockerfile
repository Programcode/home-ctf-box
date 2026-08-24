FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server sudo python3 \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash sysop \
 && echo 'sysop:KnockFirstSync88' | chpasswd \
 && useradd -r -s /usr/sbin/nologin gatekeep \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

COPY knock_share.py /opt/gatekeeper/knock_share.py
COPY menu /opt/admin-tools/menu
COPY sudoers.sysop /etc/sudoers.d/sysop

RUN chmod 0755 /opt/gatekeeper/knock_share.py /opt/admin-tools/menu \
 && chown -R root:gatekeep /opt/gatekeeper \
 && chown root:root /etc/sudoers.d/sysop \
 && chmod 440 /etc/sudoers.d/sysop \
 && visudo -cf /etc/sudoers.d/sysop

COPY entrypoint.py /usr/local/bin/entrypoint.py
RUN chmod 0755 /usr/local/bin/entrypoint.py

EXPOSE 22 8080 4010 5011 6012
ENTRYPOINT ["python3", "/usr/local/bin/entrypoint.py"]
