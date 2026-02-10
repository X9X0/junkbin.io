#!/bin/bash
#
# Junkbin.io Restore Script
# Restores database and media files from backup
#
# Usage: ./restore.sh [options] <backup_file_or_directory>
# Options:
#   --dev   Local dev mode (local postgres + ./backend/media on disk)
#
# Default mode assumes Docker (works for both dev and production Docker stacks).
#
# "NO USER SERVICEABLE PARTS INSIDE" - Time to put it back together
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${CYAN}[RESTORE]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse flags
DEV_MODE=false
BACKUP_PATH=""
for arg in "$@"; do
    case $arg in
        --dev) DEV_MODE=true ;;
        *)     BACKUP_PATH="$arg" ;;
    esac
done

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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
echo "  Junkbin.io Restore Script"
if [ "$DEV_MODE" = true ]; then
    echo "  Mode: LOCAL DEV (no Docker)"
else
    echo "  Mode: DOCKER"
fi
echo "========================================"
echo ""

# Validate input
if [ -z "$BACKUP_PATH" ]; then
    log_error "Usage: $0 [--dev] <backup_file_or_directory>"
    echo ""
    echo "Examples:"
    echo "  $0 backups/junkbin_backup_20260209_120000.tar.gz"
    echo "  $0 --dev backups/junkbin_backup_20260209_120000.tar.gz"
    exit 1
fi

if [ ! -e "$BACKUP_PATH" ]; then
    log_error "Backup not found: $BACKUP_PATH"
    exit 1
fi

# Extract if tar.gz
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

if [[ "$BACKUP_PATH" == *.tar.gz ]]; then
    log_info "Extracting backup archive..."
    tar -xzf "$BACKUP_PATH" -C "$TEMP_DIR"
    RESTORE_DIR="$TEMP_DIR/$(ls "$TEMP_DIR")"
else
    RESTORE_DIR="$BACKUP_PATH"
fi

# Verify backup contents
if [ ! -f "$RESTORE_DIR/database.sql" ]; then
    log_error "Invalid backup: database.sql not found"
    exit 1
fi

log_info "Backup contents:"
ls -lh "$RESTORE_DIR"
echo ""

if [ -f "$RESTORE_DIR/manifest.txt" ]; then
    log_info "Manifest:"
    cat "$RESTORE_DIR/manifest.txt"
    echo ""
fi

# Confirmation
echo -e "${YELLOW}WARNING: This will overwrite the current database and media files!${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    log_info "Restore cancelled."
    exit 0
fi

# --- Database Restore ---
if [ "$DEV_MODE" = true ]; then
    if ! command -v psql &> /dev/null; then
        log_error "psql not found. Install PostgreSQL client tools."
        exit 1
    fi

    log_info "Dropping and recreating database..."
    PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        -c "DROP DATABASE IF EXISTS ${DB_NAME};" postgres || true
    PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        -c "CREATE DATABASE ${DB_NAME};" postgres

    log_info "Restoring database..."
    PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        "$DB_NAME" < "$RESTORE_DIR/database.sql"
else
    if ! docker ps --format '{{.Names}}' | grep -q "^junkbin_postgres$"; then
        log_error "junkbin_postgres container is not running."
        exit 1
    fi

    # Stop backend/celery to drop active connections
    log_info "Stopping backend services..."
    cd "$PROJECT_DIR"
    docker compose stop backend celery celery-beat 2>/dev/null || true

    log_info "Dropping and recreating database..."
    docker exec junkbin_postgres psql -U "$DB_USER" \
        -c "DROP DATABASE IF EXISTS ${DB_NAME};" postgres || true
    docker exec junkbin_postgres psql -U "$DB_USER" \
        -c "CREATE DATABASE ${DB_NAME};" postgres

    log_info "Restoring database..."
    docker cp "$RESTORE_DIR/database.sql" junkbin_postgres:/tmp/database.sql
    docker exec junkbin_postgres psql -U "$DB_USER" "$DB_NAME" -f /tmp/database.sql
    docker exec junkbin_postgres rm /tmp/database.sql
fi

log_success "Database restored!"

# --- Media Restore ---
if [ -f "$RESTORE_DIR/media.tar.gz" ]; then
    log_info "Restoring media files..."

    if [ "$DEV_MODE" = true ]; then
        # Dev mode: restore to ./backend/media
        MEDIA_DIR="$PROJECT_DIR/backend/media"
        if [ -d "$MEDIA_DIR" ]; then
            mv "$MEDIA_DIR" "${MEDIA_DIR}.old.$(date +%s)" || true
        fi
        mkdir -p "$PROJECT_DIR/backend"
        tar -xzf "$RESTORE_DIR/media.tar.gz" -C "$PROJECT_DIR/backend"
        log_success "Media restored to $MEDIA_DIR"
    else
        # Docker mode: restore into the media_files volume via backend container
        if ! docker ps --format '{{.Names}}' | grep -q "^junkbin_backend$"; then
            # Backend was stopped above, start it temporarily
            cd "$PROJECT_DIR"
            docker compose start backend
            sleep 3
        fi

        docker cp "$RESTORE_DIR/media.tar.gz" junkbin_backend:/tmp/media_restore.tar.gz
        docker exec junkbin_backend rm -rf /app/media/*
        docker exec junkbin_backend tar -xzf /tmp/media_restore.tar.gz -C /app
        docker exec junkbin_backend rm /tmp/media_restore.tar.gz
        FILE_COUNT=$(docker exec junkbin_backend find /app/media -type f | wc -l)
        log_success "Media restored to volume — $FILE_COUNT files"
    fi
else
    log_warn "No media backup found, skipping..."
fi

# --- Optional .env Restore ---
if [ -f "$RESTORE_DIR/.env.backup" ]; then
    echo ""
    read -p "Restore environment configuration (.env)? (yes/no): " RESTORE_ENV
    if [ "$RESTORE_ENV" == "yes" ]; then
        cp "$RESTORE_DIR/.env.backup" "$PROJECT_DIR/.env"
        log_success "Environment configuration restored!"
    fi
fi

# --- Restart Services ---
if [ "$DEV_MODE" = false ]; then
    log_info "Restarting services..."
    cd "$PROJECT_DIR"
    docker compose up -d

    log_info "Running migrations..."
    docker compose exec backend python manage.py migrate --noinput || true
fi

echo ""
echo "========================================"
log_success "Restore completed!"
echo ""
echo "  Database: Restored"
if [ -f "$RESTORE_DIR/media.tar.gz" ]; then
    echo "  Media:    Restored"
fi
if [ "$DEV_MODE" = false ]; then
    echo "  Services: Restarted"
fi
echo ""
echo "  Please verify the site is working correctly."
echo "========================================"
echo ""
