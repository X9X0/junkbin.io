#!/bin/bash
#
# Junkbin.io Backup Script
# Creates backups of database and media files
#
# Usage: ./backup.sh [options] [backup_dir]
# Options:
#   --dev   Local dev mode (local postgres + ./backend/media on disk)
#
# Default mode assumes Docker (works for both dev and production Docker stacks).
#
# "NO USER SERVICEABLE PARTS INSIDE" - But we back them up anyway
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${CYAN}[BACKUP]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse flags
DEV_MODE=false
BACKUP_DIR=""
for arg in "$@"; do
    case $arg in
        --dev) DEV_MODE=true ;;
        *)     BACKUP_DIR="$arg" ;;
    esac
done

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="junkbin_backup_$TIMESTAMP"

# Load .env
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

DB_NAME="${POSTGRES_DB:-junkbin}"
DB_USER="${POSTGRES_USER:-junkbin}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

echo ""
echo "========================================"
echo "  Junkbin.io Backup Script"
if [ "$DEV_MODE" = true ]; then
    echo "  Mode: LOCAL DEV (no Docker)"
else
    echo "  Mode: DOCKER"
fi
echo "========================================"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# --- Database Backup ---
log_info "Backing up PostgreSQL database..."

if [ "$DEV_MODE" = true ]; then
    if ! command -v pg_dump &> /dev/null; then
        log_error "pg_dump not found. Install PostgreSQL client tools."
        exit 1
    fi
    PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" \
        > "$BACKUP_DIR/$BACKUP_NAME/database.sql"
else
    if ! docker ps --format '{{.Names}}' | grep -q "^junkbin_postgres$"; then
        log_error "junkbin_postgres container is not running."
        exit 1
    fi
    docker exec junkbin_postgres pg_dump -U "$DB_USER" "$DB_NAME" \
        > "$BACKUP_DIR/$BACKUP_NAME/database.sql"
fi

DB_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME/database.sql" | cut -f1)
log_success "Database backup complete ($DB_SIZE)"

# --- Media Backup ---
log_info "Backing up media files..."

if [ "$DEV_MODE" = true ]; then
    # Dev mode: media is on disk at ./backend/media
    MEDIA_DIR="$PROJECT_DIR/backend/media"
    if [ -d "$MEDIA_DIR" ] && [ "$(ls -A "$MEDIA_DIR" 2>/dev/null)" ]; then
        nice -n 15 tar -czf "$BACKUP_DIR/$BACKUP_NAME/media.tar.gz" -C "$PROJECT_DIR/backend" media
        MEDIA_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME/media.tar.gz" | cut -f1)
        log_success "Media backup complete ($MEDIA_SIZE)"
    else
        log_warn "No media files found at $MEDIA_DIR, skipping..."
    fi
else
    # Docker mode: media is in the media_files named volume at /app/media
    if ! docker ps --format '{{.Names}}' | grep -q "^junkbin_backend$"; then
        log_error "junkbin_backend container is not running."
        exit 1
    fi

    # Size check first. Media is archived whole on every run (02:00 and 14:00)
    # and pulled off-host each time, and the archive briefly needs room twice
    # (media.tar.gz, then the final archive around it). Since the Norway import
    # (2026-11-06) media is ~55 GB: archiving it would fill the disk and take the
    # site down, so above MEDIA_BACKUP_MAX_GB, or without room for two copies
    # plus MEDIA_BACKUP_RESERVE_GB, media is left out and the run says so.
    # MEDIA_BACKUP=always / never overrides the size check.
    MEDIA_KB=$(docker exec junkbin_backend du -sk /app/media 2>/dev/null | cut -f1)
    MEDIA_KB=${MEDIA_KB:-0}
    FREE_KB=$(df -Pk "$BACKUP_DIR" | awk 'NR==2 {print $4}')
    MAX_KB=$(( ${MEDIA_BACKUP_MAX_GB:-10} * 1000000 ))
    NEED_KB=$(( 2 * MEDIA_KB + ${MEDIA_BACKUP_RESERVE_GB:-20} * 1000000 ))
    MEDIA_GB="$(( MEDIA_KB / 1000000 )) GB"
    MEDIA_NOTE=""
    case "${MEDIA_BACKUP:-auto}" in
        never)  MEDIA_NOTE="MEDIA_BACKUP=never" ;;
        always) ;;
        *)  if [ "$MEDIA_KB" -gt "$MAX_KB" ]; then
                MEDIA_NOTE="media is ${MEDIA_GB}, over MEDIA_BACKUP_MAX_GB=${MEDIA_BACKUP_MAX_GB:-10}"
            elif [ "$FREE_KB" -lt "$NEED_KB" ]; then
                MEDIA_NOTE="media is ${MEDIA_GB}, only $(( FREE_KB / 1000000 )) GB free (needs $(( NEED_KB / 1000000 )) GB)"
            fi ;;
    esac

    if [ -n "$MEDIA_NOTE" ]; then
        log_warn "Media NOT backed up: ${MEDIA_NOTE}"
    elif [ "$MEDIA_KB" -gt 0 ]; then
        # streamed straight out of the container: no second copy in its /tmp
        set -o pipefail
        docker exec junkbin_backend nice -n 15 tar -czf - -C /app media \
            > "$BACKUP_DIR/$BACKUP_NAME/media.tar.gz"
        set +o pipefail
        FILE_COUNT=$(docker exec junkbin_backend find /app/media -type f 2>/dev/null | wc -l)
        MEDIA_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME/media.tar.gz" | cut -f1)
        log_success "Media backup complete ($MEDIA_SIZE) — $FILE_COUNT files"
    else
        log_warn "No media files in volume, skipping..."
    fi
fi

# --- .env Backup ---
log_info "Backing up configuration..."
if [ -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env" "$BACKUP_DIR/$BACKUP_NAME/.env.backup"
    log_warn "Environment file backed up — contains secrets, store securely!"
fi

# --- Manifest ---
log_info "Creating backup manifest..."
cat > "$BACKUP_DIR/$BACKUP_NAME/manifest.txt" << EOF
Junkbin.io Backup Manifest
==========================
Backup Name: $BACKUP_NAME
Created: $(date)
Hostname: $(hostname)
Mode: $([ "$DEV_MODE" = true ] && echo "local dev" || echo "docker")

Contents:
- database.sql: PostgreSQL database dump
- media.tar.gz: Uploaded images, schematics, and files (if present)${MEDIA_NOTE:+
  NOT IN THIS BACKUP: ${MEDIA_NOTE}}
- .env.backup: Environment configuration (SENSITIVE)

Database: $DB_NAME

To restore: ./restore.sh $BACKUP_DIR/${BACKUP_NAME}.tar.gz
EOF

# --- Compress ---
log_info "Compressing backup archive..."
cd "$BACKUP_DIR"
nice -n 15 tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

FINAL_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)

# Cleanup old backups (keep last 30 days)
log_info "Cleaning up old backups (keeping last 30 days)..."
find "$BACKUP_DIR" -name "junkbin_backup_*.tar.gz" -mtime +30 -delete 2>/dev/null || true

echo ""
echo "========================================"
log_success "Backup completed successfully!"
echo ""
echo "  File: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo "  Size: $FINAL_SIZE"
echo ""
echo "  Store securely — contains database and secrets."
echo "========================================"
echo ""
