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
if [ "$SYSTEM" == "PSX" ]; then
    BASE_DIR="$USB_PSX_PATH"
    SYSTEM_NAME="Sony PlayStation"
elif [ "$SYSTEM" == "mcd" ]; then
    BASE_DIR="$USB_MCD_PATH"
    SYSTEM_NAME="Sega CD"
fi
RIPDISC_PATH="/media/fat/_Utility"

# Ensure directory exists
mkdir -p "$BASE_DIR"

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
    if [ -n "$BIN_FILE" ] && [ -f "$BIN_FILE" ]; then
        echo "Removing partial BIN file: $BIN_FILE"
        rm -f "$BIN_FILE"
    fi
    # Note: /tmp/retrospin_temp.toc is not deleted for debugging
}

# Trap exit signals
trap cleanup EXIT INT TERM

# Check for .cue file and corresponding .bin file
CUE_FILE="$BASE_DIR/$TITLE.cue"
BIN_FILE="$BASE_DIR/$TITLE.bin"
SAVE_NEEDED=1

if [ -f "$CUE_FILE" ]; then
    if [ -f "$BIN_FILE" ]; then
        echo "Both .cue and .bin files found: $CUE_FILE, $BIN_FILE"
        SAVE_NEEDED=0
    else
        echo ".cue file found without .bin: $CUE_FILE"
        dialog --yesno "RetroSpin\n.cue file found for $TITLE, but no .bin file.\nSave disc as .bin/.cue to USB?" 12 50
        RESPONSE=$?
        if [ $RESPONSE -ne 0 ]; then
            echo "User declined to save disc image due to missing .bin"
            clear
            exit 0
        fi
    fi
else
    # Normal prompt for missing game file
    dialog --yesno "RetroSpin\nGame file not found: $TITLE. Save disc as .bin/.cue to USB?" 12 50
    RESPONSE=$?
    if [ $RESPONSE -ne 0 ]; then
        echo "User declined to save disc image"
        clear
        exit 0
    fi
fi

if [ $SAVE_NEEDED -eq 1 ]; then
    clear  # Clear the screen after confirming save
    echo "Preparing to save disc to: $BIN_FILE..."

    # Delete any existing .cue or partial .bin files
    if [ -f "$CUE_FILE" ]; then
        echo "Removing lone .cue file: $CUE_FILE"
        rm -f "$CUE_FILE"
    fi
    if [ -f "$BIN_FILE" ]; then
        echo "Removing partial .bin file: $BIN_FILE"
        rm -f "$BIN_FILE"
    fi

    # Verify cdrdao exists
    if [ ! -x "${RIPDISC_PATH}/cdrdao" ]; then
        echo "Error: cdrdao not found at ${RIPDISC_PATH}/cdrdao"
        dialog --msgbox "RetroSpin\nError: cdrdao not found at ${RIPDISC_PATH}/cdrdao" 12 70
        exit 1
    fi

    # Try to get disc size by parsing cdrdao read-toc output
    TEMP_LOG="/tmp/retrospin_cdrdao.log"
    TEMP_TOC_FILE="/tmp/retrospin_temp.toc"
    echo "Reading TOC data to detect disc size, logging to $TEMP_LOG..."
    ${RIPDISC_PATH}/cdrdao read-toc --device "$DRIVE_PATH" "$TEMP_TOC_FILE" 2>&1 | tee "$TEMP_LOG"
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
        dialog --msgbox "RetroSpin\nWarning: Failed to read TOC data for size detection\nFalling back to blockdev..." 12 70
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
    dialog --msgbox "RetroSpin\nPreparing to save disc...\nDrive: $DRIVE_PATH\nSystem: $SYSTEM_NAME\nSize: $DISC_SIZE_MB MB\nOutput: $BIN_FILE" 12 70 &

    # Start cdrdao in background, using maximum read speed
    START_TIME=$(date +%s)
    ${RIPDISC_PATH}/cdrdao read-cd --read-raw --speed max --datafile "$BIN_FILE" --device "$DRIVE_PATH" --driver generic-mmc-raw "$TOC_FILE" > /dev/null 2>&1 &

    # Get cdrdao process ID
    CDRDAO_PID=$!

    # Wait for copying to start or timeout
    TIMEOUT=15
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ] && ! [ -f "$BIN_FILE" ]; do
        sleep 1
        ELAPSED=$((ELAPSED + 1))
    done

    # Kill debug dialog
    pkill -f "dialog --msgbox RetroSpin" 2>/dev/null

    # Progress gauge with dynamic time, size, and transfer rate
    (
        while kill -0 $CDRDAO_PID 2>/dev/null; do
            if [ -f "$BIN_FILE" ]; then
                CURRENT_SIZE=$(stat -c %s "$BIN_FILE" 2>/dev/null || echo 0)
                CURRENT_SIZE_MB=$(echo "scale=1; $CURRENT_SIZE / 1024 / 1024" | bc)
                PERCENT=$((CURRENT_SIZE * 100 / DISC_SIZE))
                if [ $PERCENT -gt 100 ]; then PERCENT=100; fi

                # Calculate elapsed time and estimate remaining time
                CURRENT_TIME=$(date +%s)
                ELAPSED_SECONDS=$((CURRENT_TIME - START_TIME))
                if [ $CURRENT_SIZE -gt 0 ] && [ $ELAPSED_SECONDS -gt 0 ]; then
                    # Calculate actual read rate (bytes/sec)
                    READ_RATE=$((CURRENT_SIZE / ELAPSED_SECONDS))
                    # Calculate transfer rate in MB/s
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
                    # Fallback estimate (2.4 MB/s = 2457600 bytes/s)
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
            fi
            sleep 10  # Update every 10 seconds
        done
    ) | dialog --gauge "RetroSpin" 12 70 0 | cat

    # Wait for cdrdao to finish and check status
    wait $CDRDAO_PID
    CDRDAO_STATUS=$?
    if [ $CDRDAO_STATUS -eq 0 ]; then
        echo "Save to USB complete"

        # Convert .toc to .cue with only filename
        ${RIPDISC_PATH}/toc2cue "$TOC_FILE" "$CUE_FILE" > /dev/null 2>&1
        sed -i "s|$BIN_FILE|$TITLE.bin|g" "$CUE_FILE"  # Replace full path with just filename
        echo "Converted .toc to .cue: $CUE_FILE"

        # Clean up .toc file
        rm -f "$TOC_FILE"
        FINAL_MESSAGE="Disc saved successfully. Please close this dialog to restart the launcher and load $TITLE."

        # Launch retrospin_launcher.py after successful save
        echo "Launching RetroSpin launcher..."
        python3 /media/fat/retrospin/retrospin_launcher.py &
    else
        echo "Error occurred during disc save. Check $BIN_FILE and $TOC_FILE for partial data."
        FINAL_MESSAGE="Disc save failed. Partial data saved at $BIN_FILE. Close to restart launcher."
    fi
    
    # Prompt user to close and restart launcher (for failed saves or user interaction)
    dialog --msgbox "RetroSpin\n$FINAL_MESSAGE" 12 50
    /media/fat/Scripts/retrospin.sh
else
    # Both .cue and .bin exist, no save needed
    echo "No save needed, launching RetroSpin launcher..."
    python3 /media/fat/retrospin/retrospin_launcher.py &
fi