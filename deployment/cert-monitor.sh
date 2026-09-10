#!/bin/bash
################################################################################
# Junkbin.io - SSL Certificate Expiry Monitor
# Checks days-until-expiry on the live certs and sends email alerts at
# warning/critical thresholds.
# Designed to run via systemd timer (junkbin-cert-monitor.timer).
#
# This exists because a broken renewal cron let the certs expire silently in
# Sep 2026 - the renewal itself was fixed, but nothing was watching the outcome.
# It checks the served cert over TLS rather than the files on disk, so it also
# catches "renewed on disk but nginx never reloaded".
#
# Install: cp deployment/systemd/junkbin-cert-monitor.{service,timer} /etc/systemd/system/
#          systemctl enable --now junkbin-cert-monitor.timer
################################################################################

set -euo pipefail

WARNING_THRESHOLD="${CERT_WARN_DAYS:-21}"
CRITICAL_THRESHOLD="${CERT_CRIT_DAYS:-7}"
HOSTNAME=$(hostname -f 2>/dev/null || hostname)
DOMAIN="${JUNKBIN_DOMAIN:-junkbin.io}"

# Shared delivery: read_env, SMTP config, ADMIN_EMAIL resolution, alert().
ALERT_TAG=junkbin-cert-monitor
# shellcheck source=deployment/alert-lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/alert-lib.sh"

# Every hostname that must have a valid cert. A cert can renew for the apex and
# still leave a subdomain stale - they are separate lineages.
HOSTS="${JUNKBIN_CERT_HOSTS:-${DOMAIN} www.${DOMAIN} translate.${DOMAIN}}"

# Seconds until the cert served for $1 expires (negative if already expired).
# Returns non-zero if the host can't be reached. Seconds rather than days
# because bash integer division truncates toward zero: a cert that died 11
# hours ago would come back as "0 days" and never read as expired.
seconds_until_expiry() {
    local host="$1" not_after expiry_epoch now_epoch

    not_after=$(echo | timeout 15 openssl s_client -servername "$host" \
        -connect "${host}:443" 2>/dev/null \
        | openssl x509 -noout -enddate 2>/dev/null \
        | cut -d= -f2)

    # Guard with an if rather than `[ -z ... ] && return 1`: that form's exit
    # status trips errexit when the test is false.
    if [ -z "$not_after" ]; then
        return 1
    fi

    expiry_epoch=$(date -d "$not_after" +%s 2>/dev/null) || return 1
    now_epoch=$(date +%s)
    echo $(( expiry_epoch - now_epoch ))
}

# Humanise an elapsed-seconds count for the expired case. Hours matter here:
# "expired 11 hours ago" is the difference between "renewal slipped" and
# "renewal has been dead for weeks".
format_elapsed() {
    local secs="$1"
    if [ "$secs" -lt 172800 ]; then
        echo "$(( secs / 3600 )) hour(s)"
    else
        echo "$(( secs / 86400 )) day(s)"
    fi
}

RENEW_HINT="Renew manually with:
  sudo /opt/certbot/bin/certbot renew
  cd ${JUNKBIN_DIR} && docker compose -f docker-compose.yml exec -T nginx nginx -s reload

Note: /opt/certbot/bin/certbot is the venv build carrying the dns-hostinger
plugin. A bare 'certbot' resolves to the distro package, which cannot complete
the DNS challenge these certs are configured for.

Recent renewal output:
$(tail -20 "${CERT_RENEW_LOG:-/var/log/junkbin-certbot-renew.log}" 2>/dev/null || echo 'No renewal log found - the renewal cron may not be running at all.')"

for host in $HOSTS; do
    if ! DELTA=$(seconds_until_expiry "$host"); then
        alert "[CRITICAL] Junkbin.io cannot read TLS cert for ${host}" \
"Unable to retrieve a certificate from ${host}:443 on ${HOSTNAME}.

The host may be down, or TLS may be failing outright.

${RENEW_HINT}" \
            "CRITICAL: cannot read cert for ${host}" || true
        continue
    fi

    DAYS=$(( DELTA / 86400 ))

    if [ "$DELTA" -lt 0 ]; then
        ELAPSED=$(format_elapsed $(( -DELTA )))
        alert "[CRITICAL] Junkbin.io cert for ${host} EXPIRED ${ELAPSED} ago" \
"The certificate served for ${host} expired ${ELAPSED} ago.

Visitors are seeing browser security warnings right now.

${RENEW_HINT}" \
            "CRITICAL: cert for ${host} expired ${ELAPSED} ago" || true

    elif [ "$DAYS" -le "$CRITICAL_THRESHOLD" ]; then
        alert "[CRITICAL] Junkbin.io cert for ${host} expires in ${DAYS} day(s)" \
"The certificate served for ${host} expires in ${DAYS} day(s), under the critical threshold of ${CRITICAL_THRESHOLD}.

Auto-renewal should have run by now - treat it as broken until proven otherwise.

${RENEW_HINT}" \
            "CRITICAL: cert for ${host} expires in ${DAYS} days" || true

    elif [ "$DAYS" -le "$WARNING_THRESHOLD" ]; then
        alert "[WARNING] Junkbin.io cert for ${host} expires in ${DAYS} day(s)" \
"The certificate served for ${host} expires in ${DAYS} day(s), under the warning threshold of ${WARNING_THRESHOLD}.

Let's Encrypt opens the renewal window at 30 days, so a healthy setup should
already have renewed this. Check ${CERT_RENEW_LOG:-/var/log/junkbin-certbot-renew.log}.

${RENEW_HINT}" \
            "WARNING: cert for ${host} expires in ${DAYS} days" || true
    fi
done
