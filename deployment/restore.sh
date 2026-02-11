#!/bin/bash
#
# Junkbin.io Restore Script
# Interactive menu-driven restore of database, media, and config from backup
#
# Usage: ./restore.sh [options] <backup_file_or_directory>
# Options:
#   --dev    Local dev mode (local postgres + ./backend/media on disk)
#   --yes    Skip confirmation prompt (use selected defaults)
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
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

log_info()    { echo -e "${CYAN}[RESTORE]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse flags
DEV_MODE=false
AUTO_YES=false
BACKUP_PATH=""
for arg in "$@"; do
    case $arg in
        --dev) DEV_MODE=true ;;
        --yes) AUTO_YES=true ;;
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
echo -e "${BOLD}========================================"
echo "  Junkbin.io Restore Script"
if [ "$DEV_MODE" = true ]; then
    echo "  Mode: LOCAL DEV (no Docker)"
else
    echo "  Mode: DOCKER"
fi
echo -e "========================================${NC}"
echo ""

# Validate input
if [ -z "$BACKUP_PATH" ]; then
    log_error "Usage: $0 [--dev] [--yes] <backup_file_or_directory>"
    echo ""
    echo "Options:"
    echo "  --dev    Local dev mode (direct postgres, no Docker)"
    echo "  --yes    Skip interactive menu, use defaults and auto-confirm"
    echo ""
    echo "Examples:"
    echo "  $0 backups/junkbin_backup_20260209_120000.tar.gz"
    echo "  $0 --dev backups/junkbin_backup_20260209_120000.tar.gz"
    echo "  $0 --yes backups/junkbin_backup_20260209_120000.tar.gz"
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

# =========================================================================
# Inspect backup and show summary
# =========================================================================
HAS_DATABASE=true
HAS_MEDIA=false
HAS_ENV=false

DB_SIZE=$(du -h "$RESTORE_DIR/database.sql" | cut -f1)

if [ -f "$RESTORE_DIR/media.tar.gz" ]; then
    HAS_MEDIA=true
    MEDIA_SIZE=$(du -h "$RESTORE_DIR/media.tar.gz" | cut -f1)
fi

if [ -f "$RESTORE_DIR/.env.backup" ]; then
    HAS_ENV=true
fi

# Get backup info from manifest
BACKUP_DATE="unknown"
BACKUP_HOST="unknown"
if [ -f "$RESTORE_DIR/manifest.txt" ]; then
    BACKUP_DATE=$(grep "^Created:" "$RESTORE_DIR/manifest.txt" | sed 's/Created: //' || echo "unknown")
    BACKUP_HOST=$(grep "^Hostname:" "$RESTORE_DIR/manifest.txt" | sed 's/Hostname: //' || echo "unknown")
fi

echo -e "${BOLD}  Backup Summary${NC}"
echo "  ─────────────────────────────────────"
echo -e "  Created:  ${CYAN}${BACKUP_DATE}${NC}"
echo -e "  Source:   ${CYAN}${BACKUP_HOST}${NC}"
echo -e "  Database: ${GREEN}${DB_SIZE}${NC}"
if [ "$HAS_MEDIA" = true ]; then
    echo -e "  Media:    ${GREEN}${MEDIA_SIZE}${NC}"
else
    echo -e "  Media:    ${DIM}not included${NC}"
fi
if [ "$HAS_ENV" = true ]; then
    echo -e "  .env:     ${YELLOW}included${NC}"
else
    echo -e "  .env:     ${DIM}not included${NC}"
fi
echo ""

# =========================================================================
# Restore options menu — safe defaults
# =========================================================================

# Defaults: database + media + users ON, env OFF
OPT_DATABASE=true
OPT_MEDIA=true
OPT_ENV=false
OPT_RESTORE_USERS=true  # true = keep backup's users, false = wipe and create fresh admin

