#!/bin/bash
# Setup script for macOS launchd automation

echo "Setting up macOS launchd for Weekly Status Agent"
echo "================================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Paths
PLIST_FILE="$SCRIPT_DIR/com.user.weekly-status.plist"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
LAUNCHD_PLIST="$LAUNCHD_DIR/com.user.weekly-status.plist"

echo ""
echo "Project directory: $PROJECT_DIR"
echo "Plist file: $PLIST_FILE"
echo "LaunchAgents directory: $LAUNCHD_DIR"
echo ""

# Check if plist file exists
if [ ! -f "$PLIST_FILE" ]; then
    echo "ERROR: Plist file not found at $PLIST_FILE"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
if [ ! -d "$LAUNCHD_DIR" ]; then
    echo "Creating LaunchAgents directory..."
    mkdir -p "$LAUNCHD_DIR"
fi

# Check if agent is already loaded
if launchctl list | grep -q "com.user.weekly-status"; then
    echo "Agent is already loaded. Unloading..."
    launchctl unload "$LAUNCHD_PLIST"
fi

# Copy plist file to LaunchAgents
echo "Copying plist file to LaunchAgents..."
cp "$PLIST_FILE" "$LAUNCHD_PLIST"

# Load the agent
echo "Loading agent..."
launchctl load "$LAUNCHD_PLIST"

# Check if loaded successfully
if launchctl list | grep -q "com.user.weekly-status"; then
    echo ""
    echo "✓ Agent loaded successfully!"
    echo ""
    echo "The Weekly Status Agent will now run automatically according to the schedule"
    echo "defined in the plist file (default: every Friday at 5:00 PM)."
    echo ""
    echo "Useful commands:"
    echo "  - Check status: launchctl list | grep weekly-status"
    echo "  - Unload agent: launchctl unload $LAUNCHD_PLIST"
    echo "  - Reload agent: launchctl unload $LAUNCHD_PLIST && launchctl load $LAUNCHD_PLIST"
    echo "  - View logs: tail -f $PROJECT_DIR/logs/launchd-out.log"
    echo ""
else
    echo ""
    echo "✗ Failed to load agent. Check the plist file for errors."
    exit 1
fi
