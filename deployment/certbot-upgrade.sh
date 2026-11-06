#!/bin/bash
################################################################################
# Junkbin.io - keep the /opt/certbot venv new enough for shorter certificates
#
# Let's Encrypt is shortening certificate lifetimes: 90 days today, 64 days from
# 2027-02-10, 45 days from 2028-02-16 (6-day certs are already available).
# Certbot >= 4.0 renews when a third of a cert's lifetime is left, and >= 4.1
# also follows ACME Renewal Information (ARI): Let's Encrypt can ask for an
# early renewal, e.g. before revoking certificates in bulk. Older certbot keeps
# a fixed 30-days-left rule and ignores ARI.
#
# Upgrades certbot + certbot-dns-hostinger in the venv when it is older than
# CERTBOT_MIN_VERSION, then proves renewal still works end to end with
# `certbot renew --dry-run` (Let's Encrypt staging - no real cert changes, no
# nginx reload). If the dry run fails, the previous package versions are put
# back, so the renewal cron is never left on an untested certbot. The certs
# expired once (Sep 2026) through a broken renewal path; don't let an upgrade
# be the next one.
#
# Usage: sudo deployment/certbot-upgrade.sh [--force]   (--force: upgrade even if new enough)
################################################################################
set -euo pipefail

VENV="${CERTBOT_VENV:-/opt/certbot}"
MIN="${CERTBOT_MIN_VERSION:-4.1.0}"

if [ ! -x "${VENV}/bin/certbot" ]; then
    echo "No ${VENV}/bin/certbot - install it first (deployment/junkbin-deploy.sh does)." >&2
    exit 1
fi

# only the "certbot X.Y.Z" line: plugins (dns-hostinger) log timestamped lines on every run
version() { "${VENV}/bin/certbot" --version 2>&1 | sed -n 's/^certbot \([0-9][0-9.]*\).*/\1/p' | tail -1; }
at_least() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }

current=$(version)
if at_least "$current" "$MIN" && [ "${1:-}" != "--force" ]; then
    echo "certbot ${current} is ${MIN} or newer: nothing to do"
    exit 0
fi

backup="/root/certbot-venv-freeze-$(date +%Y%m%d-%H%M%S).txt"
"${VENV}/bin/pip" freeze > "$backup"
echo "certbot ${current}: package versions saved to ${backup}; upgrading to >= ${MIN}..."
"${VENV}/bin/pip" install --quiet --upgrade pip
"${VENV}/bin/pip" install --quiet --upgrade "certbot>=${MIN}" certbot-dns-hostinger
new=$(version)

echo "certbot ${new} installed; proving renewal against Let's Encrypt staging (no real certs change)..."
if "${VENV}/bin/certbot" renew --dry-run; then
    echo "Dry run passed: the renewal cron now runs certbot ${new}."
    exit 0
fi

echo "Dry run FAILED with certbot ${new} - restoring the previous versions from ${backup}" >&2
"${VENV}/bin/pip" install --quiet -r "$backup"
echo "certbot is back at $(version). Renewal is unchanged; investigate before retrying." >&2
exit 1
