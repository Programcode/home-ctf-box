#!/bin/sh
# Simulated GPO task: refresh the lab cache stamp. Runs as SYSTEM-equivalent
# every 30 seconds from the policy loop.
touch /tmp/cache-refresh.stamp
