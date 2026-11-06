#!/bin/bash
################################################################################
# Junkbin.io - off-host mirror of prod's media (runs on the backup machine)
#
# backup.sh leaves media out of its archives once it is too big to copy twice
# a day (~55 GB since the Norway import, 2026-11-06). This keeps an rsync
# mirror of prod's media volume here instead: each run moves only new and
# changed files. Nothing prod drops is lost straight away: a file prod deleted
# or replaced moves to deleted/<run>/ and is pruned after RETAIN_DAYS.
# Thumbnails (media/cache) are left out - the site regenerates them.
#
#   <DEST>/current/          prod's media as of the last run
#   <DEST>/deleted/<run>/    what that run removed or replaced
#   <DEST>/mirror.log        one line per run (SUCCESS / FAILED)
#
# Needs rsync on both machines (prod: dnf install -y rsync).
# Cron (backup machine): 30 2,14 * * * <repo>/deployment/media-mirror.sh >/dev/null 2>>$DEST/mirror.log
#
# Restore, from here (prod cannot reach the backup machine, the reverse works):
#   rsync -rlt --info=stats1 -e "ssh -i ~/.ssh/id_scp_transfer" \
#       <DEST>/current/ root@junkbin.io:/var/lib/docker/volumes/junkbinio_media_files/_data/
#   then on prod: docker exec junkbin_backend chown -R <app user> /app/media
################################################################################
set -euo pipefail

REMOTE="${MIRROR_REMOTE:-root@junkbin.io}"
SSH_KEY="${MIRROR_SSH_KEY:-$HOME/.ssh/id_scp_transfer}"
DEST="${MIRROR_DEST:-$HOME/junkbin.io/Docs/Prod_Backups/media}"
RETAIN_DAYS="${RETAIN_DAYS:-180}"
SOURCE="${MIRROR_SOURCE:-}"     # a local directory instead of prod (tests)

RUN=$(date +%Y%m%d_%H%M%S)
LOG="$DEST/mirror.log"
mkdir -p "$DEST/current" "$DEST/deleted"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG"; }

# dev-refresh-from-prod.sh reads current/ under the same lock
exec 9>"$DEST/.lock"
flock -w 3600 9 || { log "FAILED: another run still holds $DEST/.lock after an hour"; exit 1; }

if [ -n "$SOURCE" ]; then
    SRC="${SOURCE%/}/"
    RSH=()
else
    SSH="ssh -i $SSH_KEY -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30"
    # the media_files volume, wherever compose put it
    if ! VOL=$($SSH "$REMOTE" "docker inspect -f '{{range .Mounts}}{{if eq .Destination \"/app/media\"}}{{.Source}}{{end}}{{end}}' junkbin_backend"); then
        log "FAILED: cannot ask $REMOTE for its media volume"
        exit 1
    fi
    if [ -z "$VOL" ]; then
        log "FAILED: junkbin_backend on $REMOTE has no /app/media volume"
        exit 1
    fi
    SRC="$REMOTE:$VOL/"
    RSH=(-e "$SSH")
fi

# -rlt, not -a: owners and modes stay this machine's. No --inplace: a file is
# replaced by rename, so a hard-linked seed copy is never written through.
rc=0
out=$(rsync -rlt --delete --backup --backup-dir="$DEST/deleted/$RUN" --exclude=/cache/ --stats \
          "${RSH[@]}" "$SRC" "$DEST/current/" 2>&1) || rc=$?
rmdir "$DEST/deleted/$RUN" 2>/dev/null || true

stat_of() { local v; v=$(echo "$out" | sed -n "s/^$1: \([0-9,]*\).*/\1/p" | tr -d , | sed -n 1p); echo "${v:-0}"; }
summary="$(echo "$out" | sed -n 's/^Number of files:.*reg: \([0-9,]*\).*/\1/p' | tr -d ,) files, $(stat_of 'Number of regular files transferred') copied \
($(( $(stat_of 'Total transferred file size') / 1000000 )) MB), $(stat_of 'Number of deleted files') moved to deleted/"

# 24: files vanished on prod mid-run (deleted while listed) - the rest is good
if [ "$rc" -eq 0 ] || [ "$rc" -eq 24 ]; then
    note=""
    [ "$rc" -eq 24 ] && note=" (some files vanished on prod during the run)"
    log "SUCCESS: $summary$note"
else
    log "FAILED: rsync exit $rc: $(echo "$out" | grep -v '^$' | tail -3 | tr '\n' ' ')"
    exit "$rc"
fi

PRUNED=$(find "$DEST/deleted" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETAIN_DAYS" -print -exec rm -rf {} + | wc -l)
[ "$PRUNED" -gt 0 ] && log "PRUNED: $PRUNED deleted/ folder(s) older than ${RETAIN_DAYS} days"
exit 0
