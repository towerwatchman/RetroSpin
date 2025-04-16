#!/bin/bash

DRIVE="$1"
LOG_FILE="/tmp/retrospin.log"

# Log function
log() {
    echo "$(date) - $1" >> "$LOG_FILE"
}

# Setup console
setup_console() {
    console="/dev/tty2"
    log "Setting up console: $console"
    if [ -w "$console" ]; then
        stty sane < "$console" > "$console" 2>/dev/null
        tput init > "$console" 2>/dev/null
        echo -e "\033[?25h" > "$console" 2>/dev/null
        if [ -x "/sbin/chvt" ]; then
            chvt 2 2>/dev/null || log "Failed to switch to $console"
        fi
    else
        log "No writable console: $console"
        exit 1
    fi
}

# Kill MiSTer
kill_mister() {
    log "Checking for MiSTer process..."
    ps aux | grep "MiSTer" | grep -v grep > /tmp/mister_ps.log 2>&1
    MISTER_PID=$(cat /tmp/mister_ps.log | awk '{print $2}' | head -n 1)
    if [ -n "$MISTER_PID" ]; then
        log "Killing MiSTer process with PID $MISTER_PID..."
        kill -9 "$MISTER_PID" 2>/dev/null
        TIMEOUT=5
        ELAPSED=0
        while [ $ELAPSED -lt $TIMEOUT ] && ps aux | grep "MiSTer" | grep -v grep >/dev/null; do
            sleep 1
            ELAPSED=$((ELAPSED + 1))
        done
        if ! ps aux | grep "MiSTer" | grep -v grep >/dev/null; then
            log "MiSTer process terminated"
            rm -f /tmp/mister_ps.log
            return 0
        else
            log "Failed to terminate MiSTer process after $TIMEOUT seconds"
            rm -f /tmp/mister_ps.log
            return 1
        fi
    else
        log "No MiSTer process found"
        rm -f /tmp/mister_ps.log
        return 0
    fi
}

# Relaunch MiSTer
relaunch_mister() {
    if [ -x "/media/fat/MiSTer" ]; then
        log "Relaunching MiSTer process..."
        /media/fat/MiSTer >/dev/null 2>&1 &
        sleep 2
        if ps aux | grep "MiSTer" | grep -v grep >/dev/null; then
            log "MiSTer relaunched successfully"
        else
            log "Failed to relaunch MiSTer"
        fi
    fi
}

# Read disc serial
read_serial() {
    SERIAL=$(dd if="$DRIVE" bs=512 count=1 skip=32 2>/dev/null | strings | grep -E '[A-Z0-9_-]{4,}' | head -n 1)
    if [ -n "$SERIAL" ]; then
        log "Disc serial: $SERIAL"
        echo "$SERIAL"
    else
        log "No serial found on disc"
        echo ""
    fi
}

# Main
setup_console
if kill_mister; then
    SERIAL=$(read_serial)
    if [ -n "$SERIAL" ]; then
        dialog --msgbox "Disc serial: $SERIAL" 10 40 </dev/tty2 >/dev/tty2 2>/tmp/test_dialog.err
    else
        dialog --msgbox "No disc detected or serial read failed" 10 40 </dev/tty2 >/dev/tty2 2>/tmp/test_dialog.err
    fi
    if [ -s "/tmp/test_dialog.err" ]; then
        log "Dialog error: $(cat /tmp/test_dialog.err)"
        rm -f "/tmp/test_dialog.err"
    fi
    relaunch_mister
else
    dialog --msgbox "Failed to stop MiSTer process" 10 40 </dev/tty2 >/dev/tty2 2>/tmp/test_dialog.err
    if [ -s "/tmp/test_dialog.err" ]; then
        log "Dialog error: $(cat /tmp/test_dialog.err)"
        rm -f "/tmp/test_dialog.err"
    fi
fi