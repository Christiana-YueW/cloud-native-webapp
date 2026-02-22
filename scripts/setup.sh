#!/bin/bash

# ============================================================================
# Application Setup Script for Ubuntu 24.04 LTS
# ============================================================================
# This script sets up the FastAPI web application on a fresh Ubuntu 24.04
# server (AMI build time). Database configuration is injected at runtime
# via EC2 User Data — NOT during AMI build.
#
# Usage:
#   sudo bash scripts/setup.sh [path-to-app.zip]
#
# Assignment 5 - CSYE 6225
# ============================================================================

set -euo pipefail

# ============================================================================
# Configuration Variables
# ============================================================================
APP_USER="csye6225"
APP_GROUP="csye6225"
APP_DIR="/opt/csye6225"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

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

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# ============================================================================
# Step 1: Update Package Lists & Install System Dependencies
# ============================================================================
install_system_deps() {
    log_step "Step 1: Updating package lists and installing system dependencies..."

    apt-get update -y

    apt-get install -y \
        unzip \
        python3 \
        python3-pip \
        python3-venv \
        libpq-dev \
        netcat-openbsd

    # Clean up apt cache to reduce AMI size
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    log_info "✓ System dependencies installed"
    echo ""
}

# ============================================================================
# Step 2: Create Application Linux Group
# ============================================================================
create_app_group() {
    log_step "Step 2: Creating application group..."

    if getent group "$APP_GROUP" > /dev/null 2>&1; then
        log_warn "Group '$APP_GROUP' already exists"
    else
        groupadd "$APP_GROUP"
        log_info "✓ Group '$APP_GROUP' created successfully"
    fi

    echo ""
}

# ============================================================================
# Step 3: Create Application User Account
# ============================================================================
create_app_user() {
    log_step "Step 3: Creating application user..."

    if id "$APP_USER" &>/dev/null; then
        log_warn "User '$APP_USER' already exists"
    else
        log_info "Creating system user '$APP_USER' (non-login)..."
        useradd -r -s /usr/sbin/nologin -g "$APP_GROUP" -d "$APP_DIR" -M "$APP_USER"
        log_info "✓ Non-login user '$APP_USER' created successfully"
    fi

    echo ""
}

