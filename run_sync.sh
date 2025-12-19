#!/bin/bash

# Granola Sync Automation Script
# Runs the Granola sync and logs results
# This script uses relative paths and should be placed in the granola tool directory

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Set up log file with timestamp
LOG_FILE="$SCRIPT_DIR/logs/granola_sync_$(date '+%Y-%m-%d_%H-%M-%S').log"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting Granola sync..."

# Run the sync script and capture output
if python3 "$SCRIPT_DIR/main.py" --config "$SCRIPT_DIR/config.yaml" >> "$LOG_FILE" 2>&1; then
    log "Granola sync completed successfully"

    # Keep only the last 30 log files to prevent disk space issues
    (
        cd "$SCRIPT_DIR/logs"
        ls -t granola_sync_*.log 2>/dev/null | tail -n +31 | xargs rm -f 2>/dev/null
    )

    exit 0
else
    log "Granola sync failed with exit code $?"
    exit 1
fi