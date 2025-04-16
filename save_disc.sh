#!/bin/bash

DRIVE="$1"
TITLE="$2"
SYSTEM="$3"
LOG_FILE="/tmp/retrospin.log"
RIPDISC_PATH="/media/fat/_Utility"

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

# Save disc
save_disc() {
    case "$SYSTEM" in
        psx) OUTPUT_DIR="/media/usb0/games/PSX" ;;
        ss) OUTPUT_DIR="/media/usb0/games/Saturn" ;;
        mcd) OUTPUT_DIR="/media/usb0/games/MegaCD" ;;
        *) OUTPUT_DIR="/media/usb0/games" ;;
    esac
    mkdir -p "$OUTPUT_DIR"
    CUE_FILE="$OUTPUT_DIR/$TITLE.cue"
    BIN_FILE="$OUTPUT_DIR/$TITLE.bin"

    if [ -f "$CUE_FILE" ]; then
        log "Removing existing .cue file: $CUE_FILE"
        rm -f "$CUE_FILE"
    fi
    if [ -f "$BIN_FILE" ]; then
        log "Removing existing .bin file: $BIN_FILE"
        rm -f "$BIN_FILE"
    fi

    dialog --yesno "RetroSpin\nSave disc as $TITLE.bin/.cue to $OUTPUT_DIR?" 12 50 </dev/tty2 >/dev/tty2 2>/tmp/save_dialog.err
    RESPONSE=$?
    if [ -s "/tmp/save_dialog.err" ]; then
        log "Dialog error: $(cat /tmp/save_dialog.err)"
        rm -f "/tmp/save_dialog.err"
    fi
    if [ $RESPONSE -ne 0 ]; then
        log "User declined to save disc"
        return 1
    fi

    log "Saving disc to $CUE_FILE..."
    TOC_FILE="/tmp/retrospin_temp.toc"
    if ! "$RIPDISC_PATH/cdrdao" read-cd --read-raw --speed max --datafile "$BIN_FILE" --device "$DRIVE" --driver generic-mmc-raw "$TOC_FILE" 2>>"$LOG_FILE"; then
        log "Failed to read disc"
        dialog --msgbox "RetroSpin\nFailed to read disc" 10 40 </dev/tty2 >/dev/tty2 2>/tmp/save_dialog.err
        rm -f "$TOC_FILE" "$BIN_FILE"
        return 1
    fi
    if ! "$RIPDISC_PATH/toc2cue" "$TOC_FILE" "$CUE_FILE" 2>>"$LOG_FILE"; then
        log "Failed to convert TOC to CUE"
        dialog --msgbox "RetroSpin\nFailed to create .cue file" 10 40 </dev/tty2 >/dev/tty2 2>/tmp/save_dialog.err
        rm -f "$TOC_FILE" "$BIN_FILE"
        return 1
    fi
    rm -f "$TOC_FILE"
    sed -i "s|$BIN_FILE|$TITLE.bin|g" "$CUE_FILE"
    log "Successfully saved $CUE_FILE and $BIN_FILE"
    dialog --msgbox "RetroSpin\nDisc saved successfully to $CUE_FILE" 10 50 </dev/tty2 >/dev/tty2 2>/tmp/save_dialog.err
    return 0
}

# Main
setup_console
if kill_mister; then
    save_disc
    relaunch_mister
else
    dialog --msgbox "Failed to stop MiSTer process" 10 40 </dev/tty2 >/dev/tty2 2>/tmp/save_dialog.err
    if [ -s "/tmp/save_dialog.err" ]; then
        log "Dialog error: $(cat /tmp/save_dialog.err)"
        rm -f "/tmp/save_dialog.err"
    fi
fi