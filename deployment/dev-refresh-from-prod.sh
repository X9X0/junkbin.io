#!/bin/bash
################################################################################
# Junkbin.io - refresh dev from prod (runs on dev, nightly at 03:00)
#
# Dev starts each day as a copy of prod, so dev -> prod rehearsals run on real
# data. Sources are what this machine already pulls: the newest prod backup in
# Docs/Prod_Backups (02:00, pulled 02:15) and the media mirror (02:30,
# deployment/media-mirror.sh). Both must be under MAX_AGE_HOURS old or nothing
# changes. Prod is never contacted.
#
#   1. restore the dump into a new database (junkbin_refresh), beside dev's
#   2. scrub it: every password unusable and every email @example.invalid,
#      except dev's own staff accounts (they keep dev's password and email);
#      sessions, API/OAuth/push tokens and email confirmations deleted;
#      webhooks switched off - dev must never reach prod's users or services
#   3. stop the app, swap databases (dev's becomes junkbin_prev), point the
#      media volume at the mirror with hard links (old one kept as _data.prev),
#      start, migrate (dev's branch may be ahead of main), flush redis
#
# Everything only on dev's database or media is replaced. To keep dev as it
# is (an import in progress, a multi-day job): touch ~/.dev-refresh-hold
# and remove it when done.
#
# Usage: deployment/dev-refresh-from-prod.sh [--check | --undo]
#   --check  steps 1-2 only, report, drop the new database (dev untouched)
#   --undo   swap back to the previous night's database and media
################################################################################
set -Eeuo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUPS="${REFRESH_BACKUPS:-$REPO/Docs/Prod_Backups}"
MIRROR="$BACKUPS/media/current"
HOLD="${REFRESH_HOLD:-$HOME/.dev-refresh-hold}"
LOG="$BACKUPS/dev-refresh.log"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-26}"
DB=junkbin NEW=junkbin_refresh PREV=junkbin_prev
MODE="${1:-}"

cd "$REPO"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG"; }
psql_() { docker compose exec -T postgres psql -U junkbin -v ON_ERROR_STOP=1 -q "$@"; }
APP=(backend celery celery-beat nginx)
STOPPED=false

# a failure never leaves dev without a database or with the app stopped
on_error() {
    local rc=$?
    trap - ERR
    if $STOPPED; then
        if [ "$(psql_ -d postgres -Atc "select count(*) from pg_database where datname='$DB'")" = 0 ]; then
            psql_ -d postgres -c "alter database $PREV rename to $DB" || true
        fi
        docker compose start "${APP[@]}" >/dev/null 2>&1 || true
    fi
    log "FAILED (exit $rc) at line $1 - see the lines above; the app is running"
    exit "$rc"
}
trap 'on_error $LINENO' ERR

# Dev has no SMTP server: anything the app sends only reaches its log. Prod has
# one, so this also stops the script ever running there.
if grep -qE '^EMAIL_HOST=.+' .env; then
    log "REFUSED: EMAIL_HOST is set in .env - not dev, or dev can send mail"
    exit 1
fi

# the media volume's directory on this machine
volume_dir() {
    docker inspect -f '{{range .Mounts}}{{if eq .Destination "/app/media"}}{{.Source}}{{end}}{{end}}' junkbin_backend
}

# swap media directories as root (the volume belongs to root); $1: shell snippet using $V
as_root() {
    docker run --rm -v /:/host --entrypoint sh junkbinio-backend -c "set -e; V=/host$(dirname "$(volume_dir)"); $1"
}

if [ "$MODE" = "--undo" ]; then
    [ "$(psql_ -d postgres -Atc "select count(*) from pg_database where datname='$PREV'")" = 1 ] || {
        log "UNDO: no $PREV database to go back to"; exit 1; }
    STOPPED=true
    docker compose stop "${APP[@]}"
    psql_ -d postgres -c "select pg_terminate_backend(pid) from pg_stat_activity where datname in ('$DB','$PREV') and pid <> pg_backend_pid()" >/dev/null
    psql_ -d postgres -c "alter database $DB rename to junkbin_undo" -c "alter database $PREV rename to $DB" \
          -c "alter database junkbin_undo rename to $PREV"
    as_root 'if [ -d $V/_data.prev ]; then mv $V/_data $V/_data.undo; mv $V/_data.prev $V/_data; mv $V/_data.undo $V/_data.prev; fi'
    docker compose start "${APP[@]}"
    docker compose exec -T redis redis-cli FLUSHALL >/dev/null
    log "UNDO: back to the previous database and media (run --undo again to return)"
    exit 0
