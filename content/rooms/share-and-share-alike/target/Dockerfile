FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# Real smbd provides the share mechanics; the tiny Flask mirror makes
# them reachable from workstations without an SMB client.
RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
      samba python3 python3-flask \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd sharegrp \
 && useradd -M -s /usr/sbin/nologin shareweb \
 && useradd -M -s /usr/sbin/nologin smbuser \
 && usermod -aG sharegrp shareweb \
 && usermod -aG sharegrp smbuser \
 && echo 'smbuser:SpringSim26' | chpasswd \
 && mkdir -p /var/log/samba /run/samba

COPY smb.conf /etc/samba/smb.conf
COPY app.py /opt/shareweb/app.py
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 8000 445
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
