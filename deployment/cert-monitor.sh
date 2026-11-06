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
# Try:     CERT_MONITOR_DRY_RUN=1 deployment/cert-monitor.sh   (prints alerts, sends nothing)
#
# Thresholds follow each cert's own lifetime, because Let's Encrypt is shortening
# it (90 days now, 64 from Feb 2027, 45 from Feb 2028; 6-day certs exist already).
# Certbot >= 4.0 renews when a third of the lifetime is left, earlier when Let's
# Encrypt asks through ARI. A fixed "warn under 21 days" would fire on every
# healthy 45-day cert (renewed at 15 days left) and miss a 6-day cert entirely.
#   warning:  under a third of the lifetime left, less 2 days (renewal is late)
#   critical: under a sixth of the lifetime left, at most 7 days
# CERT_WARN_DAYS / CERT_CRIT_DAYS still override with fixed days.
################################################################################

set -euo pipefail

HOSTNAME=$(hostname -f 2>/dev/null || hostname)
DOMAIN="${JUNKBIN_DOMAIN:-junkbin.io}"

# Shared delivery: read_env, SMTP config, ADMIN_EMAIL resolution, alert().
ALERT_TAG=junkbin-cert-monitor
# shellcheck source=deployment/alert-lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/alert-lib.sh"

# Every hostname that must have a valid cert. A cert can renew for the apex and
# still leave a subdomain stale - they are separate lineages.
HOSTS="${JUNKBIN_CERT_HOSTS:-${DOMAIN} www.${DOMAIN} translate.${DOMAIN}}"

# "<seconds until expiry> <lifetime in seconds>" for the cert served for $1
# (expiry negative if already expired). Returns non-zero if the host can't be
# reached. Seconds rather than days because bash integer division truncates
# toward zero: a cert that died 11 hours ago would come back as "0 days" and
# never read as expired.
cert_times() {
    local host="$1" dates not_before not_after start_epoch expiry_epoch now_epoch

    dates=$(echo | timeout 15 openssl s_client -servername "$host" \
        -connect "${host}:443" 2>/dev/null \
        | openssl x509 -noout -startdate -enddate 2>/dev/null)
    not_before=$(echo "$dates" | sed -n 's/^notBefore=//p')
    not_after=$(echo "$dates" | sed -n 's/^notAfter=//p')

    # Guard with an if rather than `[ -z ... ] && return 1`: that form's exit
    # status trips errexit when the test is false.
    if [ -z "$not_after" ] || [ -z "$not_before" ]; then
        return 1
    fi

    start_epoch=$(date -d "$not_before" +%s 2>/dev/null) || return 1
    expiry_epoch=$(date -d "$not_after" +%s 2>/dev/null) || return 1
    now_epoch=$(date +%s)
    echo "$(( expiry_epoch - now_epoch )) $(( expiry_epoch - start_epoch ))"
}

# Alert thresholds in days for a cert of the given lifetime (seconds): see the header.
thresholds() {
    local lifetime_days=$(( $1 / 86400 )) warn crit
    warn=$(( lifetime_days / 3 - 2 ))
    crit=$(( lifetime_days / 6 ))
    [ "$crit" -gt 7 ] && crit=7
    [ "$crit" -lt 1 ] && crit=1
    [ "$warn" -le "$crit" ] && warn=$(( crit + 1 ))
    echo "${CERT_WARN_DAYS:-$warn} ${CERT_CRIT_DAYS:-$crit}"
}

# alert(), or just print it under CERT_MONITOR_DRY_RUN=1.
notify() {
    if [ "${CERT_MONITOR_DRY_RUN:-0}" = "1" ]; then
        printf '%s\n%s\n\n' "$1" "$2"
    else
        alert "$@"
    fi
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
    if ! TIMES=$(cert_times "$host"); then
        notify "[CRITICAL] Junkbin.io cannot read TLS cert for ${host}" \
"Unable to retrieve a certificate from ${host}:443 on ${HOSTNAME}.

The host may be down, or TLS may be failing outright.

${RENEW_HINT}" \
            "CRITICAL: cannot read cert for ${host}" || true
        continue
    fi

    read -r DELTA LIFETIME <<< "$TIMES"
    read -r WARNING_THRESHOLD CRITICAL_THRESHOLD <<< "$(thresholds "$LIFETIME")"
    DAYS=$(( DELTA / 86400 ))
    [ "${CERT_MONITOR_DRY_RUN:-0}" = "1" ] && \
        echo "${host}: ${DAYS} day(s) left of $(( LIFETIME / 86400 )); warn at ${WARNING_THRESHOLD}, critical at ${CRITICAL_THRESHOLD}"

    if [ "$DELTA" -lt 0 ]; then
        ELAPSED=$(format_elapsed $(( -DELTA )))
        notify "[CRITICAL] Junkbin.io cert for ${host} EXPIRED ${ELAPSED} ago" \
"The certificate served for ${host} expired ${ELAPSED} ago.

Visitors are seeing browser security warnings right now.

${RENEW_HINT}" \
            "CRITICAL: cert for ${host} expired ${ELAPSED} ago" || true

    elif [ "$DAYS" -le "$CRITICAL_THRESHOLD" ]; then
        notify "[CRITICAL] Junkbin.io cert for ${host} expires in ${DAYS} day(s)" \
"The certificate served for ${host} expires in ${DAYS} day(s), under the critical threshold of ${CRITICAL_THRESHOLD}.

Auto-renewal should have run by now - treat it as broken until proven otherwise.

${RENEW_HINT}" \
            "CRITICAL: cert for ${host} expires in ${DAYS} days" || true

    elif [ "$DAYS" -le "$WARNING_THRESHOLD" ]; then
        notify "[WARNING] Junkbin.io cert for ${host} expires in ${DAYS} day(s)" \
"The certificate served for ${host} expires in ${DAYS} day(s), under the warning threshold of ${WARNING_THRESHOLD}.

Certbot renews when a third of a cert's lifetime is left (sooner if Let's
Encrypt asks through ARI), so a healthy setup should already have renewed this. Check ${CERT_RENEW_LOG:-/var/log/junkbin-certbot-renew.log}.

${RENEW_HINT}" \
            "WARNING: cert for ${host} expires in ${DAYS} days" || true
    fi
done
