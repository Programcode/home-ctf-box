#!/bin/sh
# Application supervisor: applies the environment config on a fixed cadence.
# Runs as root, started by the room entrypoint.
LOG=/var/log/app-runner.log

echo "[app-runner] supervisor starting" >> "$LOG"
while :; do
    . /etc/app/env
    echo "[app-runner] applied /etc/app/env" >> "$LOG"
    sleep 30
done