show_menu() {
    echo -e "${BOLD}  Restore Options${NC}"
    echo "  ─────────────────────────────────────"

    # Database
    if [ "$OPT_DATABASE" = true ]; then
        echo -e "  ${GREEN}[1]  [x] Restore database${NC}           (products, components, schematics)"
    else
        echo -e "  ${DIM}[1]  [ ] Restore database${NC}           (products, components, schematics)"
    fi

    # Media
    if [ "$HAS_MEDIA" = true ]; then
        if [ "$OPT_MEDIA" = true ]; then
            echo -e "  ${GREEN}[2]  [x] Restore media files${NC}        (PDFs, images, spreadsheets)"
        else
            echo -e "  ${DIM}[2]  [ ] Restore media files${NC}        (PDFs, images, spreadsheets)"
        fi
    else
        echo -e "  ${DIM}[2]  [-] Restore media files${NC}        (not in backup)"
    fi

    # Users
    if [ "$OPT_RESTORE_USERS" = true ]; then
        echo -e "  ${GREEN}[3]  [x] Restore user accounts${NC}      (keep backup's users + passwords)"
    else
        echo -e "  ${YELLOW}[3]  [ ] Restore user accounts${NC}      ${YELLOW}(wipe users, create fresh admin)${NC}"
    fi

    # Env
    if [ "$HAS_ENV" = true ]; then
        if [ "$OPT_ENV" = true ]; then
            echo -e "  ${YELLOW}[4]  [x] Restore .env config${NC}        ${YELLOW}(overwrites current secrets!)${NC}"
        else
            echo -e "  ${GREEN}[4]  [ ] Restore .env config${NC}        (keep current server config)"
        fi
    else
        echo -e "  ${DIM}[4]  [-] Restore .env config${NC}        (not in backup)"
    fi

    echo ""
    echo -e "  ${BOLD}[Enter]${NC} Start restore    ${BOLD}[q]${NC} Cancel"
    echo ""
}

if [ "$AUTO_YES" = false ]; then
    while true; do
        clear 2>/dev/null || true
        echo ""
        echo -e "${BOLD}========================================"
        echo "  Junkbin.io Restore Script"
        if [ "$DEV_MODE" = true ]; then
            echo "  Mode: LOCAL DEV (no Docker)"
        else
            echo "  Mode: DOCKER"
        fi
        echo -e "========================================${NC}"
        echo ""
        echo -e "${BOLD}  Backup Summary${NC}"
        echo "  ─────────────────────────────────────"
        echo -e "  Created:  ${CYAN}${BACKUP_DATE}${NC}"
        echo -e "  Source:   ${CYAN}${BACKUP_HOST}${NC}"
        echo -e "  Database: ${GREEN}${DB_SIZE}${NC}"
        if [ "$HAS_MEDIA" = true ]; then
            echo -e "  Media:    ${GREEN}${MEDIA_SIZE}${NC}"
        else
            echo -e "  Media:    ${DIM}not included${NC}"
        fi
        if [ "$HAS_ENV" = true ]; then
            echo -e "  .env:     ${YELLOW}included${NC}"
        else
            echo -e "  .env:     ${DIM}not included${NC}"
        fi
        echo ""

        show_menu

        read -r -p "  > " choice
        case $choice in
            1) [ "$OPT_DATABASE" = true ] && OPT_DATABASE=false || OPT_DATABASE=true ;;
            2) [ "$HAS_MEDIA" = true ] && { [ "$OPT_MEDIA" = true ] && OPT_MEDIA=false || OPT_MEDIA=true; } ;;
            3) [ "$OPT_RESTORE_USERS" = true ] && OPT_RESTORE_USERS=false || OPT_RESTORE_USERS=true ;;
            4) [ "$HAS_ENV" = true ] && { [ "$OPT_ENV" = true ] && OPT_ENV=false || OPT_ENV=true; } ;;
            q|Q)
                log_info "Restore cancelled."
                exit 0
                ;;
            "")
                # Enter pressed — confirm and go
                break
                ;;
            *)
                ;;
        esac
    done

    # Final confirmation
    echo ""
    echo -e "  ${BOLD}Will restore:${NC}"
    [ "$OPT_DATABASE" = true ]    && echo -e "    ${GREEN}+ Database${NC}"
    [ "$OPT_MEDIA" = true ]       && echo -e "    ${GREEN}+ Media files${NC}"
    [ "$OPT_RESTORE_USERS" = true ] && echo -e "    ${GREEN}+ Restore user accounts from backup${NC}"
    [ "$OPT_RESTORE_USERS" = false ] && echo -e "    ${YELLOW}! Wipe users, create fresh admin${NC}"
    [ "$OPT_ENV" = true ]         && echo -e "    ${YELLOW}! Overwriting .env${NC}"
    [ "$OPT_ENV" = false ]        && echo -e "    ${GREEN}+ Keep current .env${NC}"
    echo ""

    if [ "$OPT_DATABASE" = false ] && [ "$OPT_MEDIA" = false ]; then
        log_warn "Nothing selected to restore."
        exit 0
    fi

    echo -e "${YELLOW}WARNING: This will overwrite selected data on this server!${NC}"
    read -r -p "Type 'yes' to proceed: " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        log_info "Restore cancelled."
        exit 0
    fi
fi

echo ""

# =========================================================================
# Execute restore
# =========================================================================

# --- Database Restore ---
if [ "$OPT_DATABASE" = true ]; then
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
fi

