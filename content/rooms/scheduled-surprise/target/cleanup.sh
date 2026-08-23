#!/bin/sh
# Routine housekeeping run by root's cron job every minute.
rm -rf /tmp/cache-* 2>/dev/null || true
exit 0