fi

if [ -e "$HOLD" ] && [ "$MODE" != "--check" ]; then
    log "SKIP: on hold ($HOLD exists)"
    exit 0
fi

# one run at a time, and never while the media mirror is writing
exec 9>"$BACKUPS/media/.lock"
flock -w 3600 9 || { log "SKIP: media mirror still running after an hour"; exit 1; }

ARCHIVE=$(ls -t "$BACKUPS"/junkbin_backup_*.tar.gz 2>/dev/null | sed -n 1p)
fresh() { [ -n "$(find "$1" -maxdepth 0 -mmin -$(( MAX_AGE_HOURS * 60 )) 2>/dev/null)" ]; }
problems=""
[ -n "$ARCHIVE" ] && fresh "$ARCHIVE" || problems="no prod backup newer than ${MAX_AGE_HOURS}h in $BACKUPS; "
fresh "$BACKUPS/media/mirror.log" && tail -1 "$BACKUPS/media/mirror.log" | grep -q SUCCESS \
    || problems+="media mirror's last run is old or failed; "
if [ -n "$problems" ]; then
    if [ "$MODE" != "--check" ]; then
        log "SKIP: ${problems}dev left as it is"
        exit 1
    fi
    echo "check mode, going on anyway: $problems"
fi

# --- 1. restore beside dev's database --------------------------------------------
psql_ -d postgres -c "drop database if exists $NEW" -c "create database $NEW owner junkbin"
tar -xzOf "$ARCHIVE" --wildcards '*/database.sql' | psql_ -1 -d "$NEW" >/dev/null

# --- 2. scrub ------------------------------------------------------------------------
KEEP=$(psql_ -d "$DB" -Atc "select format('update users_user set password = %L, email = %L where username = %L;',
                                   password, email, username) from users_user where is_staff or is_superuser")
psql_ -1 -d "$NEW" >/dev/null <<SQL
update users_user set password = '!dev-refresh', email = 'user-' || id || '@example.invalid';
$KEEP
update account_emailaddress a set email = u.email from users_user u where u.id = a.user_id;
update newsletter_subscriber set email = 'subscriber-' || id || '@example.invalid';
update webhooks_webhookendpoint set is_active = false;
delete from account_emailconfirmation;
delete from authtoken_token;
delete from socialaccount_socialtoken;
delete from notifications_pushsubscription;
delete from token_blacklist_blacklistedtoken;
delete from token_blacklist_outstandingtoken;
delete from django_session;
SQL
COUNTS=$(psql_ -d "$NEW" -Atc "select (select count(*) from products_product) || ' products, ' ||
    (select count(*) from components_component) || ' components, ' || (select count(*) from users_user) || ' users'")

if [ "$MODE" = "--check" ]; then
    LEFT=$(psql_ -d "$NEW" -Atc "select count(*) from users_user where email not like '%@example.invalid' or password not like '!%'")
    psql_ -d postgres -c "drop database $NEW"
    log "CHECK: $(basename "$ARCHIVE") restores and scrubs cleanly: $COUNTS ($LEFT staff kept dev's login); dev not changed"
    exit 0
fi

# --- 3. swap ---------------------------------------------------------------------------
STOPPED=true
docker compose stop "${APP[@]}"
psql_ -d postgres -c "select pg_terminate_backend(pid) from pg_stat_activity where datname = '$DB' and pid <> pg_backend_pid()" >/dev/null
psql_ -d postgres -c "drop database if exists $PREV" -c "alter database $DB rename to $PREV" \
      -c "alter database $NEW rename to $DB"
# hard links: no copy, no extra disk; the site never writes a file in place.
# Thumbnails come along (the site regenerates any it lacks).
as_root "M=/host$MIRROR
    rm -rf \$V/_data.new \$V/_data.prev
    cp -al \$M \$V/_data.new
    if [ -d \$V/_data/cache ]; then cp -al \$V/_data/cache \$V/_data.new/cache; fi
    mv \$V/_data \$V/_data.prev && mv \$V/_data.new \$V/_data"
docker compose start "${APP[@]}"
docker compose exec -T backend python manage.py migrate --noinput >/dev/null
docker compose exec -T redis redis-cli FLUSHALL >/dev/null
log "SUCCESS: dev is prod as of $(basename "$ARCHIVE" .tar.gz | sed 's/junkbin_backup_//'): $COUNTS; \
media $(find "$MIRROR" -type f | wc -l) files. Previous dev kept: --undo"
