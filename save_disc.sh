#!/bin/bash

# Arguments from Python: drive_path, title, system
DRIVE_PATH="$1"
TITLE="$2"
SYSTEM="$3"

# USB paths
USB_PSX_PATH="/media/usb0/games/PSX"
USB_SATURN_PATH="/media/usb0/games/Saturn"
USB_MCD_PATH="/media/usb0/games/MegaCD"
BASE_DIR="$USB_SATURN_PATH"
SYSTEM_NAME="Sega Saturn"
if [ "$SYSTEM" == "psx" ]; then
    BASE_DIR="$USB_PSX_PATH"
    SYSTEM_NAME="Sony PlayStation"
elif [ "$SYSTEM" == "mcd" ]; then
    BASE_DIR="$USB_MCD_PATH"
    SYSTEM_NAME="Sega CD"
fi
RIPDISC_PATH="/media/fat/_Utility"

# Ensure directory exists
mkdir -p "$BASE_DIR"

# Define file paths
CUE_FILE="$BASE_DIR/$TITLE.cue"
BIN_FILE="$BASE_DIR/$TITLE.bin"

# Delete any existing .cue or .bin files at the start
if [ -f "$CUE_FILE" ]; then
    echo "Removing existing .cue file: $CUE_FILE"
    rm -f "$CUE_FILE"
fi
if [ -f "$BIN_FILE" ]; then
    echo "Removing existing .bin file: $BIN_FILE"
    rm -f "$BIN_FILE"
fi

# Cleanup function for cdrdao and partial files
cleanup() {
    if [ -n "$CDRDAO_PID" ] && kill -0 "$CDRDAO_PID" 2>/dev/null; then
        echo "Terminating cdrdao process $CDRDAO_PID..."
        kill "$CDRDAO_PID" 2>/dev/null
        wait "$CDRDAO_PID" 2>/dev/null
    fi
    if [ -n "$TOC_FILE" ] && [ -f "$TOC_FILE" ]; then
        echo "Removing partial TOC file: $TOC_FILE"
        rm -f "$TOC_FILE"
    fi
    if [ -f "$BIN_FILE" ]; then
        echo "Removing partial .bin file: $BIN_FILE"
        rm -f "$BIN_FILE"
    fi
    # Relaunch MiSTer
    if [ -x "/media/fat/MiSTer" ]; then
        echo "Relaunching MiSTer process..."
        /media/fat/MiSTer >/dev/null 2>&1 &
        sleep 2
        if ps aux | grep -E "[/]media/fat/MiSTer" | grep -v grep >/dev/null; then
            echo "MiSTer relaunched successfully"
        else
            echo "Failed to relaunch MiSTer"
        fi
    fi
}

# Trap exit signals
trap cleanup EXIT INT TERM

# Select dialog console
SELECTED_CONSOLE="/dev/tty2"
if [ ! -w "$SELECTED_CONSOLE" ]; then
    echo "No writable console ($SELECTED_CONSOLE) found for dialogs, skipping prompt"
    exit 1
fi

# Log console selection and status
echo "Console selected: $SELECTED_CONSOLE, TERM=$TERM, TTY=$(tty 2>/dev/null || echo none)"
ls -l "$SELECTED_CONSOLE" /dev/fb0 2>/dev/null
stty < "$SELECTED_CONSOLE" 2>/dev/null || echo "Failed to read stty settings for $SELECTED_CONSOLE"

# Set terminal environment
export TERM=linux

# Reset framebuffer
if [ -w "/dev/fb0" ]; then
    cat /dev/zero >/dev/fb0 2>/dev/null || echo "Failed to reset framebuffer"
fi

# Activate console
if [ -x "/sbin/chvt" ]; then
    chvt 2 2>/dev/null || echo "Failed to switch to $SELECTED_CONSOLE"
fi

# Kill MiSTer process
if ps aux | grep -E "[/]media/fat/MiSTer" | grep -v grep >/dev/null; then
    echo "Killing MiSTer process..."
    ps aux | grep -E "[/]media/fat/MiSTer" | grep -v grep | awk '{print $2}' | while read -r pid; do
        kill "$pid" 2>/dev/null
    done
    TIMEOUT=5
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ] && ps aux | grep -E "[/]media/fat/MiSTer" | grep -v grep >/dev/null; do
        sleep 1
        ELAPSED=$((ELAPSED + 1))
    done
    if ! ps aux | grep -E "[/]media/fat/MiSTer" | grep -v grep >/dev/null; then
        echo "MiSTer process terminated"
    else
        echo "Failed to terminate MiSTer process after $TIMEOUT seconds"
        exit 1
    fi
