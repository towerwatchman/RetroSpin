#!/bin/bash

# Arguments from Python: drive_path, title, system
DRIVE_PATH="$1"
TITLE="$2"
SYSTEM="$3"

# USB paths
USB_PSX_PATH="/media/usb0/games/PSX"
USB_SATURN_PATH="/media/usb0/games/Saturn"
BASE_DIR="$USB_SATURN_PATH"
if [ "$SYSTEM" == "PSX" ]; then
    BASE_DIR="$USB_PSX_PATH"
fi
RIPDISC_PATH="/media/fat/_Utility"

# Ensure directory exists
mkdir -p "$BASE_DIR"

# Popup to ask user
dialog --yesno "RetroSpin\nGame file not found: $TITLE. Save disc as .bin/.cue to USB?" 10 50
RESPONSE=$?

if [ $RESPONSE -eq 0 ]; then  # Yes
    BIN_FILE="$BASE_DIR/$TITLE.bin"
    CUE_FILE="$BASE_DIR/$TITLE.cue"
    TOC_FILE="$BASE_DIR/$TITLE.toc"
    echo "Saving disc to: $BIN_FILE..."

    # Try to get disc size with cdrdao disc-info
    DISC_SECTORS=$(${RIPDISC_PATH}/cdrdao disc-info --device "$DRIVE_PATH" 2>/dev/null | grep "Total sectors" | awk '{print $3}')
    if [ -n "$DISC_SECTORS" ] && [ "$DISC_SECTORS" -gt 0 ]; then
        # Use 2352 bytes per sector for raw CD data
        DISC_SIZE=$((DISC_SECTORS * 2352))
        echo "Disc size detected via cdrdao: $DISC_SIZE bytes ($DISC_SECTORS sectors)"
    else
        # Fall back to blockdev
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

    # Start cdrdao in background, redirecting output to /dev/null
    START_TIME=$(date +%s)
    ${RIPDISC_PATH}/cdrdao read-cd --read-raw --datafile "$BIN_FILE" --device "$DRIVE_PATH" --driver generic-mmc-raw "$TOC_FILE" > /dev/null 2>&1 &

    # Get cdrdao process ID
    CDRDAO_PID=$!

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
                echo -e "RetroSpin\nSaving $TITLE... $PERCENT% complete\nSaved: $CURRENT_SIZE_MB MB / $DISC_SIZE_MB MB\nEstimated time remaining: $ESTIMATED_MINUTES min $ESTIMATED_REMAINDER sec\nTransfer rate: $TRANSFER_RATE_MB MB/s"
                echo "XXX"
            fi
            sleep 10  # Update every 10 seconds
        done
    ) | dialog --gauge "RetroSpin" 10 70 0

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
    else
        echo "Error occurred during disc save. Check $BIN_FILE and $TOC_FILE for partial data."
        FINAL_MESSAGE="Disc save failed. Partial data saved at $BIN_FILE. Close to restart launcher."
    fi
    
    # Prompt user to close and restart launcher
    dialog --msgbox "RetroSpin\n$FINAL_MESSAGE" 10 50
    /media/fat/Scripts/retrospin.sh
else
    echo "User declined to save disc image"
    clear
    exit 0
fi