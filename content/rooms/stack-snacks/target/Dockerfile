FROM debian:bookworm-slim AS build

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 gcc libc6-dev \
 && rm -rf /var/lib/apt/lists/*

COPY snack.c /tmp/snack.c
COPY snack-vendor.c /tmp/snack-vendor.c
RUN gcc -O0 -Wall -fstack-protector-strong -fPIE -pie -Wl,-z,relro,-z,now \
        -o /tmp/snack /tmp/snack.c \
 && gcc -O0 -Wall -fstack-protector-strong -fPIE -pie -Wl,-z,relro,-z,now \
        -o /tmp/snack-vendor /tmp/snack-vendor.c


FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
      openssh-server python3 file binutils \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd /opt/challenges \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

COPY --from=build /tmp/snack /opt/challenges/snack
COPY --from=build /tmp/snack-vendor /opt/challenges/snack-vendor
RUN chown root:root /opt/challenges/snack /opt/challenges/snack-vendor \
 && chmod 755 /opt/challenges/snack /opt/challenges/snack-vendor

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22 9994
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
