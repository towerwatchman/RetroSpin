#!/bin/bash

SCRIPT_PATH="/media/fat/retrospin/retrospin_launcher.py"
LOG_FILE="/media/fat/Scripts/retrospin_launcher.log"

# Check if Python 3 is installed
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3 is not installed!" | tee -a "$LOG_FILE"
    exit 1
fi

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: $SCRIPT_PATH not found!" | tee -a "$LOG_FILE"
    exit 1
fi

# Ensure script is executable
chmod +x "$SCRIPT_PATH"

# Launch RetroSpin in the background
echo "Launching RetroSpin Disc Launcher in the background..." | tee -a "$LOG_FILE"
nohup python3 "$SCRIPT_PATH" >> "$LOG_FILE" 2>&1 &
PID=$!
echo "RetroSpin Disc Launcher started with PID $PID. Logs at $LOG_FILE" | tee -a "$LOG_FILE"