#!/bin/bash

################################################################################
# Junkbin.io - Automated Deployment Script
# "NO USER SERVICEABLE PARTS INSIDE" - We disagree.
#
# This script handles complete deployment of Junkbin.io on a fresh Linux server
# Supports: Ubuntu, Debian, Fedora, Arch Linux, CentOS, RHEL, Alma Linux, Rocky Linux
#
# Usage: sudo ./junkbin-deploy.sh [options]
# Options:
#   --update     Update existing installation
#   --backup     Backup database and files
#   --restore    Restore from backup
#   --dev        Development mode (no SSL, local only)
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# SSL certificate renewal
CERT_RENEW_LOG="${CERT_RENEW_LOG:-/var/log/junkbin-certbot-renew.log}"
CERT_WARN_DAYS="${CERT_WARN_DAYS:-21}"

# Backups. Target defaults to the project's own ./backups (set in setup_backups
# once DEPLOY_DIR is known) because that is where the off-host puller looks for
# junkbin_backup_*.tar.gz - see docs/RUNBOOK.md, "Off-host backups".
BACKUP_LOG="${BACKUP_LOG:-/var/log/junkbin-backup.log}"

# ASCII Art Banner
print_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
     _             _    _     _       _       
    | |_   _ _ __ | | _| |__ (_)_ __ (_) ___  
 _  | | | | | '_ \| |/ / '_ \| | '_ \| |/ _ \ 
| |_| | |_| | | | |   <| |_) | | | | | | (_) |
 \___/ \__,_|_| |_|_|\_\_.__/|_|_| |_|_|\___/ 
                                               
  "NO USER SERVICEABLE PARTS INSIDE"
       We respectfully disagree.
EOF
    echo -e "${NC}"
}

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Detect Linux distribution
detect_os() {
    log_step "Detecting operating system..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        log_info "Detected: $PRETTY_NAME"
    else
        log_error "Cannot detect OS. /etc/os-release not found."
        exit 1
    fi
    
    # Validate supported OS
    case "$OS" in
        ubuntu|debian|fedora|arch|centos|rhel|almalinux|rocky)
            log_info "Operating system is supported"
            ;;
        *)
            log_error "Unsupported operating system: $OS"
            log_error "Supported: Ubuntu, Debian, Fedora, Arch, CentOS, RHEL, Alma Linux, Rocky Linux"
            exit 1
            ;;
    esac
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
    log_info "Running with root privileges"
}

# Check system requirements
check_requirements() {
    log_step "Checking system requirements..."
    
    # Check RAM (minimum 2GB)
    TOTAL_RAM=$(free -m | awk 'NR==2{print $2}')
    if [ "$TOTAL_RAM" -lt 2000 ]; then
        log_warn "Less than 2GB RAM detected ($TOTAL_RAM MB). Minimum 2GB recommended."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_info "RAM check passed: ${TOTAL_RAM}MB available"
    fi
    
    # Check disk space (minimum 10GB free)
    FREE_SPACE=$(df -BG / | awk 'NR==2{print $4}' | sed 's/G//')
    if [ "$FREE_SPACE" -lt 10 ]; then
        log_warn "Less than 10GB free disk space (${FREE_SPACE}GB available)"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_info "Disk space check passed: ${FREE_SPACE}GB available"
    fi
}

# Clean up any existing containers from previous runs
cleanup_existing() {
    log_step "Cleaning up any existing containers..."

    if command -v docker &> /dev/null && docker info &> /dev/null; then
        # Stop any existing junkbin containers
        if [ -f "docker-compose.yml" ]; then
            docker compose down 2>/dev/null || true
            log_info "Stopped existing containers"
        fi
    fi
}

