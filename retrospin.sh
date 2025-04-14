#!/bin/bash

SCRIPT_PATH="/media/fat/retrospin/retrospin_launcher.py"
WRAPPER_PATH="/media/fat/retrospin/retrospin_wrapper.sh"
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

# Ensure scripts are executable
chmod +x "$SCRIPT_PATH"
chmod +x "$WRAPPER_PATH" 2>/dev/null || echo "Warning: $WRAPPER_PATH not found, will be created by retrospin.sh"

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

# Export consoles for wrapper and save_disc.sh
export RETROSPIN_FRONTEND_CONSOLE="$FRONTEND_CONSOLE"
export RETROSPIN_DIALOG_CONSOLE="$DIALOG_CONSOLE"

# Create wrapper script
cat > "$WRAPPER_PATH" << EOF
#!/bin/bash
export TERM=linux
export RETROSPIN_FRONTEND_CONSOLE="$FRONTEND_CONSOLE"
export RETROSPIN_DIALOG_CONSOLE="$DIALOG_CONSOLE"
python3 "$SCRIPT_PATH" >> "$LOG_FILE" 2>&1
EOF
chmod +x "$WRAPPER_PATH"

# Launch RetroSpin in the background with setsid
echo "Launching RetroSpin Disc Launcher in the background..." | tee -a "$LOG_FILE"
setsid "$WRAPPER_PATH" &
PID=$!
echo "RetroSpin Disc Launcher started with PID $PID" | tee -a "$LOG_FILE"