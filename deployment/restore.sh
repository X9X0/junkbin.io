#!/bin/bash
#
# Junkbin.io Restore Script
# Restores database and media files from backup
#
# Usage: ./restore.sh <backup_file_or_directory>
#
# "NO USER SERVICEABLE PARTS INSIDE" - Time to put it back together
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_PATH="$1"

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)
fi

# Default values
DB_NAME="${POSTGRES_DB:-junkbin}"
DB_USER="${POSTGRES_USER:-junkbin}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
MEDIA_DIR="${PROJECT_DIR}/backend/media"

print_status() {
    echo -e "${CYAN}[RESTORE]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo ""
echo "========================================"
echo "  Junkbin.io Restore Script"
echo "  NO USER SERVICEABLE PARTS INSIDE"
echo "========================================"
echo ""

# Validate input
if [ -z "$BACKUP_PATH" ]; then
    print_error "Usage: $0 <backup_file_or_directory>"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/junkbin_backup_20240101_120000.tar.gz"
    echo "  $0 /path/to/junkbin_backup_20240101_120000/"
    exit 1
fi

# Check if backup exists
if [ ! -e "$BACKUP_PATH" ]; then
    print_error "Backup not found: $BACKUP_PATH"
    exit 1
fi

# Create temp directory for extraction
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Extract if tar.gz
if [[ "$BACKUP_PATH" == *.tar.gz ]]; then
    print_status "Extracting backup archive..."
    tar -xzf "$BACKUP_PATH" -C "$TEMP_DIR"
    BACKUP_DIR=$(ls "$TEMP_DIR")
    RESTORE_DIR="$TEMP_DIR/$BACKUP_DIR"
else
    RESTORE_DIR="$BACKUP_PATH"
fi

# Verify backup contents
if [ ! -f "$RESTORE_DIR/database.sql" ]; then
    print_error "Invalid backup: database.sql not found"
    exit 1
fi

print_status "Backup contents:"
ls -la "$RESTORE_DIR"
echo ""

# Confirmation
echo -e "${YELLOW}WARNING: This will overwrite the current database and media files!${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    print_status "Restore cancelled."
    exit 0
fi

# Stop services
print_status "Stopping services..."
if command -v docker &> /dev/null && docker ps --format '{{.Names}}' | grep -q "junkbin"; then
    cd "$PROJECT_DIR"
    docker compose stop backend celery || true
fi

# Restore database
print_status "Restoring database..."

if command -v docker &> /dev/null && docker ps --format '{{.Names}}' | grep -q "junkbin.*postgres"; then
    # Database is running in Docker
    print_status "Using Docker container for database restore..."

    # Drop and recreate database
    docker exec junkbin-postgres psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS ${DB_NAME};" postgres || true
    docker exec junkbin-postgres psql -U "$DB_USER" -c "CREATE DATABASE ${DB_NAME};" postgres

    # Restore
    cat "$RESTORE_DIR/database.sql" | docker exec -i junkbin-postgres psql -U "$DB_USER" "$DB_NAME"
elif command -v psql &> /dev/null; then
    # Use local psql
    print_status "Using local PostgreSQL client..."

    # Drop and recreate database
    PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE IF EXISTS ${DB_NAME};" postgres || true
    PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE ${DB_NAME};" postgres

    # Restore
    PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" < "$RESTORE_DIR/database.sql"
else
    print_error "psql not found. Please install PostgreSQL client tools."
    exit 1
fi

print_success "Database restored successfully!"

# Restore media files
if [ -f "$RESTORE_DIR/media.tar.gz" ]; then
    print_status "Restoring media files..."

    # Backup existing media (just in case)
    if [ -d "$MEDIA_DIR" ]; then
        mv "$MEDIA_DIR" "${MEDIA_DIR}.old.$(date +%s)" || true
    fi

    mkdir -p "$PROJECT_DIR/backend"
    tar -xzf "$RESTORE_DIR/media.tar.gz" -C "$PROJECT_DIR/backend"

    print_success "Media files restored!"
else
    print_warning "No media backup found, skipping..."
fi

# Restore schematics
if [ -f "$RESTORE_DIR/schematics.tar.gz" ]; then
    print_status "Restoring schematics..."
    mkdir -p "$PROJECT_DIR/backend/media"
    tar -xzf "$RESTORE_DIR/schematics.tar.gz" -C "$PROJECT_DIR/backend/media"
    print_success "Schematics restored!"
fi

# Optionally restore .env
if [ -f "$RESTORE_DIR/.env.backup" ]; then
    echo ""
    read -p "Restore environment configuration (.env)? (yes/no): " RESTORE_ENV
    if [ "$RESTORE_ENV" == "yes" ]; then
        cp "$RESTORE_DIR/.env.backup" "$PROJECT_DIR/.env"
        print_success "Environment configuration restored!"
    fi
fi

# Restart services
print_status "Restarting services..."
if command -v docker &> /dev/null && [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
    cd "$PROJECT_DIR"
    docker compose up -d
fi

# Run migrations (in case of schema changes)
print_status "Running database migrations..."
if command -v docker &> /dev/null && docker ps --format '{{.Names}}' | grep -q "junkbin.*backend"; then
    docker exec junkbin-backend python manage.py migrate --noinput || true
fi

echo ""
echo "========================================"
print_success "Restore completed successfully!"
echo ""
echo "  Database:  Restored"
echo "  Media:     Restored"
echo "  Services:  Restarted"
echo ""
echo "  Please verify the site is working correctly."
echo "========================================"
echo ""