# Check for port conflicts
check_ports() {
    log_step "Checking for port conflicts..."

    REQUIRED_PORTS=(80 443 5432 6379)
    CONFLICTS=()

    for PORT in "${REQUIRED_PORTS[@]}"; do
        # Check if port is in use, but ignore docker-proxy (our own containers)
        if ss -tuln 2>/dev/null | grep -q ":$PORT "; then
            # Check if it's docker-proxy (from our own previous run)
            if ! ss -tlnp 2>/dev/null | grep ":$PORT " | grep -q "docker-proxy"; then
                CONFLICTS+=($PORT)
            fi
        fi
    done

    if [ ${#CONFLICTS[@]} -gt 0 ]; then
        log_error "Port conflicts detected on: ${CONFLICTS[*]}"
        log_error "Please free up these ports before continuing"
        exit 1
    else
        log_info "All required ports are available"
    fi
}

# Install dependencies based on OS
install_dependencies() {
    log_step "Installing system dependencies..."
    
    case "$OS" in
        ubuntu|debian)
            apt-get update
            apt-get install -y \
                apt-transport-https \
                ca-certificates \
                curl \
                gnupg \
                lsb-release \
                git \
                wget \
                ufw \
                fail2ban \
                certbot \
                python3-certbot-nginx
            ;;
        fedora)
            dnf update -y
            dnf install -y \
                curl \
                git \
                wget \
                firewalld \
                fail2ban \
                certbot \
                python3-certbot-nginx
            ;;
        centos|rhel|almalinux|rocky)
            dnf update -y
            dnf install -y epel-release
            dnf install -y \
                curl \
                git \
                wget \
                firewalld \
                fail2ban \
                certbot \
                python3-certbot-nginx
            ;;
        arch)
            pacman -Syu --noconfirm
            pacman -S --noconfirm \
                curl \
                git \
                wget \
                ufw \
                fail2ban \
                certbot \
                certbot-nginx
            ;;
    esac
    
    log_info "System dependencies installed"
}

# Install Node.js via nvm
install_nodejs() {
    log_step "Installing Node.js..."

    REQUIRED_NODE_MAJOR=22

    # Check if Node.js is already installed and correct version
    if command -v node &> /dev/null; then
        CURRENT_NODE=$(node --version | sed 's/v//' | cut -d. -f1)
        if [ "$CURRENT_NODE" -ge "$REQUIRED_NODE_MAJOR" ]; then
            log_info "Node.js already installed: $(node --version)"
            return
        else
            log_warn "Node.js $(node --version) is too old. Need v${REQUIRED_NODE_MAJOR}+"
        fi
    fi

    # Install nvm for the deploy user
    DEPLOY_USER=${SUDO_USER:-$USER}
    DEPLOY_HOME=$(eval echo ~$DEPLOY_USER)

    log_info "Installing nvm for user $DEPLOY_USER..."

    # Install nvm
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | sudo -u $DEPLOY_USER bash

    # Source nvm and install Node
    export NVM_DIR="$DEPLOY_HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

    # Install Node 22 LTS
    sudo -u $DEPLOY_USER bash -c "
        export NVM_DIR='$DEPLOY_HOME/.nvm'
        [ -s \"\$NVM_DIR/nvm.sh\" ] && \. \"\$NVM_DIR/nvm.sh\"
        nvm install $REQUIRED_NODE_MAJOR
        nvm alias default $REQUIRED_NODE_MAJOR
        nvm use default
    "

    log_info "Node.js v${REQUIRED_NODE_MAJOR} installed via nvm"
}

# Build frontend
build_frontend() {
    log_step "Building frontend..."

    DEPLOY_USER=${SUDO_USER:-$USER}
    DEPLOY_HOME=$(eval echo ~$DEPLOY_USER)

    cd frontend

    # Use nvm to ensure correct Node version
    sudo -u $DEPLOY_USER bash -c "
        set -e
        export NVM_DIR='$DEPLOY_HOME/.nvm'
        [ -s \"\$NVM_DIR/nvm.sh\" ] && \. \"\$NVM_DIR/nvm.sh\"
        cd '$PWD'

        # Read .nvmrc if present
        if [ -f .nvmrc ]; then
            nvm use
        fi

        npm ci && npm run build
    "

    cd ..
    log_info "Frontend built successfully"
}

# Install Docker
install_docker() {
    log_step "Installing Docker..."

    if ! command -v docker &> /dev/null; then
        # Docker not installed, install it
        case "$OS" in
            ubuntu|debian)
                # Add Docker's official GPG key
                install -m 0755 -d /etc/apt/keyrings
                curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
                chmod a+r /etc/apt/keyrings/docker.gpg

                # Add Docker repository
                echo \
                  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
                  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
                  tee /etc/apt/sources.list.d/docker.list > /dev/null

                apt-get update
                apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;
            fedora)
                dnf -y install dnf-plugins-core
                dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
                dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;
            centos|rhel|almalinux|rocky)
                dnf -y install dnf-plugins-core
                dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
                dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;
            arch)
                pacman -S --noconfirm docker docker-compose
                ;;
        esac
        log_info "Docker installed: $(docker --version)"
    else
        log_info "Docker already installed: $(docker --version)"
    fi

    # Always ensure Docker is running and enabled
    if ! systemctl is-active --quiet docker; then
        log_info "Starting Docker daemon..."
        systemctl start docker
    fi
    systemctl enable docker

    log_info "Docker daemon is running"
}

