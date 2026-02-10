#!/bin/bash

# ============================================================================
# Application Setup Script for Ubuntu 24.04 LTS
# ============================================================================
# This script automates the setup of a FastAPI web application with
# PostgreSQL database on a fresh Ubuntu 24.04 server.
#
# Usage: 
#   sudo DB_PASSWORD='YourSecurePassword' bash scripts/setup.sh [path-to-app.zip]
#
# Assignment 3 - CSYE 6225
# ============================================================================

set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error

# ============================================================================
# Configuration Variables
# ============================================================================
APP_USER="csye6225"
APP_GROUP="csye6225"
APP_DIR="/opt/csye6225"
DB_NAME="csye6225_db"
DB_USER="csye6225_user"

# Security: Password must be provided via environment variable
DB_PASSWORD="${DB_PASSWORD:-}"

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

check_password() {
    if [[ -z "$DB_PASSWORD" ]]; then
        log_error "Database password not provided!"
        log_error "Usage: sudo DB_PASSWORD='YourSecurePassword' bash scripts/setup.sh"
        log_error "Password requirements:"
        log_error "  - At least 12 characters"
        log_error "  - Use only: letters, numbers, @, _, -"
        log_error "  - Avoid special characters like: ! # $ % & * ( )"
        exit 1
    fi
    
    # Validate password doesn't contain problematic characters
    if [[ "$DB_PASSWORD" =~ [!\$\`\\] ]]; then
        log_warn "Password contains special characters that may cause issues in URLs"
        log_warn "Recommended: Use only letters, numbers, @, _, -"
    fi
}

# ============================================================================
# Step 1: Update Package Lists
# ============================================================================
update_packages() {
    log_step "Step 1: Updating package lists..."
    log_info "Running: apt-get update"
    
    apt-get update
    
    log_info "✓ Package lists updated successfully"
    echo ""
}

# ============================================================================
# Step 2: Upgrade System Packages
# ============================================================================
upgrade_packages() {
    log_step "Step 2: Upgrading system packages..."
    log_info "Running: apt-get upgrade -y"
    log_warn "This may take several minutes..."
    
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
    
    log_info "✓ System packages upgraded successfully"
    echo ""
}

# ============================================================================
# Step 3: Install PostgreSQL Database Management System
# ============================================================================
install_postgresql() {
    log_step "Step 3: Installing PostgreSQL..."
    
    # Check if PostgreSQL package is installed
    if dpkg -l | grep -q "^ii  postgresql "; then
        log_warn "PostgreSQL package is already installed"
    else
        log_info "Installing PostgreSQL database server..."
        apt-get install -y postgresql postgresql-contrib
    fi
    
    # Ensure PostgreSQL service is started
    log_info "Starting PostgreSQL service..."
    systemctl start postgresql || true
    
    # Enable PostgreSQL to start on boot
    log_info "Enabling PostgreSQL to start on boot..."
    systemctl enable postgresql
    
    # Verify service is running
    sleep 2
    if systemctl is-active --quiet postgresql; then
        log_info "✓ PostgreSQL installed, running, and enabled on boot"
    else
        log_error "PostgreSQL service failed to start"
        systemctl status postgresql
        exit 1
    fi
    
    echo ""
}

# ============================================================================
# Step 4: Create Application Database
# ============================================================================
create_database() {
    log_step "Step 4: Creating application database..."
    
    # Wait for PostgreSQL to be fully ready
    sleep 2
    
    # Check if database already exists
    log_info "Checking if database '$DB_NAME' exists..."
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        log_warn "Database '$DB_NAME' already exists"
    else
        log_info "Creating database '$DB_NAME'..."
        sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
        log_info "✓ Database created"
    fi
    
    # Check if database user already exists
    log_info "Checking if database user '$DB_USER' exists..."
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
        log_warn "Database user '$DB_USER' already exists"
        log_info "Updating user password..."
        sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    else
        log_info "Creating database user '$DB_USER'..."
        sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
        log_info "✓ Database user created"
    fi
    
    # Grant privileges
    log_info "Granting privileges to user '$DB_USER'..."
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    sudo -u postgres psql -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;"
    
    # Grant schema privileges (required for PostgreSQL 15+)
    log_info "Granting schema privileges..."
    sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;" 2>/dev/null || true
    sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;" 2>/dev/null || true
    sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;" 2>/dev/null || true
    
    # Set default privileges for future objects
    log_info "Setting default privileges for future objects..."
    sudo -u postgres psql -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;" 2>/dev/null || true
    sudo -u postgres psql -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;" 2>/dev/null || true
    
    log_info "✓ Database setup completed successfully"
    echo ""
}

# ============================================================================
# Step 5: Create Application Linux Group
# ============================================================================
create_app_group() {
    log_step "Step 5: Creating application group..."
    
    # Check if group already exists
    if getent group "$APP_GROUP" > /dev/null 2>&1; then
        log_warn "Group '$APP_GROUP' already exists"
    else
        log_info "Creating group '$APP_GROUP'..."
        groupadd "$APP_GROUP"
        log_info "✓ Group '$APP_GROUP' created successfully"
    fi
    
    echo ""
}

# ============================================================================
# Step 6: Create Application User Account
# ============================================================================
create_app_user() {
    log_step "Step 6: Creating application user..."
    
    # Check if user already exists
    if id "$APP_USER" &>/dev/null; then
        log_warn "User '$APP_USER' already exists"
    else
        log_info "Creating system user '$APP_USER' (non-login)..."
        # -r: system user
        # -s /bin/false: no login shell (non-login user)
        # -g: primary group
        # -d: home directory
        # -M: do not create home directory
        useradd -r -s /bin/false -g "$APP_GROUP" -d "$APP_DIR" -M "$APP_USER"
        log_info "✓ Non-login user '$APP_USER' created successfully"
    fi
    
    echo ""
}

# ============================================================================
# Step 7: Deploy Application Files
# ============================================================================
deploy_application() {
    log_step "Step 7: Deploying application files..."
    
    # Create application directory if it doesn't exist
    if [ ! -d "$APP_DIR" ]; then
        log_info "Creating application directory: $APP_DIR"
        mkdir -p "$APP_DIR"
    else
        log_warn "Directory $APP_DIR already exists"
    fi
    
    # Check if application files are provided as argument
    if [ $# -gt 0 ] && [ -f "$1" ]; then
        APP_ARCHIVE="$1"
        log_info "Extracting application files from: $APP_ARCHIVE"
        
        # Determine file type and extract accordingly
        if [[ "$APP_ARCHIVE" == *.zip ]]; then
            log_info "Detected ZIP archive, installing unzip if needed..."
            apt-get install -y unzip
            log_info "Unzipping to $APP_DIR..."
            unzip -o "$APP_ARCHIVE" -d "$APP_DIR"
        elif [[ "$APP_ARCHIVE" == *.tar.gz ]] || [[ "$APP_ARCHIVE" == *.tgz ]]; then
            log_info "Detected tar.gz archive, extracting..."
            tar -xzf "$APP_ARCHIVE" -C "$APP_DIR"
        elif [[ "$APP_ARCHIVE" == *.tar ]]; then
            log_info "Detected tar archive, extracting..."
            tar -xf "$APP_ARCHIVE" -C "$APP_DIR"
        else
            log_error "Unsupported archive format: $APP_ARCHIVE"
            log_error "Supported formats: .zip, .tar.gz, .tgz, .tar"
            exit 1
        fi
        
        log_info "✓ Application files extracted successfully"
        
        # Check for nested directory structure and flatten if needed
        SUBDIRS=($(find "$APP_DIR" -mindepth 1 -maxdepth 1 -type d))
        if [ ${#SUBDIRS[@]} -eq 1 ] && [ ! -f "$APP_DIR/requirements.txt" ]; then
            NESTED_DIR="${SUBDIRS[0]}"
            log_warn "Detected nested directory structure: $NESTED_DIR"
            log_info "Flattening directory structure..."
            # Move all contents up one level (including hidden files)
            shopt -s dotglob  # Include hidden files in *
            mv "$NESTED_DIR"/* "$APP_DIR/" 2>/dev/null || true
            shopt -u dotglob  # Restore default behavior
            rmdir "$NESTED_DIR" 2>/dev/null || true
            log_info "✓ Directory structure flattened"
        fi
    else
        # If no archive provided, check if files already exist
        if [ "$(ls -A $APP_DIR 2>/dev/null)" ]; then
            log_warn "Application files already present in $APP_DIR"
        else
            log_warn "No application archive provided and directory is empty"
            log_warn "Please ensure application files are in $APP_DIR before starting the service"
            log_warn "Usage: sudo DB_PASSWORD='...' bash scripts/setup.sh /path/to/application.zip"
        fi
    fi
    
    # Verify critical files exist
    if [ ! -d "$APP_DIR/app" ]; then
        log_error "Application directory 'app/' not found in $APP_DIR"
        log_error "Please check your archive structure"
        ls -la "$APP_DIR"
        exit 1
    fi
    
    if [ ! -f "$APP_DIR/requirements.txt" ]; then
        log_error "requirements.txt not found in $APP_DIR"
        exit 1
    fi
    
    # Install Python and required dependencies
    log_info "Installing Python and dependencies..."
    apt-get install -y python3 python3-pip python3-venv libpq-dev
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$APP_DIR/venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv "$APP_DIR/venv"
        log_info "✓ Virtual environment created"
    else
        log_warn "Virtual environment already exists"
    fi
    
    # Install Python packages
    log_info "Installing Python packages from requirements.txt..."
    "$APP_DIR/venv/bin/pip" install --upgrade pip
    "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
    log_info "✓ Python packages installed"
    
    # URL-encode the password for DATABASE_URL
    # Simple encoding: just replace common problematic characters
    ENCODED_PASSWORD=$(echo -n "$DB_PASSWORD" | python3 -c "import sys; from urllib.parse import quote; print(quote(sys.stdin.read(), safe=''))")
    
    # Create .env file
    if [ ! -f "$APP_DIR/.env" ]; then
        log_info "Creating environment configuration file..."
        cat > "$APP_DIR/.env" << EOF
# Database Configuration
DATABASE_URL=postgresql://$DB_USER:$ENCODED_PASSWORD@localhost:5432/$DB_NAME

# Application Configuration
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
EOF
        log_info "✓ Environment file created"
    else
        log_warn ".env file already exists, skipping creation"
    fi
    
    log_info "✓ Application deployment completed"
    echo ""
}

# ============================================================================
# Step 8: Set File Permissions
# ============================================================================
set_permissions() {
    log_step "Step 8: Setting file permissions..."
    
    # 1. Set ownership for entire directory
    log_info "Changing ownership to $APP_USER:$APP_GROUP..."
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
    
    # 2. Set permissions for app source code (if exists)
    if [ -d "$APP_DIR/app" ]; then
        log_info "Setting app/ directory permissions to 750..."
        find "$APP_DIR/app" -type d -exec chmod 750 {} \; 2>/dev/null || true
        
        log_info "Setting app/ file permissions to 640..."
        find "$APP_DIR/app" -type f -exec chmod 640 {} \; 2>/dev/null || true
    fi
    
    # 3. CRITICAL: Keep venv executable (do NOT remove x permissions)
    if [ -d "$APP_DIR/venv" ]; then
        log_info "Setting venv/ permissions (keeping executables)..."
        # Keep venv directory structure intact
        chmod -R 750 "$APP_DIR/venv" 2>/dev/null || true
        # Ensure all files in venv/bin are executable
        find "$APP_DIR/venv/bin" -type f -exec chmod 750 {} \; 2>/dev/null || true
    fi
    
    # 4. Secure .env file (most restrictive)
    if [ -f "$APP_DIR/.env" ]; then
        log_info "Securing .env file (600 permissions)..."
        chmod 600 "$APP_DIR/.env"
    fi
    
    # 5. Set reasonable permissions for other files
    if [ -f "$APP_DIR/requirements.txt" ]; then
        chmod 640 "$APP_DIR/requirements.txt"
    fi
    
    if [ -f "$APP_DIR/README.md" ]; then
        chmod 640 "$APP_DIR/README.md"
    fi
    
    log_info "✓ File permissions set successfully"
    echo ""
}

# ============================================================================
# Create systemd Service
# ============================================================================
create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/csye6225.service << EOF
[Unit]
Description=CSYE6225 Web Application
After=network-online.target postgresql.service
Wants=network-online.target
Requires=postgresql.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=/opt/csye6225/.env
ExecStartPre=/usr/bin/test -x /opt/csye6225/venv/bin/uvicorn
ExecStart=/opt/csye6225/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    
    log_info "✓ Systemd service created"
    log_warn "Service is NOT started automatically"
    echo ""
}

# ============================================================================
# Main Execution
# ============================================================================
main() {
    echo "============================================================================"
    log_info "CSYE 6225 - Application Setup Script"
    log_info "Target Directory: $APP_DIR"
    log_info "Database: PostgreSQL ($DB_NAME)"
    echo "============================================================================"
    echo ""
    
    # Check prerequisites
    check_root
    check_password
    
    # Execute all setup steps
    update_packages
    upgrade_packages
    install_postgresql
    create_database
    create_app_group
    create_app_user
    deploy_application "$@"
    set_permissions
    create_systemd_service
    
    echo "============================================================================"
    log_info "✓ Setup completed successfully!"
    echo "============================================================================"
    echo ""
    log_info "Verification Commands:"
    echo ""
    echo "  1. Check PostgreSQL status:"
    echo "     sudo systemctl status postgresql"
    echo "     sudo systemctl is-enabled postgresql"
    echo ""
    echo "  2. Verify database exists:"
    echo "     sudo -u postgres psql -l | grep $DB_NAME"
    echo ""
    echo "  3. Verify user and group:"
    echo "     id $APP_USER"
    echo "     getent group $APP_GROUP"
    echo ""
    echo "  4. Check application files and permissions:"
    echo "     ls -la $APP_DIR"
    echo ""
    echo "  5. Verify venv executables:"
    echo "     ls -la $APP_DIR/venv/bin/uvicorn"
    echo ""
    echo "  6. Start the application:"
    echo "     sudo systemctl start csye6225"
    echo "     sudo systemctl enable csye6225"
    echo "     sudo systemctl status csye6225"
    echo ""
    log_info "Application will be accessible at: http://your-server-ip:8000"
    echo "============================================================================"
}

# Run main function with all arguments
main "$@"
