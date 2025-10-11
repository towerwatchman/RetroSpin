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
        chown mister:mister "$DATA_DIR"
        chmod 775 "$DATA_DIR"
    fi

    # Create games.db if it doesn't exist
    if [ ! -f "$DB_PATH" ]; then
        touch "$DB_PATH"
        chown mister:mister "$DB_PATH"
        chmod 664 "$DB_PATH"
    fi

    # Ensure games.db is writable by mister user
    chown mister:mister "$DB_PATH"
    chmod 664 "$DB_PATH"
}

# Run save_disc.py, which handles disc reading and saving
python3 core/init_database.py 2>/tmp/retrospin_err.log

while true; do
    CHOICE=$(dialog --backtitle "RetroSpin Disc Manager" \
                    --title "RetroSpin Disc Manager" \
                    --menu "Select an option:" \
                    15 40 4 \
                    1 "Test Disc" \
                    2 "Save Disc" \
                    3 "Run Service" \
                    4 "Update Database" \
                    2>&1 >/dev/tty)

    #clear
    case $CHOICE in
        1) bash core/functions/test_disc.sh ;;
        2)
            # Run save_disc.py, which handles disc reading and saving
            python3 core/functions/save_disc.py 2>/tmp/retrospin_err.log
            if [ $? -ne 0 ]; then
                error_msg=$(cat /tmp/retrospin_err.log)
                dialog --msgbox "RetroSpin\nError saving disc: $error_msg" 10 50 2>/tmp/retrospin_err.log || echo "Error saving disc: $error_msg" >&2
                echo $error_msg
            fi
            ;;
        3) python3 core/functions/retrospin_service.py ;;
        4)
            ensure_db_writable
            python3 core/update_database.py
            ;;
        *) break ;;
    esac
done

echo "Exiting RetroSpin Disc Manager."