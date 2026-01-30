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
        fedora|centos|rhel|almalinux|rocky)
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
    read -p "Enter database password: " -s DB_PASSWORD
    echo
    
    SECRET_KEY=$(generate_secret_key)
    
    cat > .env << EOF
# Junkbin.io Environment Configuration
# Generated: $(date)

# Django Settings
SECRET_KEY='${SECRET_KEY}'
DEBUG=False
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN}

# Database
DATABASE_URL=postgresql://junkbin:${DB_PASSWORD}@postgres:5432/junkbin
POSTGRES_DB=junkbin
POSTGRES_USER=junkbin
POSTGRES_PASSWORD=${DB_PASSWORD}

# Redis
REDIS_URL=redis://redis:6379/0

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
ADMIN_EMAIL=${ADMIN_EMAIL}

# Security
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
EOF
    
    chmod 600 .env
    log_info "Environment file created (.env)"
}

# Initialize database
init_database() {
    log_step "Initializing database..."
    
    docker compose up -d postgres redis
    sleep 10  # Wait for PostgreSQL to start
    
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
    
    read -p "Enter domain name: " DOMAIN
    read -p "Enter email for Let's Encrypt: " LE_EMAIL
    
    certbot certonly --nginx \
        -d $DOMAIN \
        -d www.$DOMAIN \
        --email $LE_EMAIL \
        --agree-tos \
        --non-interactive
    
    # Setup auto-renewal
    (crontab -l 2>/dev/null; echo "0 0 * * * certbot renew --quiet") | crontab -
    
    log_info "SSL certificates installed"
}

# Deploy application
deploy_app() {
    log_step "Deploying Junkbin.io..."
    
    # Build and start containers
    docker compose build
    docker compose up -d
    
    # Wait for services to be ready
    sleep 15
    
    # Collect static files
    docker compose exec -T backend python manage.py collectstatic --noinput
    
    log_info "Application deployed successfully"
}

# Setup backup cron job
setup_backups() {
    log_step "Setting up automated backups..."
    
    mkdir -p /opt/junkbin-backups
    
    # Create backup script
    cat > /opt/junkbin-backups/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/junkbin-backups"
DATE=$(date +%Y%m%d_%H%M%S)
cd /opt/junkbin.io
docker compose exec -T postgres pg_dump -U junkbin junkbin | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"
tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" backend/media/
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
EOF
    
    chmod +x /opt/junkbin-backups/backup.sh
    
    # Add to crontab (daily at 2 AM)
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/junkbin-backups/backup.sh") | crontab -
    
    log_info "Backup system configured (daily at 2 AM)"
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
    deploy_app
    setup_backups
    print_success
}

# Run main function
main "$@"
