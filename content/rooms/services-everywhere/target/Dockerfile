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

COPY ftp_sim.py manager_sim.py /opt/services-everywhere/
COPY entrypoint.py /usr/local/bin/entrypoint.py
RUN chmod 0755 /usr/local/bin/entrypoint.py /opt/services-everywhere/*.py \
 && useradd -r -s /usr/sbin/nologin svcdrop \
 && mkdir -p /srv/ftpd/pub /opt/tomcat-sim/webapps \
 && chown -R svcdrop:svcdrop /srv/ftpd /opt/tomcat-sim /opt/services-everywhere

EXPOSE 22 2121 8080
ENTRYPOINT ["python3", "/usr/local/bin/entrypoint.py"]