# Configure firewall
configure_firewall() {
    log_step "Configuring firewall..."
    
    case "$OS" in
        ubuntu|debian|arch)
            # Use UFW
            ufw --force reset
            ufw default deny incoming
            ufw default allow outgoing
            ufw allow 22/tcp   # SSH
            ufw allow 80/tcp   # HTTP
            ufw allow 443/tcp  # HTTPS
            ufw --force enable
            log_info "UFW firewall configured"
            ;;
        fedora|centos|rhel|almalinux|rocky)
            # Use firewalld
            systemctl start firewalld
            systemctl enable firewalld
            firewall-cmd --permanent --add-service=ssh
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            firewall-cmd --reload
            log_info "Firewalld configured"
            ;;
    esac
}

# Configure fail2ban
configure_fail2ban() {
    log_step "Configuring fail2ban..."
    
    cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log
backend = systemd

[nginx-http-auth]
enabled = true
port = 80,443
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port = 80,443
logpath = /var/log/nginx/error.log
EOF
    
    systemctl enable fail2ban
    systemctl restart fail2ban
    log_info "Fail2ban configured"
}

# Generate random secret key
generate_secret_key() {
    openssl rand -base64 64 | tr -d '\n'
}

# Create .env file
create_env_file() {
    log_step "Creating environment configuration..."

    read -p "Enter domain name (e.g., junkbin.io): " DOMAIN
    read -p "Enter admin email: " ADMIN_EMAIL

    # Export for use in other functions
    export DOMAIN
    export ADMIN_EMAIL

    # Auto-generate a URL-safe database password (alphanumeric only)
    # This avoids URL-parsing issues in DATABASE_URL when passwords
    # contain special characters like @ : / ? #
    DB_PASSWORD=$(tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 48)

    # Get server IP for ALLOWED_HOSTS
    SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')

    SECRET_KEY=$(generate_secret_key)

    cat > .env << EOF
# Junkbin.io Environment Configuration
# Generated: $(date)

# Django Settings
SECRET_KEY='${SECRET_KEY}'
DEBUG=False
DJANGO_SETTINGS_MODULE=config.settings.production
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN},${SERVER_IP},localhost,127.0.0.1,backend

# Database
DATABASE_URL=postgresql://junkbin:${DB_PASSWORD}@postgres:5432/junkbin
POSTGRES_DB=junkbin
POSTGRES_USER=junkbin
POSTGRES_PASSWORD=${DB_PASSWORD}

# Redis
REDIS_URL=redis://redis:6379/0

# CORS & CSRF (must match the live domain with HTTPS)
CORS_ALLOWED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}
CSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=${ADMIN_EMAIL}
EMAIL_HOST_PASSWORD=

# OAuth (Configure later)
OAUTH_GOOGLE_CLIENT_ID=
OAUTH_GOOGLE_CLIENT_SECRET=

# Storage
STORAGE_BACKEND=local
MEDIA_ROOT=/app/media

# Site Settings
SITE_URL=https://${DOMAIN}
FRONTEND_URL=https://${DOMAIN}
ADMIN_EMAIL=${ADMIN_EMAIL}

# Security
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
AUTH_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
CSP_UPGRADE_INSECURE=True
EOF
    
    chmod 600 .env
    log_info "Environment file created (.env)"
}