else
    echo "No MiSTer process found, proceeding with dialog"
fi

# Initialize console
if [ -w "$SELECTED_CONSOLE" ]; then
    stty sane < "$SELECTED_CONSOLE" > "$SELECTED_CONSOLE" 2>/dev/null
    tput init > "$SELECTED_CONSOLE" 2>/dev/null
    echo -e "\033[?25h" > "$SELECTED_CONSOLE" 2>/dev/null
fi

# Prompt to save disc
echo "Executing dialog: Prompt to save disc on $SELECTED_CONSOLE"
dialog --timeout 30 --yesno "RetroSpin\nGame file not found: $TITLE. Save disc as .bin/.cue to USB?" 12 50 </dev/tty2 >/dev/tty2 2>/tmp/dialog.err
RESPONSE=$?
if [ -s "/tmp/dialog.err" ]; then
    echo "Dialog error: $(cat /tmp/dialog.err)"
    rm -f "/tmp/dialog.err"
fi
echo "Dialog exit status: $RESPONSE"
if [ $RESPONSE -ne 0 ]; then
    echo "User declined to save disc image, timed out, or dialog failed"
    exit 0
fi

clear > "$SELECTED_CONSOLE" 2>/dev/null
echo "Preparing to save disc to: $CUE_FILE, $BIN_FILE..."

# Verify cdrdao exists
if [ ! -x "${RIPDISC_PATH}/cdrdao" ]; then
    echo "Error: cdrdao not found at ${RIPDISC_PATH}/cdrdao"
    dialog --timeout 30 --msgbox "RetroSpin\nError: cdrdao not found at ${RIPDISC_PATH}/cdrdao" 12 70 </dev/tty2 >/dev/tty2 2>/tmp/dialog.err
    RESPONSE=$?
    if [ -s "/tmp/dialog.err" ]; then
        echo "Dialog error: $(cat /tmp/dialog.err)"
        rm -f "/tmp/dialog.err"
    fi
    exit 1
fi

# Try to get disc size by parsing cdrdao read-toc output
TEMP_LOG="/tmp/retrospin_cdrdao.log"
TOC_FILE="/tmp/retrospin_temp.toc"
echo "Reading TOC data to detect disc size, logging to $TEMP_LOG..."
${RIPDISC_PATH}/cdrdao read-toc --device "$DRIVE_PATH" "$TOC_FILE" 2>&1 | tee "$TEMP_LOG"
CDRDAO_STATUS=$?
if [ -f "$TEMP_LOG" ]; then
    # Parse leadout sector count from output (e.g., "Leadout ... (211574)")
    DISC_SECTORS=$(grep "Leadout" "$TEMP_LOG" | grep -oE '\([0-9]+\)' | tr -d '()' | grep -E '^[0-9]+$')
    if [ -n "$DISC_SECTORS" ] && [ "$DISC_SECTORS" -gt 0 ]; then
        # Use 2352 bytes per sector for raw CD data
        DISC_SIZE=$((DISC_SECTORS * 2352))
        echo "Disc size detected via TOC output: $DISC_SIZE bytes ($DISC_SECTORS sectors)"
    else
        echo "Failed to parse sectors from TOC output, falling back to blockdev..."
        DISC_SIZE=$(blockdev --getsize64 "$DRIVE_PATH" 2>/dev/null)
        if [ -n "$DISC_SIZE" ] && [ "$DISC_SIZE" -gt 0 ]; then
            echo "Disc size detected via blockdev: $DISC_SIZE bytes"
        else
            # Last resort: 700MB
            DISC_SIZE=$((700 * 1024 * 1024))
            echo "Disc size detection failed, using fallback: $DISC_SIZE bytes"
        fi
    fi
