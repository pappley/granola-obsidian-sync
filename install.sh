#!/bin/bash

#############################################################################
# Granola Obsidian Sync - Automated Installation Script
#
# This script sets up the Granola transcript sync tool with automated
# validation, dependency installation, and configuration generation.
#
# Usage: ./install.sh
#############################################################################

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

#############################################################################
# Logging functions
#############################################################################

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

#############################################################################
# Validation functions
#############################################################################

check_python_version() {
    log_info "Checking Python version..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        echo "Please install Python 3.9 or higher from https://www.python.org/"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 9 ]); then
        log_error "Python 3.9 or higher required (found $PYTHON_VERSION)"
        exit 1
    fi

    log_success "Python $PYTHON_VERSION found"
}

check_granola_app() {
    log_info "Checking for Granola app..."

    if [ ! -d "/Applications/Granola.app" ]; then
        log_error "Granola app not found in /Applications/"
        echo "Please download and install Granola from https://granola.ai/"
        exit 1
    fi

    log_success "Granola app found at /Applications/Granola.app"
}

check_granola_credentials() {
    log_info "Checking for Granola credentials..."

    CREDS_FILE="$HOME/Library/Application Support/Granola/supabase.json"

    if [ ! -f "$CREDS_FILE" ]; then
        log_error "Granola credentials not found"
        echo ""
        echo "To fix this:"
        echo "1. Open the Granola app (/Applications/Granola.app)"
        echo "2. Sign in with your account"
        echo "3. Close the app"
        echo "4. Run this installer again"
        echo ""
        echo "Credentials should be stored at: $CREDS_FILE"
        exit 1
    fi

    # Verify credentials contain OAuth tokens
    if ! python3 -c "import json; f=open('$CREDS_FILE'); d=json.load(f); assert 'workos_tokens' in d or 'cognito_tokens' in d" 2>/dev/null; then
        log_error "Granola credentials file is invalid or missing OAuth tokens"
        echo "Please try signing out and back in to Granola, then run this installer again"
        exit 1
    fi

    log_success "Found valid Granola credentials at $CREDS_FILE"
    log_info "  These credentials are used only by this tool on your local machine"
}

check_obsidian() {
    log_info "Checking for Obsidian..."

    if ! command -v obsidian &> /dev/null; then
        log_warn "Obsidian CLI not found in PATH (this is normal if using GUI)"
        log_info "  Make sure you have Obsidian installed and a vault created"
    else
        log_success "Obsidian found in PATH"
    fi
}

#############################################################################
# Installation functions
#############################################################################

install_dependencies() {
    log_info "Installing Python dependencies..."

    if python3 -m pip --version &> /dev/null; then
        python3 -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
    else
        python3 -m pip install -r "$SCRIPT_DIR/requirements.txt"
    fi

    log_success "Dependencies installed"
}

prompt_obsidian_vault() {
    log_info "Setting up Obsidian vault path..."
    echo ""
    echo "Where is your Obsidian vault? This should be the folder that contains your notes."
    echo ""

    # Default to common location
    DEFAULT_VAULT="$HOME/Obsidian/first-vault/Granola"

    while true; do
        read -p "Enter path to Obsidian vault [$DEFAULT_VAULT]: " VAULT_PATH
        VAULT_PATH="${VAULT_PATH:-$DEFAULT_VAULT}"

        # Expand ~ to home directory
        VAULT_PATH="${VAULT_PATH/#\~/$HOME}"

        # Check if parent directory exists
        PARENT_DIR="$(dirname "$VAULT_PATH")"
        if [ ! -d "$PARENT_DIR" ]; then
            log_error "Parent directory does not exist: $PARENT_DIR"
            echo "Please enter a valid path"
            continue
        fi

        log_success "Vault path set to: $VAULT_PATH"
        break
    done
}

generate_config() {
    log_info "Generating configuration..."

    CONFIG_FILE="$SCRIPT_DIR/config.yaml"
    TEMPLATE_FILE="$SCRIPT_DIR/config.yaml.template"

    # Create config from template, replacing placeholder
    sed "s|{{OBSIDIAN_VAULT_PATH}}|$VAULT_PATH|g" "$TEMPLATE_FILE" > "$CONFIG_FILE"

    log_success "Configuration saved to $CONFIG_FILE"
}

create_directories() {
    log_info "Creating required directories..."

    mkdir -p "$SCRIPT_DIR/data"
    mkdir -p "$SCRIPT_DIR/logs"
    mkdir -p "$SCRIPT_DIR/backups"
    mkdir -p "$VAULT_PATH"

    log_success "Directories created"
}

run_test_sync() {
    log_info "Running test sync..."
    echo ""

    if cd "$SCRIPT_DIR" && python3 main.py --config config.yaml 2>&1; then
        log_success "Test sync completed successfully!"
        return 0
    else
        log_warn "Test sync encountered issues (this may be normal on first run)"
        return 1
    fi
}

setup_cron() {
    log_info ""
    read -p "Would you like to set up automatic syncing via cron? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Running cron setup tool..."
        python3 "$SCRIPT_DIR/setup_automation.py"
    else
        log_info "Skipping cron setup (you can run setup_automation.py later)"
    fi
}

#############################################################################
# Main installation flow
#############################################################################

main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Granola Obsidian Sync - Installation  ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""

    # Validation phase
    log_info "Running pre-installation checks..."
    echo ""
    check_python_version
    check_granola_app
    check_granola_credentials
    check_obsidian

    echo ""

    # Installation phase
    log_info "Installing dependencies..."
    echo ""
    install_dependencies

    echo ""

    # Configuration phase
    log_info "Configuring installation..."
    echo ""
    prompt_obsidian_vault
    generate_config
    create_directories

    echo ""

    # Testing phase
    log_info "Verifying installation..."
    echo ""
    run_test_sync

    echo ""

    # Cron setup (optional)
    setup_cron

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Installation Complete!               ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Your Obsidian vault is configured: $VAULT_PATH"
    echo "2. Test sync results are in: $SCRIPT_DIR/logs/"
    echo "3. Run manually anytime: python3 main.py"
    echo "4. View transcripts in: $VAULT_PATH"
    echo ""
    log_info "If you set up cron, syncing will start automatically"
    log_info "For help, see: INSTALL.md"
    echo ""
}

# Run main installation
main