# --- Media Restore ---
if [ "$OPT_MEDIA" = true ] && [ "$HAS_MEDIA" = true ]; then
    log_info "Restoring media files..."

    if [ "$DEV_MODE" = true ]; then
        MEDIA_DIR="$PROJECT_DIR/backend/media"
        if [ -d "$MEDIA_DIR" ]; then
            mv "$MEDIA_DIR" "${MEDIA_DIR}.old.$(date +%s)" || true
        fi
        mkdir -p "$PROJECT_DIR/backend"
        tar -xzf "$RESTORE_DIR/media.tar.gz" -C "$PROJECT_DIR/backend"
        log_success "Media restored to $MEDIA_DIR"
    else
        if ! docker ps --format '{{.Names}}' | grep -q "^junkbin_backend$"; then
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
fi

# --- .env Restore ---
if [ "$OPT_ENV" = true ] && [ "$HAS_ENV" = true ]; then
    # Back up current .env first
    if [ -f "$PROJECT_DIR/.env" ]; then
        cp "$PROJECT_DIR/.env" "$PROJECT_DIR/.env.pre-restore.$(date +%s)"
        log_info "Current .env backed up to .env.pre-restore.*"
    fi
    cp "$RESTORE_DIR/.env.backup" "$PROJECT_DIR/.env"
    log_success "Environment configuration restored!"
    log_warn "Review .env for correct ALLOWED_HOSTS, CORS, and domain settings!"
fi

# --- Restart Services ---
if [ "$DEV_MODE" = false ]; then
    log_info "Restarting services..."
    cd "$PROJECT_DIR"
    docker compose up -d

    log_info "Running migrations..."
    docker compose exec -T backend python manage.py migrate --noinput 2>/dev/null || true
fi

# --- Reset Users (only when user chose NOT to restore backup's users) ---
if [ "$OPT_RESTORE_USERS" = false ] && [ "$OPT_DATABASE" = true ]; then
    log_info "Resetting user accounts..."

    if [ "$DEV_MODE" = true ]; then
        DJANGO_CMD="cd $PROJECT_DIR/backend && python manage.py"
    else
        # Make sure backend is running
        if ! docker ps --format '{{.Names}}' | grep -q "^junkbin_backend$"; then
            cd "$PROJECT_DIR"
            docker compose up -d backend
            sleep 3
        fi
        DJANGO_CMD="docker compose exec -T backend python manage.py"
    fi

    cd "$PROJECT_DIR"

    # Remove all users from the backup, then create a fresh superuser
    $DJANGO_CMD shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
count = User.objects.count()
User.objects.all().delete()
print(f'Removed {count} user account(s) from backup.')
" 2>/dev/null

    echo ""
    echo -e "  ${BOLD}Create admin account for this server:${NC}"
    echo ""

    if [ "$AUTO_YES" = true ]; then
        # Non-interactive: create default admin
        $DJANGO_CMD shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.create_superuser(username='admin', email='admin@junkbin.io', password='changeme')
print(f'Created superuser: admin / changeme')
print('CHANGE THIS PASSWORD IMMEDIATELY!')
" 2>/dev/null
        log_warn "Default admin created (admin / changeme) — change password immediately!"
    else
        # Interactive: prompt for credentials
        $DJANGO_CMD createsuperuser 2>/dev/null || {
            log_warn "Superuser creation skipped. Run 'manage.py createsuperuser' later."
        }
    fi

    log_success "User accounts reset!"
fi

# =========================================================================
# Summary
# =========================================================================
echo ""
echo -e "${BOLD}========================================"
log_success "Restore completed!"
echo ""
[ "$OPT_DATABASE" = true ]     && echo -e "  Database:  ${GREEN}Restored${NC}"
[ "$OPT_DATABASE" = false ]    && echo -e "  Database:  ${DIM}Skipped${NC}"
if [ "$OPT_MEDIA" = true ] && [ "$HAS_MEDIA" = true ]; then
    echo -e "  Media:     ${GREEN}Restored${NC}"
else
    echo -e "  Media:     ${DIM}Skipped${NC}"
fi
if [ "$OPT_RESTORE_USERS" = true ] || [ "$OPT_DATABASE" = false ]; then
    echo -e "  Users:     ${GREEN}Restored from backup${NC}"
else
    echo -e "  Users:     ${YELLOW}Reset (fresh admin)${NC}"
fi
if [ "$OPT_ENV" = true ]; then
    echo -e "  Config:    ${YELLOW}Restored (review .env!)${NC}"
else
    echo -e "  Config:    ${GREEN}Kept current${NC}"
fi
if [ "$DEV_MODE" = false ]; then
    echo -e "  Services:  ${GREEN}Restarted${NC}"
fi
echo ""
echo "  Please verify the site is working correctly."
echo -e "========================================${NC}"
echo ""
