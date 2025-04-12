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
dialog --yesno "\Zb\Z1RetroSpin\Zn\nGame file not found: $TITLE. Save disc as .bin/.cue to USB?" 10 50
RESPONSE=$?

if [ $RESPONSE -eq 0 ]; then  # Yes
    BIN_FILE="$BASE_DIR/$TITLE.bin"
    CUE_FILE="$BASE_DIR/$TITLE.cue"
    TOC_FILE="$BASE_DIR/$TITLE.toc"
    echo "Saving disc to: $BIN_FILE..."

    # Try to get actual disc size, fall back to 700MB if it fails
    DISC_SIZE=$(blockdev --getsize64 "$DRIVE_PATH" 2>/dev/null || echo $((700 * 1024 * 1024)))
    echo "Disc size detected: $DISC_SIZE bytes"

    # Estimate time (assuming 2.4 MB/s read rate)
    READ_RATE=2457600  # 2.4 MB/s in bytes
    ESTIMATED_SECONDS=$((DISC_SIZE / READ_RATE))
    ESTIMATED_MINUTES=$((ESTIMATED_SECONDS / 60))
    ESTIMATED_REMAINDER=$((ESTIMATED_SECONDS % 60))
    echo "Estimated save time: $ESTIMATED_MINUTES minutes $ESTIMATED_REMAINDER seconds"

    # Start cdrdao in background, redirecting output to /dev/null
    ${RIPDISC_PATH}/cdrdao read-cd --read-raw --datafile "$BIN_FILE" --device "$DRIVE_PATH" --driver generic-mmc-raw "$TOC_FILE" > /dev/null 2>&1 &

    # Get cdrdao process ID
    CDRDAO_PID=$!

    # Progress gauge with RetroSpin in red
    (
        while kill -0 $CDRDAO_PID 2>/dev/null; do
            if [ -f "$BIN_FILE" ]; then
                CURRENT_SIZE=$(stat -c %s "$BIN_FILE" 2>/dev/null || echo 0)
                PERCENT=$((CURRENT_SIZE * 100 / DISC_SIZE))
                if [ $PERCENT -gt 100 ]; then PERCENT=100; fi
                echo "XXX"
                echo "$PERCENT"
                echo -e "\Zb\Z1RetroSpin\Zn\nSaving $TITLE... $PERCENT% complete\nEstimated time: $ESTIMATED_MINUTES min $ESTIMATED_REMAINDER sec"
                echo "XXX"
            fi
            sleep 10  # Update every 10 seconds
        done
    ) | dialog --gauge "\Zb\Z1RetroSpin\Zn" 10 50 0

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
    dialog --msgbox "\Zb\Z1RetroSpin\Zn\n$FINAL_MESSAGE" 10 50
    /media/fat/Scripts/retrospin.sh
else
    echo "User declined to save disc image"
    clear
    exit 0
fi