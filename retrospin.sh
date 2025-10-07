#!/bin/bash

# retrospin - RetroSpin Disc Manager for MiSTer FPGA
# Dialog menu with options to run core functions

while true; do
    CHOICE=$(dialog --clear --backtitle "RetroSpin Disc Manager" \
                    --title "RetroSpin Disc Manager" \
                    --menu "Select an option:" \
                    15 40 4 \
                    1 "Test Disc" \
                    2 "Save Disc" \
                    3 "Run Service" \
                    4 "Update Database" \
                    2>&1 >/dev/tty)

    clear
    case $CHOICE in
        1) bash core/functions/test_disc.sh ;;
        2) bash core/functions/save_disc.sh ;;
        3) bash core/functions/service.sh ;;
        4) python3 core/functions/update_db.py ;;
        *) break ;;
    esac
done

echo "Exiting RetroSpin Disc Manager."