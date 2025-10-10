#!/bin/bash

# retrospin - RetroSpin Disc Manager for MiSTer FPGA
# Dialog menu with options to run core functions

# Define paths
DATA_DIR="/retrospin/data"
DB_PATH="${DATA_DIR}/games.db"

# Ensure data directory and database file exist with correct permissions
ensure_db_writable() {
    # Create data directory if it doesn't exist
    if [ ! -d "$DATA_DIR" ]; then
        mkdir -p "$DATA_DIR"
        #chown mister:mister "$DATA_DIR"
        chmod 775 "$DATA_DIR"
    fi

    # Create games.db if it doesn't exist
    if [ ! -f "$DB_PATH" ]; then
        touch "$DB_PATH"
        #chown mister:mister "$DB_PATH"
        chmod 664 "$DB_PATH"
    fi

    # Ensure games.db is writable by mister user
    #chown mister:mister "$DB_PATH"
    chmod 664 "$DB_PATH"
}

while true; do
    CHOICE=$(dialog --clear --backtitle "RetroSpin Disc Manager" \
                    --title "RetroSpin Disc Manager" \
                    --menu "Select an option:" \
                    15 40 4 \
                    1 "Test Disc" \
                    2 "Save Disc" \
                    3 "Start Retrospin Service" \
                    4 "Update Database" \
                    2>&1 >/dev/tty)

    clear
    case $CHOICE in
        1) bash python3 core/functions/test_disc.py ;;
        2) bash core/functions/save_disc.sh ;;
        3) bash core/functions/service.sh ;;
        4)
            ensure_db_writable
            python3 core/functions/update_db.py
            ;;
        *) break ;;
    esac
done

echo "Exiting RetroSpin Disc Manager."