else
    echo "Failed to capture TOC data (no log created), falling back to blockdev..."
    dialog --timeout 30 --msgbox "RetroSpin\nWarning: Failed to read TOC data for size detection\nFalling back to blockdev..." 12 70 </dev/tty2 >/dev/tty2 2>/tmp/dialog.err
    RESPONSE=$?
    if [ -s "/tmp/dialog.err" ]; then
        echo "Dialog error: $(cat /tmp/dialog.err)"
        rm -f "/tmp/dialog.err"
    fi
    DISC_SIZE=$(blockdev --getsize64 "$DRIVE_PATH" 2>/dev/null)
    if [ -n "$DISC_SIZE" ] && [ "$DISC_SIZE" -gt 0 ]; then
        echo "Disc size detected via blockdev: $DISC_SIZE bytes"
    else
        # Last resort: 700MB
        DISC_SIZE=$((700 * 1024 * 1024))
        echo "Disc size detection failed, using fallback: $DISC_SIZE bytes"
    fi
fi

# Convert sizes to MB for display
DISC_SIZE_MB=$(echo "scale=1; $DISC_SIZE / 1024 / 1024" | bc)

# Show debug info dialog before copying
echo "Executing dialog: Save disc info on $SELECTED_CONSOLE"
dialog --timeout 30 --msgbox "RetroSpin\nPreparing to save disc...\nDrive: $DRIVE_PATH\nSystem: $SYSTEM_NAME\nSize: $DISC_SIZE_MB MB\nOutput: $CUE_FILE" 12 70 </dev/tty2 >/dev/tty2 2>/tmp/dialog.err
RESPONSE=$?
if [ -s "/tmp/dialog.err" ]; then
    echo "Dialog error: $(cat /tmp/dialog.err)"
    rm -f "/tmp/dialog  echo "Disc size detected via blockdev: $DISC_SIZE bytes" > /dev/null
fi

# Start cdrdao in background, using maximum read speed
START_TIME=$(date +%s)
${RIPDISC_PATH}/cdrdao read-cd --read-raw --speed max --datafile "$BIN_FILE" --device "$DRIVE_PATH" --driver generic-mmc-raw "$TOC_FILE" > /dev/null 2>&1 &
CDRDAO_PID=$!

# Wait for copying to start or timeout
TIMEOUT=15
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ] && ! [ -f "$BIN_FILE" ]; do
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

# Progress gauge with dynamic time, size, and transfer rate
echo "Executing dialog: Progress gauge on $SELECTED_CONSOLE"
( while kill -0 $CDRDAO_PID 2>/dev/null; do
    if [ -f "$BIN_FILE" ]; then
        CURRENT_SIZE=$(stat -c %s "$BIN_FILE" 2>/dev/null || echo 0)
        CURRENT_SIZE_MB=$(echo "scale=1; $CURRENT_SIZE / 1024 / 1024" | bc)
        PERCENT=$((CURRENT_SIZE * 100 / DISC_SIZE))
        if [ $PERCENT -gt 100 ]; then PERCENT=100; fi

        # Calculate elapsed time and estimate remaining time
        CURRENT_TIME=$(date +%s)
        ELAPSED_SECONDS=$((CURRENT_TIME - START_TIME))
        if [ $CURRENT_SIZE -gt 0 ] && [ $ELAPSED_SECONDS -gt 0 ]; then
            READ_RATE=$((CURRENT_SIZE / ELAPSED_SECONDS))
            TRANSFER_RATE_MB=$(echo "scale=1; $READ_RATE / 1024 / 1024" | bc)
            if [ $READ_RATE -gt 0 ]; then
                REMAINING_BYTES=$((DISC_SIZE - CURRENT_SIZE))
                ESTIMATED_SECONDS=$((REMAINING_BYTES / READ_RATE))
                ESTIMATED_MINUTES=$((ESTIMATED_SECONDS / 60))
                ESTIMATED_REMAINDER=$((ESTIMATED_SECONDS % 60))
            else
                ESTIMATED_MINUTES=0
                ESTIMATED_REMAINDER=0
                TRANSFER_RATE_MB="0.0"
            fi
        else
            READ_RATE=2457600
            TRANSFER_RATE_MB="2.4"
            REMAINING_BYTES=$((DISC_SIZE - CURRENT_SIZE))
            ESTIMATED_SECONDS=$((REMAINING_BYTES / READ_RATE))
            ESTIMATED_MINUTES=$((ESTIMATED_SECONDS / 60))
            ESTIMATED_REMAINDER=$((ESTIMATED_SECONDS % 60))
        fi

        echo "XXX"
        echo "$PERCENT"
        echo -e "RetroSpin\nSaving $TITLE...\nSaved: $CURRENT_SIZE_MB MB / $DISC_SIZE_MB MB\nEstimated time remaining: $ESTIMATED_MINUTES min $ESTIMATED_REMAINDER sec\nTransfer rate: $TRANSFER_RATE_MB MB/s"
        echo "XXX"
        sleep 10
    fi
done ) | dialog --gauge "RetroSpin" 12 70 0 </dev/tty2 >/dev/tty2 2>/tmp/dialog.err
RESPONSE=$?
if [ -s "/tmp/dialog.err" ]; then
    echo "Dialog error: $(cat /tmp/dialog.err)"
    rm -f "/tmp/dialog.err"
