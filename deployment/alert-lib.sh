#!/bin/bash
################################################################################
# Junkbin.io - shared alert delivery for infrastructure monitors
#
# Sourced by cert-monitor.sh and disk-monitor.sh. Not executable on its own.
#
# Both monitors originally called `mail -s ...`, which on this host delivers
# nowhere: there is no `mail` binary, and exim is installed but not running.
# An alert sent that way falls back to stderr and is swallowed by the systemd
# timer - a monitor that reaches nobody, which is worse than no monitor at all
# because it reads as coverage. That is precisely how the Sep 2026 certificate
# expiry went unnoticed.
#
# Delivery therefore reuses the Django app's authenticated SMTP relay. A local
# MTA was rejected as the fix: mail from a cloud IP with no SPF or DKIM is
# mostly spam-filtered, which reintroduces the same silence one layer down.
#
# Callers should set ALERT_TAG before sourcing, so journal entries carry the
# originating monitor's name.
#
# Usage:
#     ALERT_TAG=junkbin-cert-monitor
#     source "$(dirname "${BASH_SOURCE[0]}")/alert-lib.sh"
#     alert "subject" "body" "journal tag line" || true
################################################################################

ALERT_TAG="${ALERT_TAG:-junkbin-monitor}"
JUNKBIN_DIR="${JUNKBIN_DIR:-/root/junkbin.io}"
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

# SMTP credentials from the app's .env. These are secrets - never echo them.
SMTP_HOST="$(read_env EMAIL_HOST)"
SMTP_PORT="$(read_env EMAIL_PORT)"
SMTP_USER="$(read_env EMAIL_HOST_USER)"
SMTP_PASSWORD="$(read_env EMAIL_HOST_PASSWORD)"
SMTP_SSL="$(read_env EMAIL_USE_SSL)"
SMTP_PORT="${SMTP_PORT:-465}"
SMTP_SSL="${SMTP_SSL:-True}"

# Who gets alerted. Resolved from .env so the address lives in exactly one place
# on the server and never in version control - this repo is public. ALERT_EMAIL
# takes precedence and accepts a comma-separated list, so alerts can go
# somewhere a person actually reads without disturbing ADMIN_EMAIL, which the
# app and certbot registration also use. JUNKBIN_ADMIN_EMAIL overrides both,
# for testing.
ADMIN_EMAIL="${JUNKBIN_ADMIN_EMAIL:-$(read_env ALERT_EMAIL)}"
ADMIN_EMAIL="${ADMIN_EMAIL:-$(read_env ADMIN_EMAIL)}"
ADMIN_EMAIL="${ADMIN_EMAIL:-root}"

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

# alert <subject> <body> <journal-line>
# Returns non-zero if every delivery path failed. Callers running under `set -e`
# must guard with `|| true`, or one failed send abandons the rest of the sweep.
alert() {
    local subject="$1" body="$2" tag="$3"

    # Journal first, so the alert is recorded even if every delivery path fails.
    logger -t "$ALERT_TAG" "$tag"

    if send_smtp "$subject" "$body"; then
        logger -t "$ALERT_TAG" "alert delivered via SMTP to ${ADMIN_EMAIL}"
        return 0
    fi

    if command -v mail >/dev/null 2>&1 && \
       echo "$body" | mail -s "$subject" "$ADMIN_EMAIL" 2>/dev/null; then
        logger -t "$ALERT_TAG" "alert delivered via mail(1) to ${ADMIN_EMAIL}"
        return 0
    fi

    logger -t "$ALERT_TAG" "ALERT DELIVERY FAILED - no SMTP relay and no working mail(1); intended recipient: ${ADMIN_EMAIL}"
    echo "$subject" >&2
    return 1
}