# Initialize database
init_database() {
    log_step "Initializing database..."

    # On fresh deploys, remove existing postgres volume so it re-initializes
    # with the new password. PostgreSQL only reads POSTGRES_PASSWORD on first
    # init — if a volume exists from a previous (failed) deploy, the password
    # in .env won't match. Skip this on --update to preserve production data.
    if [ "$UPDATE_MODE" = false ]; then
        PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')
        PG_VOLUME="${PROJECT_NAME}_postgres_data"
        if docker volume ls -q | grep -q "^${PG_VOLUME}$"; then
            log_warn "Removing existing postgres data volume to re-initialize with new credentials..."
            docker compose down postgres 2>/dev/null || true
            docker volume rm "$PG_VOLUME" 2>/dev/null || true
        fi
    fi

    # Build backend image first
    log_info "Building backend container..."
    docker compose build backend

    # Start database services and backend
    log_info "Starting database services..."
    docker compose up -d postgres redis
    sleep 10  # Wait for PostgreSQL to start

    # Start backend container
    log_info "Starting backend container..."
    docker compose up -d backend
    sleep 5  # Wait for backend to start

    docker compose exec -T backend python manage.py migrate
    log_info "Database migrations completed"

    # Create superuser
    log_info "Creating admin superuser..."
    docker compose exec -T backend python manage.py createsuperuser --noinput || true
}

# Setup SSL certificates
setup_ssl() {
    log_step "Setting up SSL certificates..."

    if [ "$DEV_MODE" = true ]; then
        log_warn "Development mode - skipping SSL setup"
        return
    fi

    # Check if certificates already exist
    if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
        log_info "SSL certificates already exist for ${DOMAIN}"
        return
    fi

    # Install certbot + certbot-dns-hostinger in a dedicated venv so the plugin
    # is always visible to certbot regardless of the system Python environment.
    # This is required on RHEL/AlmaLinux/Rocky where dnf-installed certbot uses
    # a different Python env than pip3.
    if [ ! -x /opt/certbot/bin/certbot ]; then
        log_info "Installing certbot in /opt/certbot venv..."
        case "$OS" in
            ubuntu|debian)
                apt-get install -y python3 python3-venv python3-pip
                ;;
            fedora|centos|rhel|almalinux|rocky)
                dnf install -y python3 python3-pip
                ;;
            arch)
                pacman -S --noconfirm python python-pip
                ;;
        esac
        python3 -m venv /opt/certbot
        /opt/certbot/bin/pip install --quiet --upgrade pip
        /opt/certbot/bin/pip install --quiet certbot certbot-dns-hostinger
        ln -sf /opt/certbot/bin/certbot /usr/local/bin/certbot
        log_info "certbot + certbot-dns-hostinger installed in /opt/certbot"
    elif ! /opt/certbot/bin/pip show certbot-dns-hostinger &> /dev/null; then
        log_info "Installing certbot-dns-hostinger plugin..."
        /opt/certbot/bin/pip install --quiet certbot-dns-hostinger
    fi

    # Create Hostinger DNS credentials file
    if [ ! -f /etc/letsencrypt/hostinger.ini ]; then
        if [ -z "${HOSTINGER_API_TOKEN:-}" ]; then
            read -p "Enter Hostinger API token (for DNS challenge): " HOSTINGER_API_TOKEN
        fi
        mkdir -p /etc/letsencrypt
        echo "dns_hostinger_api_token = ${HOSTINGER_API_TOKEN}" > /etc/letsencrypt/hostinger.ini
        chmod 600 /etc/letsencrypt/hostinger.ini
        log_info "Hostinger credentials saved to /etc/letsencrypt/hostinger.ini"
    fi

    # Get certificates using DNS challenge (works behind firewalls, supports auto-renewal)
    log_info "Requesting SSL certificate for ${DOMAIN} via DNS challenge..."
    /usr/local/bin/certbot certonly --authenticator dns-hostinger \
        --dns-hostinger-credentials /etc/letsencrypt/hostinger.ini \
        -d ${DOMAIN} \
        -d www.${DOMAIN} \
        --email ${ADMIN_EMAIL} \
        --agree-tos \
        --non-interactive

    # Get certificate for translate subdomain
    log_info "Requesting SSL certificate for translate.${DOMAIN} via DNS challenge..."
    /usr/local/bin/certbot certonly --authenticator dns-hostinger \
        --dns-hostinger-credentials /etc/letsencrypt/hostinger.ini \
        -d translate.${DOMAIN} \
        --email ${ADMIN_EMAIL} \
        --agree-tos \
        --non-interactive

    if [ $? -eq 0 ]; then
        log_info "SSL certificates installed successfully"
    else
        log_warn "SSL certificate acquisition failed - site will run on HTTP only"
    fi
}