# ============================================================================
# Step 4: Deploy Application Files
# ============================================================================
deploy_application() {
    log_step "Step 4: Deploying application files..."

    # Create application directory
    if [ ! -d "$APP_DIR" ]; then
        log_info "Creating application directory: $APP_DIR"
        mkdir -p "$APP_DIR"
    else
        log_warn "Directory $APP_DIR already exists"
    fi

    # Extract application archive if provided
    if [ $# -gt 0 ] && [ -f "$1" ]; then
        APP_ARCHIVE="$1"
        log_info "Extracting application files from: $APP_ARCHIVE"

        if [[ "$APP_ARCHIVE" == *.zip ]]; then
            unzip -o "$APP_ARCHIVE" -d "$APP_DIR"
        elif [[ "$APP_ARCHIVE" == *.tar.gz ]] || [[ "$APP_ARCHIVE" == *.tgz ]]; then
            tar -xzf "$APP_ARCHIVE" -C "$APP_DIR"
        elif [[ "$APP_ARCHIVE" == *.tar ]]; then
            tar -xf "$APP_ARCHIVE" -C "$APP_DIR"
        else
            log_error "Unsupported archive format: $APP_ARCHIVE"
            exit 1
        fi

        log_info "✓ Application files extracted successfully"

        # Flatten nested directory structure if needed
        SUBDIRS=($(find "$APP_DIR" -mindepth 1 -maxdepth 1 -type d))
        if [ ${#SUBDIRS[@]} -eq 1 ] && [ ! -f "$APP_DIR/requirements.txt" ]; then
            NESTED_DIR="${SUBDIRS[0]}"
            log_warn "Detected nested directory structure, flattening..."
            shopt -s dotglob
            mv "$NESTED_DIR"/* "$APP_DIR/" 2>/dev/null || true
            shopt -u dotglob
            rmdir "$NESTED_DIR" 2>/dev/null || true
            log_info "✓ Directory structure flattened"
        fi
    else
        if [ "$(ls -A $APP_DIR 2>/dev/null)" ]; then
            log_warn "Application files already present in $APP_DIR"
        else
            log_error "No application archive provided and directory is empty"
            exit 1
        fi
    fi

    # Verify critical files exist
    if [ ! -d "$APP_DIR/app" ]; then
        log_error "Application directory 'app/' not found in $APP_DIR"
        ls -la "$APP_DIR"
        exit 1
    fi

    if [ ! -f "$APP_DIR/requirements.txt" ]; then
        log_error "requirements.txt not found in $APP_DIR"
        exit 1
    fi

    # Create virtual environment
    if [ ! -d "$APP_DIR/venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv "$APP_DIR/venv"
        log_info "✓ Virtual environment created"
    else
        log_warn "Virtual environment already exists"
    fi

    # Install Python packages (including boto3 for S3)
    log_info "Installing Python packages from requirements.txt..."
    "$APP_DIR/venv/bin/pip" install --upgrade pip
    "$APP_DIR/venv/bin/pip" install --no-cache-dir -r "$APP_DIR/requirements.txt"
    log_info "✓ Python packages installed (including boto3)"

    # Verify uvicorn is installed
    if ! "$APP_DIR/venv/bin/pip" show uvicorn > /dev/null 2>&1; then
        log_error "uvicorn not installed — check requirements.txt"
        exit 1
    fi
    log_info "✓ uvicorn verified"

    # Create empty .env placeholder — real values injected by EC2 User Data at runtime
    if [ ! -f "$APP_DIR/.env" ]; then
        log_info "Creating .env placeholder (values injected at runtime by EC2 User Data)..."
        touch "$APP_DIR/.env"
        chmod 600 "$APP_DIR/.env"
        log_info "✓ .env placeholder created"
    else
        log_warn ".env file already exists"
    fi

    log_info "✓ Application deployment completed"
    echo ""
}

# ============================================================================
# Step 5: Set File Permissions
# ============================================================================
set_permissions() {
    log_step "Step 5: Setting file permissions..."

    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

    if [ -d "$APP_DIR/app" ]; then
        find "$APP_DIR/app" -type d -exec chmod 750 {} \; 2>/dev/null || true
        find "$APP_DIR/app" -type f -exec chmod 640 {} \; 2>/dev/null || true
    fi

    # 755 instead of 750 to avoid runtime import permission errors
    if [ -d "$APP_DIR/venv" ]; then
        chmod -R 755 "$APP_DIR/venv" 2>/dev/null || true
    fi

    if [ -f "$APP_DIR/.env" ]; then
        chmod 600 "$APP_DIR/.env"
        chown "$APP_USER:$APP_GROUP" "$APP_DIR/.env"
    fi

    if [ -f "$APP_DIR/requirements.txt" ]; then
        chmod 640 "$APP_DIR/requirements.txt"
    fi

    log_info "✓ File permissions set successfully"
    echo ""
}

# ============================================================================
# Step 6: Create and Enable systemd Service
# ============================================================================
create_systemd_service() {
    log_step "Step 6: Creating systemd service..."

    cat > /etc/systemd/system/csye6225.service << EOF
[Unit]
Description=CSYE6225 Web Application
After=network-online.target cloud-final.service
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=-/opt/csye6225/.env
Environment="PATH=/opt/csye6225/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/csye6225/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
LimitNOFILE=65535

# Security settings
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    # Enable at AMI build time so it auto-starts on every boot
    # User Data only needs to write .env and then start the service
    systemctl enable csye6225

    log_info "✓ Systemd service created, daemon reloaded, and service enabled"
    log_warn "Service will be STARTED by EC2 User Data after .env is written"
    echo ""
}

# ============================================================================
# Main Execution
# ============================================================================
main() {
    echo "============================================================================"
    log_info "CSYE 6225 - Application Setup Script (A5)"
    log_info "Target Directory: $APP_DIR"
    log_info "Note: Database config and S3 bucket name injected at runtime via EC2 User Data"
    echo "============================================================================"
    echo ""

    check_root

    install_system_deps
    create_app_group
    create_app_user
    deploy_application "$@"
    set_permissions
    create_systemd_service

    echo "============================================================================"
    log_info "✓ AMI setup completed successfully!"
    log_info "The following will be handled at EC2 launch via User Data:"
    log_info "  - Write DATABASE_URL and S3_BUCKET_NAME to /opt/csye6225/.env"
    log_info "  - systemctl start csye6225"
    echo "============================================================================"
}

main "$@"
