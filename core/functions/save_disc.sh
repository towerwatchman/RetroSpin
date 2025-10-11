#!/bin/bash

DRIVE="$1"
TITLE="$2"
SYSTEM="$3"
LOG_FILE="/tmp/retrospin.log"
RIPDISC_PATH="/media/fat/_Utility"
OUTPUT_BASE_DIR="/media/usb0/games"

# Log function
log() {
    echo "$(date) - $1" >> "$LOG_FILE" 2>/dev/null || echo "$(date) - $1" >&2
}

# Ensure log file is writable
ensure_log_writable() {
    mkdir -p /tmp 2>/dev/null
    chmod 777 /tmp 2>/dev/null
    touch "$LOG_FILE" 2>/dev/null
    chown mister:mister "$LOG_FILE" 2>/dev/null
    chmod 664 "$LOG_FILE" 2>/dev/null
}

# Setup console
setup_console() {
    console="/dev/tty"
    log "Setting up console: $console"
    if [ -w "$console" ]; then
        stty sane < "$console" > "$console" 2>/dev/null
        tput init > "$console" 2>/dev/null
        echo -e "\033[?25h" > "$console" 2>/dev/null
    else
        log "No writable console: $console, falling back to stderr"
        console="/dev/stderr"
    fi
}

# Save disc
save_disc() {
    # Check RIPDISC_PATH
    if [ ! -d "$RIPDISC_PATH" ] || [ ! -x "$RIPDISC_PATH/cdrdao" ] || [ ! -x "$RIPDISC_PATH/toc2cue" ]; then
        log "RIPDISC_PATH ($RIPDISC_PATH) or binaries (cdrdao, toc2cue) not found or not executable"
        # Check if cdrdao and toc2cue are in system PATH
        if command -v cdrdao >/dev/null 2>&1 && command -v toc2cue >/dev/null 2>&1; then
            log "Found cdrdao and toc2cue in system PATH, using system binaries"
            RIPDISC_PATH=""  # Use system binaries
        else
            log "Error: cdrdao and toc2cue not found in $RIPDISC_PATH or system PATH"
            dialog --msgbox "RetroSpin\nError: Utility binaries (cdrdao, toc2cue) not found in $RIPDISC_PATH or system PATH" 10 60 2>>"$LOG_FILE" || log "Failed to display error: Utility binaries not found"
            return 1
        fi
    fi

    # Check OUTPUT_BASE_DIR and fallback to /usr/games if not found
    if [ ! -d "$OUTPUT_BASE_DIR" ]; then
        log "OUTPUT_BASE_DIR ($OUTPUT_BASE_DIR) not found, falling back to /usr/games"
        OUTPUT_BASE_DIR="/usr/games"
    fi

    # Set output directory based on system
    case "$SYSTEM" in
        psx) OUTPUT_DIR="$OUTPUT_BASE_DIR/PSX" ;;
        ss) OUTPUT_DIR="$OUTPUT_BASE_DIR/Saturn" ;;
        mcd) OUTPUT_DIR="$OUTPUT_BASE_DIR/MegaCD" ;;
        *) OUTPUT_DIR="$OUTPUT_BASE_DIR" ;;
    esac

    # Ensure output directory exists and is writable
    if ! mkdir -p "$OUTPUT_DIR" 2>/dev/null; then
        log "Error: Cannot create output directory $OUTPUT_DIR"
        dialog --msgbox "RetroSpin\nError: Cannot create output directory $OUTPUT_DIR" 10 50 2>>"$LOG_FILE" || log "Failed to display error: Cannot create output directory"
        return 1
    fi
    chown mister:mister "$OUTPUT_DIR" 2>/dev/null
    chmod 775 "$OUTPUT_DIR" 2>/dev/null

    CUE_FILE="$OUTPUT_DIR/$TITLE.cue"
    BIN_FILE="$OUTPUT_DIR/$TITLE.bin"

    # Remove existing files
    if [ -f "$CUE_FILE" ]; then
        log "Removing existing .cue file: $CUE_FILE"
        rm -f "$CUE_FILE" 2>>"$LOG_FILE"
    fi
    if [ -f "$BIN_FILE" ]; then
        log "Removing existing .bin file: $BIN_FILE"
        rm -f "$BIN_FILE" 2>>"$LOG_FILE"
    fi

    # Prompt user to save disc
    dialog --yesno "RetroSpin\nSave disc as $TITLE.bin/.cue to $OUTPUT_DIR?" 12 50 2>/tmp/save_dialog.err
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
    CDRDAO="$RIPDISC_PATH/cdrdao"
    TOC2CUE="$RIPDISC_PATH/toc2cue"
    [ -z "$RIPDISC_PATH" ] && CDRDAO="cdrdao" && TOC2CUE="toc2cue"
    if ! "$CDRDAO" read-cd --read-raw --speed max --datafile "$BIN_FILE" --device "$DRIVE" --driver generic-mmc-raw "$TOC_FILE" 2>>"$LOG_FILE"; then
        log "Failed to read disc"
        dialog --msgbox "RetroSpin\nFailed to read disc" 10 40 2>>"$LOG_FILE" || log "Failed to display error: Failed to read disc"
        rm -f "$TOC_FILE" "$BIN_FILE" 2>>"$LOG_FILE"
        return 1
    fi
    if ! "$TOC2CUE" "$TOC_FILE" "$CUE_FILE" 2>>"$LOG_FILE"; then
        log "Failed to convert TOC to CUE"
        dialog --msgbox "RetroSpin\nFailed to create .cue file" 10 40 2>>"$LOG_FILE" || log "Failed to display error: Failed to create .cue file"
        rm -f "$TOC_FILE" "$BIN_FILE" 2>>"$LOG_FILE"
        return 1
    fi
    rm -f "$TOC_FILE" 2>>"$LOG_FILE"
    sed -i "s|$BIN_FILE|$TITLE.bin|g" "$CUE_FILE" 2>>"$LOG_FILE"
    log "Successfully saved $CUE_FILE and $BIN_FILE"
    dialog --msgbox "RetroSpin\nDisc saved successfully to $CUE_FILE" 10 50 2>>"$LOG_FILE" || log "Failed to display success message"
    return 0
}

# Main
ensure_log_writable
setup_console
save_disc