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
JUNKBIN_DIR="${JUNKBIN_DIR:-/root/junkbin.io}"

# Load the app's SMTP credentials. The production host has no `mail` binary and
# no running MTA, so an alert sent the conventional way would land in a local
# spool nobody reads - the same silence that let the certs expire. The Django
# app already delivers through an authenticated SMTP relay, so reuse it: a local
# MTA on a cloud IP with no SPF/DKIM would mostly get spam-filtered.
# These are secrets - never echo them.
ENV_FILE="${JUNKBIN_ENV_FILE:-${JUNKBIN_DIR}/.env}"
# Read one key from the .env file, normalising the value the way docker compose
# and django-environ do. Surrounding quotes MUST be stripped: a quoted password
# handed to smtplib with the quotes still attached authenticates as the wrong
# string and fails with SMTPAuthenticationError, which looks exactly like a bad
# credential and sends you chasing the wrong problem.
read_env() {
    local v
    [ -f "$ENV_FILE" ] || return 0
    v=$(grep -E "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- || true)
    v="${v%$'\r'}"
    case "$v" in
        \"*\") v="${v#\"}"; v="${v%\"}" ;;
        \'*\') v="${v#\'}"; v="${v%\'}" ;;
    esac
    printf '%s' "$v"
}
SMTP_HOST="$(read_env EMAIL_HOST)"
SMTP_PORT="$(read_env EMAIL_PORT)"
SMTP_USER="$(read_env EMAIL_HOST_USER)"
SMTP_PASSWORD="$(read_env EMAIL_HOST_PASSWORD)"
SMTP_SSL="$(read_env EMAIL_USE_SSL)"
SMTP_PORT="${SMTP_PORT:-465}"
SMTP_SSL="${SMTP_SSL:-True}"

# Who gets alerted. Resolved from .env so the address lives in exactly one
# place on the server and never in version control - this repo is public.
# ALERT_EMAIL takes precedence and accepts a comma-separated list, so alerts can
# go somewhere a person actually reads without disturbing ADMIN_EMAIL, which the
# app and certbot registration also use. JUNKBIN_ADMIN_EMAIL still overrides
# both, for testing.
ADMIN_EMAIL="${JUNKBIN_ADMIN_EMAIL:-$(read_env ALERT_EMAIL)}"
ADMIN_EMAIL="${ADMIN_EMAIL:-$(read_env ADMIN_EMAIL)}"
ADMIN_EMAIL="${ADMIN_EMAIL:-root}"

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

# Deliver through the app's authenticated SMTP relay. ADMIN_EMAIL may be a
# comma-separated list. The password goes via the environment, not argv, which
# would otherwise be visible in `ps`.
send_smtp() {
    local subject="$1" body="$2"

    if [ -z "$SMTP_HOST" ] || [ -z "$SMTP_USER" ] || [ -z "$SMTP_PASSWORD" ]; then
        return 1
    fi

    SUBJECT="$subject" BODY="$body" MAIL_TO="$ADMIN_EMAIL" \
    SMTP_HOST="$SMTP_HOST" SMTP_PORT="$SMTP_PORT" SMTP_USER="$SMTP_USER" \
    SMTP_PASSWORD="$SMTP_PASSWORD" SMTP_SSL="$SMTP_SSL" \
    python3 -c '
import os, smtplib, ssl, sys
from email.message import EmailMessage

recipients = [a.strip() for a in os.environ["MAIL_TO"].split(",") if a.strip()]
msg = EmailMessage()
msg["Subject"] = os.environ["SUBJECT"]
msg["From"] = os.environ["SMTP_USER"]
msg["To"] = ", ".join(recipients)
msg.set_content(os.environ["BODY"])

host, port = os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])
ctx = ssl.create_default_context()
try:
    if os.environ["SMTP_SSL"].strip().lower() in ("1", "true", "yes"):
        srv = smtplib.SMTP_SSL(host, port, context=ctx, timeout=30)
    else:
        srv = smtplib.SMTP(host, port, timeout=30)
        srv.starttls(context=ctx)
    with srv:
        srv.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        srv.send_message(msg, to_addrs=recipients)
except Exception as exc:
    # Report the exception type only - the text can echo back credentials.
    print("SMTP send failed: %s" % type(exc).__name__, file=sys.stderr)
    sys.exit(1)
'
}

alert() {
    local subject="$1" body="$2" tag="$3"

    # Journal first, so the alert is recorded even if every delivery path fails.
    logger -t junkbin-cert-monitor "$tag"

    if send_smtp "$subject" "$body"; then
        logger -t junkbin-cert-monitor "alert delivered via SMTP to ${ADMIN_EMAIL}"
        return 0
    fi

    if command -v mail >/dev/null 2>&1 && \
       echo "$body" | mail -s "$subject" "$ADMIN_EMAIL" 2>/dev/null; then
        logger -t junkbin-cert-monitor "alert delivered via mail(1) to ${ADMIN_EMAIL}"
        return 0
    fi

    logger -t junkbin-cert-monitor "ALERT DELIVERY FAILED - no SMTP relay and no working mail(1); intended recipient: ${ADMIN_EMAIL}"
    echo "$subject" >&2
    return 1
}

RENEW_HINT="Renew manually with:
  sudo /opt/certbot/bin/certbot renew
  cd ${JUNKBIN_DIR:-/home/scap/junkbin.io} && docker compose -f docker-compose.yml exec -T nginx nginx -s reload

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
