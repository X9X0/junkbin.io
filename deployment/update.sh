#!/bin/bash

################################################################################
# Junkbin.io - Quick Update Script
#
# Pulls latest code, rebuilds containers, and runs migrations.
# For use on an already-deployed instance — not a fresh install.
#
# Usage: ./deployment/update.sh [options]
# Options:
#   --skip-pull   Skip git pull (if you already pulled manually)
#   --seed        Run seed_data after migrations
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

# Parse flags
SKIP_PULL=false
RUN_SEED=false
for arg in "$@"; do
    case $arg in
        --skip-pull) SKIP_PULL=true ;;
        --seed)      RUN_SEED=true ;;
        *)           log_error "Unknown option: $arg"; exit 1 ;;
    esac
done

# Navigate to project root (parent of deployment/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
log_info "Working directory: $PROJECT_ROOT"

# 1. Pull latest code
if [ "$SKIP_PULL" = false ]; then
    log_step "Pulling latest code..."
    git pull
else
    log_warn "Skipping git pull (--skip-pull)"
fi

# 2. Build images
log_step "Building Docker images..."
docker compose build backend frontend

# 3. Recreate containers (frontend needs volume reset for new build assets)
log_step "Stopping frontend and nginx..."
docker compose down frontend nginx

COMPOSE_PROJECT="$(docker compose config --format json | python3 -c 'import sys,json; print(json.load(sys.stdin)["name"])')"
FRONTEND_VOL="${COMPOSE_PROJECT}_frontend_build"
log_step "Removing frontend build volume ($FRONTEND_VOL)..."
docker volume rm "$FRONTEND_VOL" 2>/dev/null || true

log_step "Starting all containers..."
docker compose up -d

# 4. Run migrations
log_step "Running database migrations..."
docker compose exec backend python manage.py migrate --noinput

# 5. Collect static files
log_step "Collecting static files..."
docker compose exec backend python manage.py collectstatic --noinput

# 6. Seed data (optional)
if [ "$RUN_SEED" = true ]; then
    log_step "Running seed_data..."
    docker compose exec backend python manage.py seed_data
fi

# 7. Status summary
echo ""
log_step "Container status:"
docker compose ps
echo ""
log_info "Update complete."
