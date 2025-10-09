import os
import time
import subprocess
from core.utilities.core import find_cores
from core.utilities.database import load_game_titles
from core.utilities.disc import get_optical_drive, is_disc_present, read_saturn_game_id, read_mcd_game_id, read_psx_game_id
from core.utilities.ui import show_popup, select_game_title
from core.utilities.launcher import launch_game_on_mister
from core.utilities.files import find_game_file

def main():
    # Log terminal environment
    print(f"Terminal environment: TERM={os.environ.get('TERM', 'unset')}, TTY={os.ttyname(0) if os.isatty(0) else 'none'}")
    
    print("Starting RetroSpin disc launcher on MiSTer...")
    game_titles = load_game_titles()
    
    # Define supported systems (full names for cores, but use DB-normalized keys for lookups)
    supported_systems = ["psx", "saturn", "megacd", "neogeo", "cdi", "tgcd"]
    
    # Find all available cores once
    available_cores = find_cores(supported_systems)
    
    # Check for core support
    if not any(available_cores.get(system) for system in supported_systems):
        show_popup("No supported CD-ROM cores (PSX, Saturn, or Mega CD) found in /media/fat/_Console/.")
        print("Cannot proceed without supported cores. Exiting...")
        return
    
    last_game_serial = None
    last_drive_path = None
    
    while True:
        drive_path = get_optical_drive()
        
        # Check if drive is accessible and disc is present
        if drive_path and is_disc_present(drive_path):
            if last_game_serial and drive_path == last_drive_path:
                print(f"Same game already loaded: {last_game_serial}. Waiting for drive to open...")
                time.sleep(1)
                continue
            
            print(f"Checking drive {drive_path}...")
            
            # Try Saturn
            saturn_game_serial = read_saturn_game_id(drive_path)
            if saturn_game_serial:
                serial_key = saturn_game_serial.upper()
                print(f"Looking up Saturn serial: {serial_key}")
                matches = []
                # Check for exact and partial matches (using DB-normalized "ss")
                for (db_serial, db_system), titles in game_titles.items():
                    if db_system == "ss" and (db_serial == serial_key or db_serial.startswith(serial_key)):
                        matches.extend(titles)
                print(f"Saturn matches found: {len(matches)}")
                if matches:
                    if len(matches) == 1:
                        title = matches[0][1]
                    else:
                        title = select_game_title(matches, "Saturn", serial_key)
                    print(f"Found Saturn game: {title} ({saturn_game_serial})")
                    saturn_core = available_cores.get("saturn")
                    if saturn_core and title != "Unknown Game":
                        launch_game_on_mister(saturn_game_serial, title, saturn_core, "saturn", drive_path, find_game_file)
                    else:
                        print(f"No Saturn core or no valid match for {saturn_game_serial}. Skipping.")
                else:
                    print(f"No database match for Saturn serial {saturn_game_serial}. Skipping.")
                last_game_serial = (saturn_game_serial, "saturn")
                last_drive_path = drive_path
                time.sleep(1)
                continue
            
            # Try Sega CD (Mega CD)
            mcd_game_serial = read_mcd_game_id(drive_path)
            if mcd_game_serial:
                serial_key = mcd_game_serial.upper()
                print(f"Looking up Mega CD serial: {serial_key}")
                matches = []
                # Check for exact and partial matches (using DB-normalized "mcd")
                for (db_serial, db_system), titles in game_titles.items():
                    if db_system == "mcd" and (db_serial == serial_key or db_serial.startswith(serial_key)):
                        matches.extend(titles)
                print(f"Mega CD matches found: {len(matches)}")
                if matches:
                    if len(matches) == 1:
                        title = matches[0][1]
                    else:
                        title = select_game_title(matches, "Mega CD", serial_key)
                    print(f"Found Mega CD game: {title} ({mcd_game_serial})")
                    mcd_core = available_cores.get("megacd")
                    if mcd_core and title != "Unknown Game":
                        launch_game_on_mister(mcd_game_serial, title, mcd_core, "megacd", drive_path, find_game_file)
                    else:
                        print(f"No Mega CD core or no valid match for {mcd_game_serial}. Skipping.")
                else:
                    print(f"No database match for Mega CD serial {mcd_game_serial}. Skipping.")
                last_game_serial = (mcd_game_serial, "megacd")
                last_drive_path = drive_path
                time.sleep(1)
                continue
            
            # Try PSX
            psx_game_serial = None
            for attempt in range(2):
                psx_game_serial = read_psx_game_id(drive_path)
                if psx_game_serial:
                    break
                print(f"PSX read attempt {attempt + 1} failed, retrying after delay...")
                time.sleep(1)
                os.system(f"umount /mnt/cdrom 2>/dev/null")  # Force unmount
            if psx_game_serial:
                serial_key = psx_game_serial.replace("_", "").upper()
                print(f"Looking up PSX serial: {serial_key}")
                matches = []
                # Check for exact and partial matches
                for (db_serial, db_system), titles in game_titles.items():
                    if db_system == "psx" and (db_serial == serial_key or db_serial.startswith(serial_key)):
                        matches.extend(titles)
                print(f"PSX matches found: {len(matches)}")
                if matches:
                    if len(matches) == 1:
                        title = matches[0][1]
                    else:
                        title = select_game_title(matches, "PSX", serial_key)
                    print(f"Found PSX game: {title} ({psx_game_serial})")
                    psx_core = available_cores.get("psx")
                    if psx_core:
                        launch_game_on_mister(psx_game_serial, title, psx_core, "psx", drive_path, find_game_file)
                    else:
                        print("No PSX core available to launch game")
                else:
                    print(f"No database match for PSX serial {psx_game_serial}. Skipping.")
                last_game_serial = (psx_game_serial, "psx")
                last_drive_path = drive_path
                time.sleep(1)
                continue
            
            print("No game detected. Waiting...")
            last_game_serial = None
            last_drive_path = None
        else:
            print("No optical drive or disc detected. Waiting...")
            last_game_serial = None
            last_drive_path = None
        
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript stopped by user. Exiting...")