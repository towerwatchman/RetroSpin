#!/bin/bash

LOG_FILE="/tmp/retrospin.log"
DRIVE="/dev/sr0"

# Log function
log() {
    echo "$(date) - $1" >> "$LOG_FILE"
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
log "Starting RetroSpin service..."
while true; do
    if [ -b "$DRIVE" ]; then
        SERIAL=$(read_serial)
        if [ -n "$SERIAL" ]; then
            TITLE="Game_$SERIAL"
            SYSTEM="ss"
            /media/fat/Scripts/save_disc.sh "$DRIVE" "$TITLE" "$SYSTEM"
        fi
    fi
    sleep 1
done