# Setup certbot auto-renewal cron job
# Note: certbot's systemd timer only renews the cert files — it does NOT reload
# nginx inside Docker. This cron job handles both: renewal + nginx reload.
#
# The renewal MUST invoke the /opt/certbot venv binary by absolute path. The
# renewal configs specify `authenticator = dns-hostinger`, and that plugin lives
# only in the venv (see setup_ssl). cron's PATH is /usr/bin:/bin — it does not
# include the /usr/local/bin symlink — so a bare `certbot` resolves to the
# distro package from install_dependencies(), which has no dns-hostinger plugin
# and fails on every run. That silently expired the certs once already.
setup_cert_renewal() {
    log_step "Setting up SSL certificate auto-renewal..."

    if [ "$DEV_MODE" = true ]; then
        log_warn "Development mode - skipping cert renewal setup"
        return
    fi

    DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

    # Prefer the venv certbot (has certbot-dns-hostinger); fall back to system.
    if [ -x /opt/certbot/bin/certbot ]; then
        CERTBOT_BIN=/opt/certbot/bin/certbot
    else
        CERTBOT_BIN="$(command -v certbot || echo /usr/bin/certbot)"
        log_warn "/opt/certbot venv missing - using ${CERTBOT_BIN}, which may lack the dns-hostinger plugin"
    fi

    DOCKER_BIN="$(command -v docker || echo /usr/bin/docker)"

    # --deploy-hook fires only when a cert was actually renewed, so nginx is
    # reloaded on renewal rather than twice a day regardless. Output is appended
    # to a log rather than --quiet'd into the void, so a failing renewal leaves
    # a trail instead of expiring in silence.
    RENEWAL_CMD="${CERTBOT_BIN} renew --deploy-hook '${DOCKER_BIN} compose -f ${DEPLOY_DIR}/docker-compose.yml exec -T nginx nginx -s reload' >> ${CERT_RENEW_LOG} 2>&1"

    # Replace any existing entry rather than skipping: re-running this installer
    # must repair a stale or broken renewal line, not leave it in place.
    if crontab -l 2>/dev/null | grep -q "certbot renew"; then
        crontab -l 2>/dev/null | grep -v "certbot renew" | crontab -
        log_info "Removed stale cert renewal cron entry"
    fi
    (crontab -l 2>/dev/null; echo "0 3,15 * * * ${RENEWAL_CMD}") | crontab -
    log_info "Cert renewal cron installed (03:00 and 15:00 daily, logging to ${CERT_RENEW_LOG})"

    install_cert_monitor
}

# Install the certificate expiry monitor (systemd timer, daily).
# The renewal cron above fixes the known failure; this catches the next unknown
# one by alerting on days-until-expiry regardless of *why* renewal stalled.
install_cert_monitor() {
    DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

    if [ ! -f "${DEPLOY_DIR}/deployment/cert-monitor.sh" ]; then
        log_warn "cert-monitor.sh not found - skipping expiry monitor"
        return
    fi

    chmod +x "${DEPLOY_DIR}/deployment/cert-monitor.sh"

    # Without this the monitor's alerts go to local mail for root, which nobody
    # reads - that is half of why the Sep 2026 expiry went unnoticed.
    cat > /etc/default/junkbin-monitor << ENVEOF
JUNKBIN_ADMIN_EMAIL=${ADMIN_EMAIL:-root}
JUNKBIN_DOMAIN=${DOMAIN}
JUNKBIN_DIR=${DEPLOY_DIR}
JUNKBIN_CERT_HOSTS="${DOMAIN} www.${DOMAIN} translate.${DOMAIN}"
CERT_RENEW_LOG=${CERT_RENEW_LOG}
CERT_WARN_DAYS=${CERT_WARN_DAYS}
ENVEOF
    chmod 644 /etc/default/junkbin-monitor

    install_systemd_unit "${DEPLOY_DIR}/deployment/systemd/junkbin-cert-monitor.service"
    install_systemd_unit "${DEPLOY_DIR}/deployment/systemd/junkbin-cert-monitor.timer"

    systemctl daemon-reload
    systemctl enable --now junkbin-cert-monitor.timer
    log_info "Cert expiry monitor enabled (daily; warns at ${CERT_WARN_DAYS:-21} days)"
}

