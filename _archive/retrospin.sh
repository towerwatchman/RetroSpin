#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_PATH="$SCRIPT_DIR/main.py"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/retrospin_launcher.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

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

# Set terminal environment
export TERM=linux

# Detect active console (frontend)
FRONTEND_CONSOLE=""
if [ -x "/bin/fgconsole" ]; then
    TTY_NUM=$(fgconsole 2>/dev/null)
    if [ -n "$TTY_NUM" ]; then
        FRONTEND_CONSOLE="/dev/tty$TTY_NUM"
    fi
fi
if [ -z "$FRONTEND_CONSOLE" ] || [ ! -w "$FRONTEND_CONSOLE" ]; then
    for dev in /dev/tty2 /dev/tty1 /dev/console; do
        if [ -w "$dev" ]; then
            FRONTEND_CONSOLE="$dev"
            break
        fi
    done
fi
if [ -z "$FRONTEND_CONSOLE" ]; then
    FRONTEND_CONSOLE="/dev/tty2"  # Default to tty2 based on log
fi

# Dialog console (separate from frontend)
DIALOG_CONSOLE="/dev/tty3"

# Log console setup and permissions
echo "Console setup: TERM=$TERM, FRONTEND_CONSOLE=$FRONTEND_CONSOLE, DIALOG_CONSOLE=$DIALOG_CONSOLE, TTY=$(tty 2>/dev/null || echo none)" | tee -a "$LOG_FILE"
ls -l "$FRONTEND_CONSOLE" "$DIALOG_CONSOLE" /dev/fb0 2>/dev/null | tee -a "$LOG_FILE"

# Export consoles for main.py and save_disc.sh
export RETROSPIN_FRONTEND_CONSOLE="$FRONTEND_CONSOLE"
export RETROSPIN_DIALOG_CONSOLE="$DIALOG_CONSOLE"

# Launch RetroSpin interactively in the foreground (no redirection to allow interactive dialog)
echo "Launching RetroSpin Disc Launcher..." | tee -a "$LOG_FILE"
python3 "$SCRIPT_PATH"
echo "RetroSpin Disc Launcher completed." | tee -a "$LOG_FILE"