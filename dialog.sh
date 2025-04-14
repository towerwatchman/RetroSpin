#!/bin/bash

# Log file for debugging
LOG_FILE="/tmp/test_dialog.log"

# Select console
SELECTED_CONSOLE="/dev/tty2"
if [ ! -w "$SELECTED_CONSOLE" ]; then
    echo "No writable console ($SELECTED_CONSOLE) found" | tee -a "$LOG_FILE"
    exit 1
fi

# Log initial state
echo "Starting test dialog script at $(date)" | tee -a "$LOG_FILE"
echo "Console selected: $SELECTED_CONSOLE, TERM=$TERM, TTY=$(tty 2>/dev/null || echo none)" | tee -a "$LOG_FILE"
ls -l "$SELECTED_CONSOLE" /dev/fb0 2>/dev/null | tee -a "$LOG_FILE"
stty < "$SELECTED_CONSOLE" 2>/dev/null || echo "Failed to read stty settings for $SELECTED_CONSOLE" | tee -a "$LOG_FILE"

# Set terminal environment
export TERM=linux

# Activate console
if [ -x "/sbin/chvt" ]; then
    chvt 2 2>/dev/null || echo "Failed to switch to $SELECTED_CONSOLE" | tee -a "$LOG_FILE"
fi

# Kill MiSTer process
echo "Checking for MiSTer process..." | tee -a "$LOG_FILE"
ps aux | grep "MiSTer" | grep -v grep >>"$LOG_FILE" 2>&1
MISTER_PID=$(ps aux | grep "MiSTer" | grep -v grep | awk '{print $2}' | head -n 1)
if [ -n "$MISTER_PID" ]; then
    echo "Killing MiSTer process with PID $MISTER_PID..." | tee -a "$LOG_FILE"
    kill -9 "$MISTER_PID" 2>/dev/null
    TIMEOUT=5
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ] && ps aux | grep "MiSTer" | grep -v grep >/dev/null; do
        sleep 1
        ELAPSED=$((ELAPSED + 1))
    done
    if ! ps aux | grep "MiSTer" | grep -v grep >/dev/null; then
        echo "MiSTer process terminated" | tee -a "$LOG_FILE"
    else
        echo "Failed to terminate MiSTer process after $TIMEOUT seconds" | tee -a "$LOG_FILE"
        exit 1
    fi
else
    echo "No MiSTer process found, proceeding with dialog" | tee -a "$LOG_FILE"
fi

# Initialize console
if [ -w "$SELECTED_CONSOLE" ]; then
    stty sane < "$SELECTED_CONSOLE" > "$SELECTED_CONSOLE" 2>/dev/null
    tput init > "$SELECTED_CONSOLE" 2>/dev/null
    echo -e "\033[?25h" > "$SELECTED_CONSOLE" 2>/dev/null
else
    echo "Cannot initialize console $SELECTED_CONSOLE" | tee -a "$LOG_FILE"
    exit 1
fi

# Test dialog
echo "Executing test dialog on $SELECTED_CONSOLE" | tee -a "$LOG_FILE"
dialog --timeout 30 --yesno "Test Dialog\nCan you see this dialog?" 10 40 </dev/tty2 >/dev/tty2 2>/tmp/test_dialog.err
RESPONSE=$?
if [ -s "/tmp/test_dialog.err" ]; then
    echo "Dialog error: $(cat /tmp/test_dialog.err)" | tee -a "$LOG_FILE"
    rm -f "/tmp/test_dialog.err"
fi
echo "Dialog exit status: $RESPONSE" | tee -a "$LOG_FILE"

# Relaunch MiSTer
if [ -x "/media/fat/MiSTer" ]; then
    echo "Relaunching MiSTer process..." | tee -a "$LOG_FILE"
    /media/fat/MiSTer >/dev/null 2>&1 &
    sleep 2
    if ps aux | grep "MiSTer" | grep -v grep >/dev/null; then
        echo "MiSTer relaunched successfully" | tee -a "$LOG_FILE"
    else
        echo "Failed to relaunch MiSTer" | tee -a "$LOG_FILE"
    fi
else
    echo "MiSTer executable not found" | tee -a "$LOG_FILE"
fi

exit 0