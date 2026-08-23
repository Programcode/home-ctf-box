FROM debian:bookworm-slim AS build

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 gcc libc6-dev \
 && rm -rf /var/lib/apt/lists/*

COPY jailctl.c /tmp/jailctl.c
RUN gcc -static -O2 -Wall -s -o /tmp/jailctl /tmp/jailctl.c


FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends -o Acquire::Retries=5 openssh-server python3 busybox-static \
 && rm -rf /var/lib/apt/lists/*

# Learner's login shell is the jail helper itself, so every SSH session
# starts inside the chroot sandbox.
RUN useradd -m -s /usr/local/bin/jailctl learner \
 && echo 'learner:learner' | chpasswd \
 && mkdir /run/sshd \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
      > /etc/ssh/sshd_config.d/lab.conf \
 && sed -i 's/^session\s*required\s*pam_loginuid.so/session optional pam_loginuid.so/' /etc/pam.d/sshd

COPY --from=build /tmp/jailctl /usr/local/bin/jailctl
RUN chown root:root /usr/local/bin/jailctl \
 && chmod 4755 /usr/local/bin/jailctl

# Populate the jail: static busybox plus applets, minimal etc, writable tmp,
# a second copy of the helper (SUID), device nodes, learner home.
RUN mkdir -p /jail/bin /jail/etc /jail/home/learner /jail/tmp /jail/usr/local/bin /jail/dev /jail/root \
 && cp /bin/busybox /jail/bin/busybox \
 && for t in sh ls cat mkdir cp rm mv echo id pwd touch grep vi date; do ln -sf busybox "/jail/bin/$t"; done \
 && printf 'root:x:0:0:root:/root:/bin/sh\nlearner:x:1000:1000:Learner:/home/learner:/bin/sh\n' > /jail/etc/passwd \
 && printf 'root:x:0:\nlearner:x:1000:\n' > /jail/etc/group \
 && printf 'export PATH=/bin\n' > /jail/etc/profile \
 && chown -R learner:learner /jail/home/learner \
 && chmod 750 /jail/home/learner \
 && chmod 1777 /jail/tmp \
 && cp /usr/local/bin/jailctl /jail/usr/local/bin/jailctl \
 && chown root:root /jail/usr/local/bin/jailctl \
 && chmod 4755 /jail/usr/local/bin/jailctl \
 && mknod /jail/dev/null c 1 3 && chmod 666 /jail/dev/null \
 && mknod /jail/dev/zero c 1 5 && chmod 666 /jail/dev/zero \
 && mknod /jail/dev/random c 1 8 && chmod 666 /jail/dev/random \
 && mknod /jail/dev/urandom c 1 9 && chmod 666 /jail/dev/urandom \
 && mknod /jail/dev/tty c 5 0 && chmod 666 /jail/dev/tty

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