# Deploy application
deploy_app() {
    log_step "Deploying Junkbin.io..."

    # Clear frontend build volume to prevent stale builds
    log_info "Clearing frontend build volume..."
    docker compose down frontend nginx 2>/dev/null || true

    # Get the volume name (project name + volume name)
    PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')
    VOLUME_NAME="${PROJECT_NAME}_frontend_build"

    # Remove the frontend build volume if it exists
    if docker volume ls -q | grep -q "^${VOLUME_NAME}$"; then
        docker volume rm "$VOLUME_NAME" 2>/dev/null || true
        log_info "Removed stale frontend build volume"
    fi

    # Build and start containers
    docker compose build
    docker compose up -d

    # Wait for services to be ready
    sleep 15

    # Collect static files
    docker compose exec -T backend python manage.py collectstatic --noinput

    # Compile translation files (.po -> .mo)
    docker compose exec -T backend python manage.py compilemessages || true

    log_info "Application deployed successfully"
}

# Setup logrotate for nginx logs
setup_logrotate() {
    log_step "Setting up log rotation..."

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    LOGROTATE_SRC="$SCRIPT_DIR/logrotate/junkbin"

    if [ ! -f "$LOGROTATE_SRC" ]; then
        # Fallback: look relative to project root
        LOGROTATE_SRC="$(pwd)/deployment/logrotate/junkbin"
    fi

    if [ -f "$LOGROTATE_SRC" ]; then
        cp "$LOGROTATE_SRC" /etc/logrotate.d/junkbin
        chmod 644 /etc/logrotate.d/junkbin
        log_info "Logrotate config installed to /etc/logrotate.d/junkbin"
    else
        log_warn "Logrotate config not found at $LOGROTATE_SRC — skipping"
    fi
}

# Install a systemd unit, substituting __DEPLOY_DIR__ with the real install path.
# The shipped units use that placeholder rather than a literal path: they used to
# hardcode /opt/junkbin.io, which exists on no environment we run - prod is
# /root/junkbin.io and the dev VM is /home/scap/junkbin.io. Nothing has broken
# from this yet only because these units are not currently installed on prod at
# all; installing them as-shipped would have given junkbin.service a nonexistent
# WorkingDirectory and the disk monitor a nonexistent ExecStart.
install_systemd_unit() {
    local src="$1" name
    name="$(basename "$src")"

    if [ ! -f "$src" ]; then
        log_warn "${name} not found — skipping"
        return 1
    fi

    sed "s|__DEPLOY_DIR__|${DEPLOY_DIR}|g" "$src" > "/etc/systemd/system/${name}"
    log_info "Installed ${name}"
}

# Setup systemd service and disk monitor
setup_systemd() {
    log_step "Setting up systemd services..."

    DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    SYSTEMD_SRC="${DEPLOY_DIR}/deployment/systemd"

    install_systemd_unit "$SYSTEMD_SRC/junkbin.service"

    if install_systemd_unit "$SYSTEMD_SRC/junkbin-disk-monitor.service"; then
        install_systemd_unit "$SYSTEMD_SRC/junkbin-disk-monitor.timer"
        chmod +x "${DEPLOY_DIR}/deployment/disk-monitor.sh" 2>/dev/null || true
    fi

    systemctl daemon-reload

    # Enable services
    systemctl enable junkbin.service 2>/dev/null || true
    systemctl enable --now junkbin-disk-monitor.timer 2>/dev/null || true

    log_info "Systemd services configured"
}

