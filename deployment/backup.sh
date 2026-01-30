#!/bin/bash
#
# Junkbin.io Backup Script
# Creates backups of database and media files
#
# Usage: ./backup.sh [backup_dir]
#
# "NO USER SERVICEABLE PARTS INSIDE" - But we back them up anyway
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
BACKUP_DIR="${1:-$PROJECT_DIR/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="junkbin_backup_$TIMESTAMP"

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)
fi

# Default values if not in .env
DB_NAME="${POSTGRES_DB:-junkbin}"
DB_USER="${POSTGRES_USER:-junkbin}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
MEDIA_DIR="${PROJECT_DIR}/backend/media"

print_status() {
    echo -e "${CYAN}[BACKUP]${NC} $1"
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
echo "  Junkbin.io Backup Script"
echo "  NO USER SERVICEABLE PARTS INSIDE"
echo "========================================"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup database
print_status "Backing up PostgreSQL database..."

if command -v docker &> /dev/null && docker ps --format '{{.Names}}' | grep -q "junkbin.*postgres"; then
    # Database is running in Docker
    print_status "Using Docker container for database backup..."
    docker exec junkbin-postgres pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_DIR/$BACKUP_NAME/database.sql"
elif command -v pg_dump &> /dev/null; then
    # Use local pg_dump
    PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" > "$BACKUP_DIR/$BACKUP_NAME/database.sql"
else
    print_error "pg_dump not found. Please install PostgreSQL client tools."
    exit 1
fi

if [ -f "$BACKUP_DIR/$BACKUP_NAME/database.sql" ]; then
    DB_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME/database.sql" | cut -f1)
    print_success "Database backup complete ($DB_SIZE)"
else
    print_error "Database backup failed!"
    exit 1
fi

# Backup media files
print_status "Backing up media files..."

if [ -d "$MEDIA_DIR" ]; then
    tar -czf "$BACKUP_DIR/$BACKUP_NAME/media.tar.gz" -C "$PROJECT_DIR/backend" media
    MEDIA_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME/media.tar.gz" | cut -f1)
    print_success "Media backup complete ($MEDIA_SIZE)"
else
    print_warning "Media directory not found, skipping..."
fi

# Backup schematics (separate for potentially large files)
SCHEMATICS_DIR="${PROJECT_DIR}/backend/media/schematics"
if [ -d "$SCHEMATICS_DIR" ] && [ "$(ls -A $SCHEMATICS_DIR 2>/dev/null)" ]; then
    print_status "Backing up schematics..."
    tar -czf "$BACKUP_DIR/$BACKUP_NAME/schematics.tar.gz" -C "$PROJECT_DIR/backend/media" schematics
    SCHEMA_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME/schematics.tar.gz" | cut -f1)
    print_success "Schematics backup complete ($SCHEMA_SIZE)"
fi

# Backup .env file (encrypted or with warning)
print_status "Backing up configuration..."
if [ -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env" "$BACKUP_DIR/$BACKUP_NAME/.env.backup"
    print_warning "Environment file backed up - contains secrets, store securely!"
fi

# Create backup manifest
print_status "Creating backup manifest..."
cat > "$BACKUP_DIR/$BACKUP_NAME/manifest.txt" << EOF
Junkbin.io Backup Manifest
==========================
Backup Name: $BACKUP_NAME
Created: $(date)
Hostname: $(hostname)

Contents:
- database.sql: PostgreSQL database dump
- media.tar.gz: User uploaded images and files
- schematics.tar.gz: Schematic files (if present)
- .env.backup: Environment configuration (SENSITIVE)

Database: $DB_NAME
Database Host: $DB_HOST

To restore, use: ./restore.sh $BACKUP_DIR/$BACKUP_NAME

"NO USER SERVICEABLE PARTS INSIDE" - We took that personally.
EOF

# Create compressed archive of entire backup
print_status "Compressing backup archive..."
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

FINAL_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)

# Cleanup old backups (keep last 30 days)
print_status "Cleaning up old backups (keeping last 30 days)..."
find "$BACKUP_DIR" -name "junkbin_backup_*.tar.gz" -mtime +30 -delete 2>/dev/null || true

echo ""
echo "========================================"
print_success "Backup completed successfully!"
echo ""
echo "  Backup file: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo "  Total size:  $FINAL_SIZE"
echo ""
echo "  Store this backup securely - it contains"
echo "  database content and configuration secrets."
echo "========================================"
echo ""