fi

# Wait for cdrdao to finish and check status
wait $CDRDAO_PID
CDRDAO_STATUS=$?
if [ $CDRDAO_STATUS -eq 0 ]; then
    echo "Save to USB complete"

    # Convert .toc to .cue
    if [ -f "$TOC_FILE" ]; then
        echo "Converting .toc to .cue: $CUE_FILE"
        ${RIPDISC_PATH}/toc2cue "$TOC_FILE" "$CUE_FILE" > /dev/null 2>&1
        if [ -f "$CUE_FILE" ]; then
            sed -i "s|$BIN_FILE|$TITLE.bin|g" "$CUE_FILE"  # Replace full path with filename
            echo "Successfully created .cue file: $CUE_FILE"
        else
            echo "Error: Failed to create .cue file: $CUE_FILE"
            dialog --timeout 30 --msgbox "RetroSpin\nError: Failed to create .cue file\n.bin file saved at $BIN_FILE" 12 70 </dev/tty2 >/dev/tty2 2>/tmp/dialog.err
            RESPONSE=$?
            if [ -s "/tmp/dialog.err" ]; then
                echo "Dialog error: $(cat /tmp/dialog.err)"
                rm -f "/tmp/dialog.err"
            fi
            rm -f "$TOC_FILE"
            exit 1
        fi
        # Clean up .toc file
        rm -f "$TOC_FILE"
        echo "Removed temporary .toc file: $TOC_FILE"
    else
        echo "Error: .toc file missing after cdrdao: $TOC_FILE"
        dialog --timeout 30 --msgbox "RetroSpin\nError: .toc file missing\n.bin file saved at $BIN_FILE" 12 70 </dev/tty2 >/dev/tty2 2>/tmp/dialog.err
        RESPONSE=$?
        if [ -s "/tmp/dialog.err" ]; then
            echo "Dialog error: $(cat /tmp/dialog.err)"
            rm -f "/tmp/dialog.err"
        fi
        exit 1
    fi

    # Verify both files exist
    if [ -f "$CUE_FILE" ] && [ -f "$BIN_FILE" ]; then
        echo "Successfully saved $CUE_FILE and $BIN_FILE"
        FINAL_MESSAGE="Disc saved successfully. Please close this dialog to restart the launcher and load $TITLE."
    else
        echo "Error: Missing .cue or .bin file after save"
        FINAL_MESSAGE="Disc save incomplete. Check $CUE_FILE and $BIN_FILE."
    fi
else
    echo "Error occurred during disc save. Check $BIN_FILE and $TOC_FILE for partial data."
    FINAL_MESSAGE="Disc save failed. Partial data may be at $BIN_FILE. Close to restart launcher."
fi

# Prompt user to close and restart launcher
echo "Executing dialog: Final message on $SELECTED_CONSOLE"
dialog --timeout 30 --msgbox "RetroSpin\n$FINAL_MESSAGE" 12 50 </dev/tty2 >/dev/tty2 2>/tmp/dialog.err
RESPONSE=$?
if [ -s "/tmp/dialog.err" ]; then
    echo "Dialog error: $(cat /tmp/dialog.err)"
    rm -f "/tmp/dialog.err"
fi

# Restart launcher via retrospin.sh
echo "Restarting RetroSpin launcher via retrospin.sh..."
/media/fat/Scripts/retrospin.sh
exit 0