# Setup backup cron job
#
# This used to write its own inline backup script and cron that, while the real
# deployment/backup.sh sat unused. The inline version was silently broken:
#   - it cd'd to a hardcoded /opt/junkbin.io with no `|| exit`
#   - `pg_dump | gzip` without pipefail writes a valid 20-byte empty archive when
#     pg_dump fails, so a total failure still looked like a successful backup
#   - combined with `find -mtime +30 -delete`, 30 days of that silently deleted
#     every genuine backup
#   - it tarred ./backend/media, but media lives in the media_files Docker volume
#     at /app/media and nothing bind-mounts that path
# deployment/backup.sh gets all of this right, so cron that instead.
setup_backups() {
    log_step "Setting up automated backups..."

    DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    BACKUP_SCRIPT="${DEPLOY_DIR}/deployment/backup.sh"

    if [ ! -f "$BACKUP_SCRIPT" ]; then
        log_warn "deployment/backup.sh not found — skipping backup setup"
        return
    fi

    # Must stay ./backups: the off-host pull job fetches junkbin_backup_*.tar.gz
    # from there twice daily. Writing anywhere else silently orphans off-host
    # backups while the local ones still look fine.
    BACKUP_TARGET_DIR="${BACKUP_TARGET_DIR:-${DEPLOY_DIR}/backups}"

    mkdir -p "$BACKUP_TARGET_DIR"
    chmod +x "$BACKUP_SCRIPT"

    # On failure, echo to stdout so cron mails the operator - backup.sh runs
    # under `set -e` and exits non-zero if a container is missing or pg_dump dies.
    BACKUP_CMD="${BACKUP_SCRIPT} ${BACKUP_TARGET_DIR} >> ${BACKUP_LOG} 2>&1 || echo \"Junkbin backup FAILED - see ${BACKUP_LOG}\""

    # Replace any existing entry, including the old /opt/junkbin-backups/backup.sh
    # line, so re-running this installer repairs a broken backup rather than
    # leaving it in place.
    if crontab -l 2>/dev/null | grep -qE "junkbin-backups/backup.sh|deployment/backup.sh"; then
        crontab -l 2>/dev/null | grep -vE "junkbin-backups/backup.sh|deployment/backup.sh" | crontab -
        log_info "Removed stale backup cron entry"
    fi
    # 02:00 and 14:00, matching what prod already runs: the off-host pull job
    # fetches at ~02:15 and ~14:15, so a once-daily backup would leave the
    # afternoon pull with nothing new to collect.
    (crontab -l 2>/dev/null; echo "0 2,14 * * * ${BACKUP_CMD}") | crontab -

    log_info "Backup cron installed (02:00 and 14:00 -> ${BACKUP_TARGET_DIR}, logging to ${BACKUP_LOG})"
}

# Print success message
print_success() {
    echo -e "${GREEN}"
    cat << EOF

================================================================================
                    DEPLOYMENT SUCCESSFUL!
================================================================================

Junkbin.io is now running!

Access Points:
  - Web Interface: https://$DOMAIN
  - Admin Panel: https://$DOMAIN/admin
  
Next Steps:
  1. Configure OAuth credentials in .env file
  2. Configure email settings in .env file
  3. Restart services: docker compose restart
  4. Visit admin panel to create initial content
  
Useful Commands:
  - View logs: docker compose logs -f
  - Restart: docker compose restart
  - Stop: docker compose down
  - Update: ./junkbin-deploy.sh --update
  - Backup: ./junkbin-deploy.sh --backup

Documentation: /opt/junkbin.io/docs/

Support: https://github.com/yourusername/junkbin.io/issues

"NO USER SERVICEABLE PARTS INSIDE" - We proved them wrong!

================================================================================
EOF
    echo -e "${NC}"
}

# Main deployment function
main() {
    print_banner
    
    # Parse arguments
    DEV_MODE=false
    UPDATE_MODE=false
    BACKUP_MODE=false
    RESTORE_MODE=false
    
    for arg in "$@"; do
        case $arg in
            --dev) DEV_MODE=true ;;
            --update) UPDATE_MODE=true ;;
            --backup) BACKUP_MODE=true ;;
            --restore) RESTORE_MODE=true ;;
        esac
    done
    
    # Run deployment steps
    check_root
    detect_os
    check_requirements
    cleanup_existing
    check_ports
    install_dependencies
    install_nodejs
    install_docker
    configure_firewall
    configure_fail2ban
    create_env_file
    build_frontend
    init_database
    setup_ssl
    setup_cert_renewal
    deploy_app
    setup_logrotate
    setup_systemd
    setup_backups
    print_success
}

# Run main function
main "$@"
