#!/bin/bash
################################################################################
# Junkbin.io - Disk Space Monitor
# Checks disk usage and sends email alerts at warning/critical thresholds.
# Designed to run via systemd timer (junkbin-disk-monitor.timer).
#
# Install: cp deployment/systemd/junkbin-disk-monitor.{service,timer} /etc/systemd/system/
#          systemctl enable --now junkbin-disk-monitor.timer
################################################################################

set -euo pipefail

WARNING_THRESHOLD=80
CRITICAL_THRESHOLD=90
ADMIN_EMAIL="${JUNKBIN_ADMIN_EMAIL:-root}"
HOSTNAME=$(hostname -f 2>/dev/null || hostname)

# Get disk usage percentage for root filesystem
USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')

if [ "$USAGE" -ge "$CRITICAL_THRESHOLD" ]; then
    SUBJECT="[CRITICAL] Junkbin.io disk usage at ${USAGE}% on ${HOSTNAME}"
    BODY="Disk usage on ${HOSTNAME} has reached ${USAGE}%, exceeding the critical threshold of ${CRITICAL_THRESHOLD}%.

Filesystem details:
$(df -h /)

Docker disk usage:
$(docker system df 2>/dev/null || echo 'Docker not available')

Largest directories under /var/lib/docker:
$(du -sh /var/lib/docker/*/ 2>/dev/null | sort -rh | head -5 || echo 'Unable to check')

Immediate action required to prevent service disruption."

    echo "$BODY" | mail -s "$SUBJECT" "$ADMIN_EMAIL" 2>/dev/null || \
        echo "$SUBJECT" >&2
    logger -t junkbin-disk-monitor "CRITICAL: disk usage at ${USAGE}%"

elif [ "$USAGE" -ge "$WARNING_THRESHOLD" ]; then
    SUBJECT="[WARNING] Junkbin.io disk usage at ${USAGE}% on ${HOSTNAME}"
    BODY="Disk usage on ${HOSTNAME} has reached ${USAGE}%, exceeding the warning threshold of ${WARNING_THRESHOLD}%.

Filesystem details:
$(df -h /)

Consider running: docker system prune -f"

    echo "$BODY" | mail -s "$SUBJECT" "$ADMIN_EMAIL" 2>/dev/null || \
        echo "$SUBJECT" >&2
    logger -t junkbin-disk-monitor "WARNING: disk usage at ${USAGE}%"
fi
